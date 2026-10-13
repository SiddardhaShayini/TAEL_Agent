import * as vscode from 'vscode';
import { OllamaClient, ChatMessage } from './ollamaClient';
import { TaskRouter, RouteDecision } from './router';
import { WorkspaceContextProvider } from './workspaceContext';
import { ToolRegistry, XMLToolParser } from './tools';
import { EditApplier } from './editApplier';

export class TaelChatViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'tael.chatView';

  private view?: vscode.WebviewView;
  private history: ChatMessage[] = [];
  private abortController: { aborted: boolean } = { aborted: false };
  private router: TaskRouter;

  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly ollamaClient: OllamaClient,
    private readonly workspaceContext: WorkspaceContextProvider,
    private readonly toolRegistry: ToolRegistry,
    private readonly editApplier: EditApplier
  ) {
    this.router = new TaskRouter();
  }

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this.extensionUri],
    };

    webviewView.webview.html = this.getHtmlForWebview(webviewView.webview);

    webviewView.webview.onDidReceiveMessage(async (msg) => {
      switch (msg.type) {
        case 'sendPrompt':
          await this.handleUserPrompt(msg.prompt, Boolean(msg.agentMode), Boolean(msg.includeContext));
          break;
        case 'stopGeneration':
          this.abortController.aborted = true;
          break;
        case 'applyCode':
          await this.editApplier.applyToActiveEditor(msg.code, 'auto');
          break;
        case 'diffCode':
          await this.editApplier.previewDiff(msg.code);
          break;
        case 'quickAction':
          await this.triggerQuickAction(msg.action);
          break;
        case 'clearChat':
          this.clearConversation();
          break;
        case 'refreshContext':
          await this.sendWorkspaceStatusToWebview();
          break;
      }
    });

    // Send initial status once webview loads
    setTimeout(() => {
      void this.sendWorkspaceStatusToWebview();
    }, 300);
  }

  public clearConversation(): void {
    this.history = [];
    this.postMessage({ type: 'cleared' });
  }

  public async sendWorkspaceStatusToWebview(): Promise<void> {
    if (!this.view) {
      return;
    }
    const health = await this.ollamaClient.checkStatus();
    const snap = this.workspaceContext.captureSnapshot();
    this.postMessage({
      type: 'statusUpdate',
      health,
      workspace: {
        name: snap.workspaceName,
        activeFile: snap.activeEditor.hasActiveEditor ? snap.activeEditor.relativePath : 'None',
        hasSelection: snap.activeEditor.hasSelection,
        selectionLines: snap.activeEditor.hasSelection
          ? `L${snap.activeEditor.selectionStartLine}-${snap.activeEditor.selectionEndLine}`
          : '',
        diagnosticsCount: snap.activeEditor.diagnostics.length,
      },
    });
  }

  private async triggerQuickAction(action: string): Promise<void> {
    switch (action) {
      case 'generate':
        await vscode.commands.executeCommand('tael.generateCode');
        break;
      case 'refactor':
        await vscode.commands.executeCommand('tael.refactorCode');
        break;
      case 'explain':
        await vscode.commands.executeCommand('tael.explainCode');
        break;
      case 'fix':
        await vscode.commands.executeCommand('tael.fixDiagnostics');
        break;
    }
  }

  /**
   * Public method so editor commands (Explain, Refactor, Generate, Agent Task) can send prompts directly into the Chat Panel.
   */
  public async runPromptInPanel(
    displayTitle: string,
    prompt: string,
    forceAgentMode: boolean = false,
    includeContext: boolean = true
  ): Promise<void> {
    if (this.view) {
      this.view.show?.(true);
    } else {
      await vscode.commands.executeCommand('tael.chatView.focus');
    }
    await this.handleUserPrompt(prompt, forceAgentMode, includeContext, displayTitle);
  }

  /**
   * Executes the full TAEL pipeline:
   * User Prompt -> Workspace Context Injection -> Dynamic Task Router -> Ollama Stream ->
   * XML <tool_call> Detection -> Sandboxed Tool Execution -> <tool_response> Loop.
   */
  public async handleUserPrompt(
    userPrompt: string,
    forceAgentMode: boolean = false,
    includeContext: boolean = true,
    displayOverride?: string
  ): Promise<void> {
    const trimmed = (userPrompt || '').trim();
    if (!trimmed) {
      return;
    }

    this.abortController = { aborted: false };
    const config = vscode.workspace.getConfiguration('tael');
    const autoTools = forceAgentMode || config.get<boolean>('autoExecuteTools', true);
    const maxIterations = config.get<number>('maxAgentIterations', 6);

    // 1. Update workspace root on tool registry
    this.toolRegistry.setWorkspaceRoot(this.workspaceContext.getWorkspaceRoot());

    // 2. Route prompt via Dynamic Task Router
    const route: RouteDecision = this.router.route(trimmed, forceAgentMode);

    // 3. Notify webview of user message and routing decision
    this.postMessage({
      type: 'userMessage',
      content: displayOverride || trimmed,
      route: {
        category: route.category,
        confidence: Math.round(route.confidence * 100),
        temperature: route.temperature,
        isFallback: route.isFallback,
      },
    });

    // 4. Construct augmented prompt with Workspace Context
    let fullUserContent = trimmed;
    if (includeContext && config.get<boolean>('includeWorkspaceContext', true)) {
      const ctxBlock = this.workspaceContext.formatPromptContext(false);
      fullUserContent = `${ctxBlock}\n\n[USER REQUEST]\n${trimmed}`;
    }

    this.history.push({ role: 'user', content: fullUserContent });

    // Keep sliding window of recent history to respect 4096 token budget
    if (this.history.length > 12) {
      this.history = this.history.slice(-12);
    }

    // 5. Autonomous Multi-Step Agent Loop
    let iteration = 0;
    while (iteration < maxIterations && !this.abortController.aborted) {
      iteration++;

      const messagesForInference: ChatMessage[] = [
        { role: 'system', content: route.systemPrompt },
        ...this.history,
      ];

      const streamId = `msg_${Date.now()}_${iteration}`;
      this.postMessage({
        type: 'streamStart',
        streamId,
        iteration,
        category: route.category,
      });

      try {
        const result = await this.ollamaClient.chatStream(
          messagesForInference,
          {
            temperature: route.temperature,
            top_p: route.topP,
            num_predict: route.maxTokens,
          },
          (_token, accumulated) => {
            this.postMessage({
              type: 'streamDelta',
              streamId,
              content: accumulated,
            });
          },
          this.abortController
        );

        this.history.push({ role: 'assistant', content: result.content });
        this.editApplier.setLastSuggestedCode(result.content);

        this.postMessage({
          type: 'streamDone',
          streamId,
          content: result.content,
          tokensPerSec: result.tokensPerSec,
          evalCount: result.evalCount,
          durationMs: result.evalDurationMs,
        });

        // 6. Check for <tool_call> tags
        const toolCalls = XMLToolParser.extractToolCalls(result.content);
        if (toolCalls.length === 0 || !autoTools || this.abortController.aborted) {
          break;
        }

        // Execute each tool call and collect <tool_response> blocks
        const responseBlocks: string[] = [];
        for (const call of toolCalls) {
          this.postMessage({
            type: 'toolStart',
            toolName: call.name,
            args: call.arguments,
          });

          const execResult = await this.toolRegistry.execute(call);
          responseBlocks.push(execResult.xmlResponse);

          this.postMessage({
            type: 'toolDone',
            toolName: execResult.toolName,
            status: execResult.status,
            output: execResult.output,
            durationMs: execResult.durationMs,
          });
        }

        // Feed <tool_response> back to the model for next agent turn
        const combinedToolFeedback =
          responseBlocks.join('\n\n') +
          '\n\nContinue based on the tool execution results above. If the task is complete, summarize the final result clearly.';
        this.history.push({ role: 'user', content: combinedToolFeedback });
      } catch (err: unknown) {
        const errMsg = err instanceof Error ? err.message : String(err);
        this.postMessage({
          type: 'streamError',
          streamId,
          error: `Ollama Runtime Error: ${errMsg}. Verify Ollama is running ('ollama serve') and 'tael-agent' is created.`,
        });
        break;
      }
    }
  }

  private postMessage(message: unknown): void {
    if (this.view) {
      void this.view.webview.postMessage(message);
    }
  }

  private getHtmlForWebview(_webview: vscode.Webview): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>TAEL AI Assistant</title>
  <style>
    :root {
      --bg: var(--vscode-sideBar-background, #1e1e1e);
      --fg: var(--vscode-sideBar-foreground, #cccccc);
      --input-bg: var(--vscode-input-background, #2d2d2d);
      --input-fg: var(--vscode-input-foreground, #ffffff);
      --input-border: var(--vscode-input-border, #3e3e3e);
      --btn-bg: var(--vscode-button-background, #0e639c);
      --btn-fg: var(--vscode-button-foreground, #ffffff);
      --btn-hover: var(--vscode-button-hoverBackground, #1177bb);
      --badge-bg: var(--vscode-badge-background, #4d4d4d);
      --badge-fg: var(--vscode-badge-foreground, #ffffff);
      --border: var(--vscode-panel-border, #333333);
      --code-bg: var(--vscode-textCodeBlock-background, #161616);
      --accent: #38bdf8;
      --success: #4ade80;
      --warn: #fbbf24;
      --danger: #f87171;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      padding: 0;
      background: var(--bg);
      color: var(--fg);
      font-family: var(--vscode-font-family, system-ui, -apple-system, sans-serif);
      font-size: var(--vscode-font-size, 13px);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }

    /* Status & Context Header */
    .header {
      padding: 8px 10px;
      border-bottom: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 6px;
      background: rgba(0, 0, 0, 0.12);
    }

    .status-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
    }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      font-weight: 600;
    }

    .dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--warn);
    }
    .dot.online { background: var(--success); }
    .dot.offline { background: var(--danger); }

    .context-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      font-size: 11px;
    }

    .tag {
      background: var(--badge-bg);
      color: var(--badge-fg);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 10.5px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 100%;
    }

    /* Quick Action Toolbar */
    .quick-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      padding: 6px 10px;
      border-bottom: 1px solid var(--border);
    }

    .action-btn {
      background: var(--input-bg);
      color: var(--fg);
      border: 1px solid var(--input-border);
      border-radius: 4px;
      padding: 3px 7px;
      font-size: 11px;
      cursor: pointer;
      transition: background 0.15s;
    }
    .action-btn:hover {
      background: var(--btn-bg);
      color: var(--btn-fg);
    }

    /* Scrollable Chat Stream with Modern Scroll-State Support */
    .scroller {
      flex: 1;
      overflow-y: auto;
      padding: 10px;
      padding-bottom: 36px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      container-type: scroll-state;
      position: relative;
    }

    .scroll-sentinel {
      height: 0;
      width: 0;
      visibility: hidden;
    }

    .msg {
      border-radius: 6px;
      padding: 8px 10px;
      line-height: 1.45;
      word-wrap: break-word;
      border: 1px solid var(--border);
    }

    .msg.user {
      background: rgba(14, 99, 156, 0.18);
      border-color: rgba(56, 189, 248, 0.35);
      align-self: flex-end;
      width: 94%;
    }

    .msg.assistant {
      background: rgba(255, 255, 255, 0.03);
      align-self: flex-start;
      width: 98%;
    }

    .msg-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 10.5px;
      opacity: 0.85;
      margin-bottom: 5px;
      padding-bottom: 3px;
      border-bottom: 1px dashed rgba(255, 255, 255, 0.1);
    }

    .router-badge {
      background: rgba(56, 189, 248, 0.18);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.4);
      padding: 1px 6px;
      border-radius: 10px;
      font-weight: 600;
      font-size: 10px;
    }

    /* Code Blocks & 1-Click Edit Controls */
    .code-wrapper {
      margin: 8px 0;
      border: 1px solid var(--border);
      border-radius: 5px;
      overflow: hidden;
      background: var(--code-bg);
    }

    .code-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: rgba(255, 255, 255, 0.06);
      padding: 4px 8px;
      font-size: 10.5px;
    }

    .code-actions {
      display: flex;
      gap: 5px;
    }

    .code-btn {
      background: var(--btn-bg);
      color: var(--btn-fg);
      border: none;
      border-radius: 3px;
      padding: 2px 6px;
      font-size: 10px;
      cursor: pointer;
    }
    .code-btn.secondary {
      background: transparent;
      border: 1px solid var(--input-border);
      color: var(--fg);
    }
    .code-btn:hover {
      opacity: 0.9;
    }

    pre {
      margin: 0;
      padding: 8px;
      overflow-x: auto;
      font-family: var(--vscode-editor-font-family, Consolas, monospace);
      font-size: 12px;
      white-space: pre;
    }

    /* Tool Call Execution Card */
    .tool-card {
      border-left: 3px solid var(--accent);
      background: rgba(56, 189, 248, 0.07);
      padding: 6px 8px;
      border-radius: 4px;
      font-size: 11.5px;
    }
    .tool-card.success { border-left-color: var(--success); }
    .tool-card.error { border-left-color: var(--danger); }

    .tool-title {
      font-weight: 600;
      display: flex;
      justify-content: space-between;
      margin-bottom: 4px;
    }

    .tool-output {
      font-family: var(--vscode-editor-font-family, monospace);
      font-size: 11px;
      max-height: 110px;
      overflow-y: auto;
      white-space: pre-wrap;
      opacity: 0.9;
      background: rgba(0, 0, 0, 0.25);
      padding: 4px 6px;
      border-radius: 3px;
    }

    /* Floating Scroll-to-Top / Bottom Affordance */
    .back-to-top {
      position: sticky;
      bottom: 8px;
      align-self: flex-end;
      background: var(--btn-bg);
      color: var(--btn-fg);
      border: none;
      border-radius: 12px;
      padding: 3px 9px;
      font-size: 10.5px;
      cursor: pointer;
      visibility: visible;
      opacity: 1;
      transition: visibility 0.25s, opacity 0.25s ease, translate 0.25s ease;
    }

    @supports (container-type: scroll-state) {
      .back-to-top {
        visibility: hidden;
        opacity: 0;
        translate: 0 10px;
      }
      @container scroll-state(scrollable: top) {
        .back-to-top {
          visibility: visible;
          opacity: 1;
          translate: 0 0;
        }
      }
    }

    /* Composer Area */
    .composer {
      padding: 8px 10px;
      border-top: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 6px;
      background: var(--bg);
    }

    .composer-options {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 11px;
    }

    .checkbox-label {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      cursor: pointer;
    }

    textarea {
      width: 100%;
      min-height: 58px;
      max-height: 140px;
      resize: vertical;
      background: var(--input-bg);
      color: var(--input-fg);
      border: 1px solid var(--input-border);
      border-radius: 4px;
      padding: 6px 8px;
      font-family: inherit;
      font-size: 12.5px;
    }
    textarea:focus {
      outline: 1px solid var(--accent);
    }

    .composer-buttons {
      display: flex;
      gap: 6px;
      justify-content: flex-end;
    }

    .primary-btn {
      background: var(--btn-bg);
      color: var(--btn-fg);
      border: none;
      border-radius: 4px;
      padding: 5px 12px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
    }
    .primary-btn:hover { background: var(--btn-hover); }

    .stop-btn {
      background: rgba(248, 113, 113, 0.2);
      color: var(--danger);
      border: 1px solid var(--danger);
      border-radius: 4px;
      padding: 5px 10px;
      font-size: 12px;
      cursor: pointer;
      display: none;
    }
  </style>
</head>
<body>
  <div class="header">
    <div class="status-row">
      <span class="status-pill">
        <span id="statusDot" class="dot"></span>
        <span id="statusText">Checking Ollama...</span>
      </span>
      <button class="action-btn" id="refreshBtn" title="Refresh Workspace & Ollama Status">↻ Status</button>
    </div>
    <div class="context-bar" id="contextBar">
      <span class="tag" id="fileTag">File: None</span>
      <span class="tag" id="selTag" style="display:none;"></span>
      <span class="tag" id="diagTag" style="display:none;"></span>
    </div>
  </div>

  <div class="quick-actions">
    <button class="action-btn" data-action="generate">✨ Generate</button>
    <button class="action-btn" data-action="refactor">🛠️ Refactor</button>
    <button class="action-btn" data-action="explain">📖 Explain</button>
    <button class="action-btn" data-action="fix">🩺 Fix Problems</button>
    <button class="action-btn" id="clearBtn">🗑️ Clear</button>
  </div>

  <div class="scroller" id="chatScroller">
    <div class="scroll-sentinel" id="topSentinel"></div>
    <div class="msg assistant">
      <div class="msg-header">
        <strong>TAEL v2.0 (Granite 2B GGUF)</strong>
        <span class="router-badge">Ready</span>
      </div>
      <div>
        Hello! I am <strong>TAEL</strong>, your local autonomous software engineering assistant powered by Ollama.<br/><br/>
        • Highlight code and click <strong>Refactor</strong> or <strong>Explain</strong><br/>
        • Enable <strong>Agent Tools</strong> to let me read/write files, search code, and run commands<br/>
        • Click <strong>Apply Edit</strong> or <strong>Diff Preview</strong> on any generated code block
      </div>
    </div>
    <button class="back-to-top" id="scrollTopBtn" title="Scroll to top">↑ Top</button>
  </div>

  <div class="composer">
    <div class="composer-options">
      <label class="checkbox-label" title="Allow TAEL to execute sandboxed <tool_call> actions in the workspace">
        <input type="checkbox" id="agentModeToggle" checked />
        <span>🤖 Agent Tools</span>
      </label>
      <label class="checkbox-label" title="Include active editor file, selection, and diagnostics">
        <input type="checkbox" id="contextToggle" checked />
        <span>📂 Workspace Context</span>
      </label>
    </div>
    <textarea id="promptInput" placeholder="Ask TAEL to write code, refactor, explain, or execute workspace tools... (Enter to send, Shift+Enter for newline)"></textarea>
    <div class="composer-buttons">
      <button class="stop-btn" id="stopBtn">⏹ Stop</button>
      <button class="primary-btn" id="sendBtn">Send ↵</button>
    </div>
  </div>

  <script>
    const vscode = acquireVsCodeApi();
    const scroller = document.getElementById('chatScroller');
    const promptInput = document.getElementById('promptInput');
    const sendBtn = document.getElementById('sendBtn');
    const stopBtn = document.getElementById('stopBtn');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const fileTag = document.getElementById('fileTag');
    const selTag = document.getElementById('selTag');
    const diagTag = document.getElementById('diagTag');
    const agentModeToggle = document.getElementById('agentModeToggle');
    const contextToggle = document.getElementById('contextToggle');
    const scrollTopBtn = document.getElementById('scrollTopBtn');

    const activeStreams = new Map();
    const codeStore = new Map();
    let codeSeq = 0;

    function escapeHtml(str) {
      return (str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    }

    function renderMarkdownWithActions(raw) {
      // Hide raw <tool_call> blocks or render them neatly
      let cleaned = (raw || '').replace(/<tool_call>([\\s\\S]*?)(?:<\\/tool_call>|$)/gi, (_m, inner) => {
        return '\\n\`\`\`json\\n// [TAEL Tool Call]\\n' + inner.trim() + '\\n\`\`\`\\n';
      });

      const parts = [];
      let lastIndex = 0;
      const fenceRegex = /\`\`\`([a-zA-Z0-9_+-]*)?\\r?\\n([\\s\\S]*?)(?:\`\`\`|$)/g;
      let match;

      while ((match = fenceRegex.exec(cleaned)) !== null) {
        if (match.index > lastIndex) {
          const prose = escapeHtml(cleaned.slice(lastIndex, match.index)).replace(/\\n/g, '<br/>');
          parts.push('<span>' + prose + '</span>');
        }
        const lang = match[1] || 'code';
        const codeContent = match[2];
        const codeId = 'code_' + (++codeSeq);
        codeStore.set(codeId, codeContent);

        parts.push(
          '<div class="code-wrapper">' +
            '<div class="code-toolbar">' +
              '<span>' + escapeHtml(lang) + '</span>' +
              '<div class="code-actions">' +
                '<button class="code-btn" data-code-action="apply" data-code-id="' + codeId + '">✓ Apply Edit</button>' +
                '<button class="code-btn secondary" data-code-action="diff" data-code-id="' + codeId + '">⇄ Diff</button>' +
                '<button class="code-btn secondary" data-code-action="copy" data-code-id="' + codeId + '">📋 Copy</button>' +
              '</div>' +
            '</div>' +
            '<pre><code>' + escapeHtml(codeContent) + '</code></pre>' +
          '</div>'
        );
        lastIndex = fenceRegex.lastIndex;
      }

      if (lastIndex < cleaned.length) {
        const tail = escapeHtml(cleaned.slice(lastIndex)).replace(/\\n/g, '<br/>');
        parts.push('<span>' + tail + '</span>');
      }

      return parts.join('');
    }

    function scrollToBottom() {
      scroller.scrollTop = scroller.scrollHeight;
    }

    scrollTopBtn.addEventListener('click', () => {
      scroller.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // Event delegation for code block buttons
    scroller.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-code-action]');
      if (!btn) return;
      const action = btn.getAttribute('data-code-action');
      const id = btn.getAttribute('data-code-id');
      const code = codeStore.get(id) || '';

      if (action === 'apply') {
        vscode.postMessage({ type: 'applyCode', code });
      } else if (action === 'diff') {
        vscode.postMessage({ type: 'diffCode', code });
      } else if (action === 'copy') {
        navigator.clipboard.writeText(code);
        btn.textContent = '✓ Copied';
        setTimeout(() => (btn.textContent = '📋 Copy'), 1500);
      }
    });

    // Quick action buttons
    document.querySelectorAll('[data-action]').forEach((btn) => {
      btn.addEventListener('click', () => {
        vscode.postMessage({ type: 'quickAction', action: btn.getAttribute('data-action') });
      });
    });

    document.getElementById('clearBtn').addEventListener('click', () => {
      vscode.postMessage({ type: 'clearChat' });
    });

    document.getElementById('refreshBtn').addEventListener('click', () => {
      vscode.postMessage({ type: 'refreshContext' });
    });

    function submitPrompt() {
      const text = promptInput.value.trim();
      if (!text) return;
      promptInput.value = '';
      vscode.postMessage({
        type: 'sendPrompt',
        prompt: text,
        agentMode: agentModeToggle.checked,
        includeContext: contextToggle.checked,
      });
    }

    sendBtn.addEventListener('click', submitPrompt);
    promptInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        submitPrompt();
      }
    });

    stopBtn.addEventListener('click', () => {
      vscode.postMessage({ type: 'stopGeneration' });
      stopBtn.style.display = 'none';
    });

    window.addEventListener('message', (event) => {
      const msg = event.data;
      switch (msg.type) {
        case 'statusUpdate': {
          const h = msg.health;
          if (h.online && h.modelAvailable) {
            statusDot.className = 'dot online';
            statusText.textContent = 'Ollama: ' + h.activeModel + ' (Online)';
          } else if (h.online) {
            statusDot.className = 'dot';
            statusText.textContent = 'Ollama Online (' + h.activeModel + ' missing)';
          } else {
            statusDot.className = 'dot offline';
            statusText.textContent = 'Ollama Offline';
          }
          const w = msg.workspace;
          fileTag.textContent = '📄 ' + (w.activeFile || 'No active file');
          if (w.hasSelection) {
            selTag.style.display = 'inline-block';
            selTag.textContent = '✂️ ' + w.selectionLines;
          } else {
            selTag.style.display = 'none';
          }
          if (w.diagnosticsCount > 0) {
            diagTag.style.display = 'inline-block';
            diagTag.textContent = '⚠️ ' + w.diagnosticsCount + ' problem(s)';
          } else {
            diagTag.style.display = 'none';
          }
          break;
        }

        case 'userMessage': {
          const div = document.createElement('div');
          div.className = 'msg user';
          const r = msg.route;
          div.innerHTML =
            '<div class="msg-header">' +
              '<strong>You</strong>' +
              '<span class="router-badge" title="Dynamic Task Router">' +
                escapeHtml(r.category) + ' • ' + r.confidence + '% (T=' + r.temperature + ')' +
              '</span>' +
            '</div>' +
            '<div>' + escapeHtml(msg.content).replace(/\\n/g, '<br/>') + '</div>';
          scroller.insertBefore(div, scrollTopBtn);
          scrollToBottom();
          break;
        }

        case 'streamStart': {
          stopBtn.style.display = 'inline-block';
          const div = document.createElement('div');
          div.className = 'msg assistant';
          div.innerHTML =
            '<div class="msg-header">' +
              '<strong>TAEL (Turn ' + msg.iteration + ')</strong>' +
              '<span class="router-badge" id="meta_' + msg.streamId + '">Streaming...</span>' +
            '</div>' +
            '<div id="body_' + msg.streamId + '">▋</div>';
          scroller.insertBefore(div, scrollTopBtn);
          activeStreams.set(msg.streamId, div);
          scrollToBottom();
          break;
        }

        case 'streamDelta': {
          const bodyEl = document.getElementById('body_' + msg.streamId);
          if (bodyEl) {
            bodyEl.innerHTML = renderMarkdownWithActions(msg.content);
            scrollToBottom();
          }
          break;
        }

        case 'streamDone': {
          stopBtn.style.display = 'none';
          const bodyEl = document.getElementById('body_' + msg.streamId);
          const metaEl = document.getElementById('meta_' + msg.streamId);
          if (bodyEl) {
            bodyEl.innerHTML = renderMarkdownWithActions(msg.content);
          }
          if (metaEl) {
            metaEl.textContent = msg.tokensPerSec + ' tok/s • ' + (msg.durationMs / 1000).toFixed(1) + 's';
          }
          scrollToBottom();
          break;
        }

        case 'streamError': {
          stopBtn.style.display = 'none';
          const bodyEl = document.getElementById('body_' + msg.streamId);
          if (bodyEl) {
            bodyEl.innerHTML = '<span style="color:var(--danger);">' + escapeHtml(msg.error) + '</span>';
          }
          break;
        }

        case 'toolStart': {
          const card = document.createElement('div');
          card.className = 'tool-card';
          card.innerHTML =
            '<div class="tool-title">' +
              '<span>🔧 Executing Tool: ' + escapeHtml(msg.toolName) + '</span>' +
              '<span>Running...</span>' +
            '</div>' +
            '<div class="tool-output">' + escapeHtml(JSON.stringify(msg.args)) + '</div>';
          scroller.insertBefore(card, scrollTopBtn);
          scrollToBottom();
          break;
        }

        case 'toolDone': {
          const card = document.createElement('div');
          card.className = 'tool-card ' + msg.status;
          const icon = msg.status === 'success' ? '✅' : '❌';
          card.innerHTML =
            '<div class="tool-title">' +
              '<span>' + icon + ' Tool Result: ' + escapeHtml(msg.toolName) + '</span>' +
              '<span>' + msg.durationMs + 'ms</span>' +
            '</div>' +
            '<div class="tool-output">' + escapeHtml(msg.output) + '</div>';
          scroller.insertBefore(card, scrollTopBtn);
          scrollToBottom();
          break;
        }

        case 'cleared': {
          scroller.querySelectorAll('.msg, .tool-card').forEach((el, idx) => {
            if (idx > 0) el.remove();
          });
          break;
        }
      }
    });
  </script>
</body>
</html>`;
  }
}
