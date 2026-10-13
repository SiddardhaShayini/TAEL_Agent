"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const ollamaClient_1 = require("./ollamaClient");
const workspaceContext_1 = require("./workspaceContext");
const tools_1 = require("./tools");
const editApplier_1 = require("./editApplier");
const chatViewProvider_1 = require("./chatViewProvider");
function activate(context) {
    const config = vscode.workspace.getConfiguration('tael');
    const baseUrl = config.get('ollamaBaseUrl', 'http://127.0.0.1:11434');
    const modelName = config.get('modelName', 'tael-agent');
    const numCtx = config.get('numCtx', 4096);
    const ollamaClient = new ollamaClient_1.OllamaClient(baseUrl, modelName, numCtx);
    const workspaceContext = new workspaceContext_1.WorkspaceContextProvider();
    const toolRegistry = new tools_1.ToolRegistry(workspaceContext.getWorkspaceRoot());
    const diffProvider = new editApplier_1.TaelDiffContentProvider();
    const editApplier = new editApplier_1.EditApplier(diffProvider);
    // Register virtual document provider for side-by-side Diff Previews
    context.subscriptions.push(vscode.workspace.registerTextDocumentContentProvider(editApplier_1.TaelDiffContentProvider.scheme, diffProvider));
    // Register Sidebar Webview Chat Panel
    const chatProvider = new chatViewProvider_1.TaelChatViewProvider(context.extensionUri, ollamaClient, workspaceContext, toolRegistry, editApplier);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider(chatViewProvider_1.TaelChatViewProvider.viewType, chatProvider, {
        webviewOptions: { retainContextWhenHidden: true },
    }));
    // Status Bar Item
    const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'tael.checkOllamaStatus';
    statusBarItem.text = `$(hubot) TAEL: ${modelName}`;
    statusBarItem.tooltip = 'TAEL Autonomous AI Coding Assistant (Local Ollama Runtime)';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    const refreshConfiguration = () => {
        const cfg = vscode.workspace.getConfiguration('tael');
        const url = cfg.get('ollamaBaseUrl', 'http://127.0.0.1:11434');
        const mdl = cfg.get('modelName', 'tael-agent');
        const ctx = cfg.get('numCtx', 4096);
        ollamaClient.updateConfig(url, mdl, ctx);
        statusBarItem.text = `$(hubot) TAEL: ${mdl}`;
    };
    context.subscriptions.push(vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration('tael')) {
            refreshConfiguration();
            void chatProvider.sendWorkspaceStatusToWebview();
        }
    }));
    // Keep workspace awareness updated when active file, selection, or diagnostics change
    context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor(() => {
        void chatProvider.sendWorkspaceStatusToWebview();
    }), vscode.window.onDidChangeTextEditorSelection(() => {
        void chatProvider.sendWorkspaceStatusToWebview();
    }), vscode.languages.onDidChangeDiagnostics(() => {
        void chatProvider.sendWorkspaceStatusToWebview();
    }));
    // 1. Focus Chat Command
    context.subscriptions.push(vscode.commands.registerCommand('tael.openChat', async () => {
        await vscode.commands.executeCommand('tael.chatView.focus');
    }));
    // 2. Generate Code Command
    context.subscriptions.push(vscode.commands.registerCommand('tael.generateCode', async () => {
        const instruction = await vscode.window.showInputBox({
            title: 'TAEL: Generate Code',
            placeHolder: 'Describe the function, class, or module to generate...',
            prompt: 'TAEL will generate code tailored to your active file and language.',
        });
        if (!instruction) {
            return;
        }
        const snap = workspaceContext.captureSnapshot();
        const lang = snap.activeEditor.hasActiveEditor ? snap.activeEditor.languageId : 'python';
        const prompt = `Write clean, production-ready ${lang} code for the following requirement:\n${instruction}\n\nProvide the complete code inside a fenced \`\`\`${lang} code block so it can be directly applied.`;
        await chatProvider.runPromptInPanel(`✨ Generate Code: ${instruction}`, prompt, false, true);
        const action = await vscode.window.showInformationMessage('TAEL finished generating code.', 'Apply to Editor', 'Preview Diff');
        if (action === 'Apply to Editor') {
            await editApplier.applyToActiveEditor(undefined, 'auto');
        }
        else if (action === 'Preview Diff') {
            await editApplier.previewDiff();
        }
    }));
    // 3. Refactor Selected Code Command
    context.subscriptions.push(vscode.commands.registerCommand('tael.refactorCode', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.selection.isEmpty) {
            vscode.window.showWarningMessage('TAEL: Please select a block of code in the editor to refactor.');
            return;
        }
        const selectedCode = editor.document.getText(editor.selection);
        const lang = editor.document.languageId;
        const customGoal = await vscode.window.showInputBox({
            title: 'TAEL: Refactor Selected Code',
            placeHolder: 'Optional: Specify refactoring goal (leave empty for Clean Code + Guard Clauses)',
            value: 'Refactor for readability, guard clauses, reduced nesting, and clean code principles while preserving exact behavior.',
        });
        if (!customGoal) {
            return;
        }
        const prompt = `Refactor the following ${lang} code from ${editor.document.fileName}:\nGoal: ${customGoal}\n\n\`\`\`${lang}\n${selectedCode}\n\`\`\`\n\nReturn the refactored code in a single fenced \`\`\`${lang} block followed by a brief summary of improvements.`;
        await chatProvider.runPromptInPanel(`🛠️ Refactor Selection (${lang})`, prompt, false, false);
        const action = await vscode.window.showInformationMessage('TAEL refactoring complete.', 'Apply Refactoring', 'Preview Diff');
        if (action === 'Apply Refactoring') {
            await editApplier.applyToActiveEditor(undefined, 'replaceSelection');
        }
        else if (action === 'Preview Diff') {
            await editApplier.previewDiff();
        }
    }));
    // 4. Explain Selected Code Command
    context.subscriptions.push(vscode.commands.registerCommand('tael.explainCode', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('TAEL: Open a file and select code to explain.');
            return;
        }
        const codeToExplain = !editor.selection.isEmpty
            ? editor.document.getText(editor.selection)
            : editor.document.getText();
        const lang = editor.document.languageId;
        const prompt = `Explain the following ${lang} code clearly. Cover:\n1. High-level purpose\n2. Step-by-step logic & control flow\n3. Time/space complexity or architectural notes\n\n\`\`\`${lang}\n${codeToExplain.slice(0, 3500)}\n\`\`\``;
        await chatProvider.runPromptInPanel(`📖 Explain Code (${lang})`, prompt, false, false);
    }));
    // 5. Fix Diagnostics / Problems Command
    context.subscriptions.push(vscode.commands.registerCommand('tael.fixDiagnostics', async () => {
        const snap = workspaceContext.captureSnapshot();
        if (!snap.activeEditor.hasActiveEditor) {
            vscode.window.showWarningMessage('TAEL: No active editor file to inspect.');
            return;
        }
        if (snap.activeEditor.diagnostics.length === 0) {
            vscode.window.showInformationMessage(`TAEL: No compiler or linter problems detected in ${snap.activeEditor.relativePath}.`);
            return;
        }
        const prompt = `Debug and fix the following diagnostics in ${snap.activeEditor.relativePath}:\n${snap.activeEditor.diagnostics.join('\n')}\n\nProvide the root-cause analysis and the corrected code block.`;
        await chatProvider.runPromptInPanel(`🩺 Fix ${snap.activeEditor.diagnostics.length} Problem(s) in ${snap.activeEditor.relativePath}`, prompt, false, true);
    }));
    // 6. Apply Last Suggested Edit Command
    context.subscriptions.push(vscode.commands.registerCommand('tael.applyEdit', async () => {
        await editApplier.applyToActiveEditor(undefined, 'auto');
    }));
    // 7. Run Autonomous Agent Task (With Tools)
    context.subscriptions.push(vscode.commands.registerCommand('tael.runAgentTask', async () => {
        const task = await vscode.window.showInputBox({
            title: 'TAEL: Run Autonomous Agent Task (With Tools)',
            placeHolder: 'e.g., Create a utility file math_utils.py with factorial(n) and verify it',
        });
        if (!task) {
            return;
        }
        await chatProvider.runPromptInPanel(`🤖 Agent Task: ${task}`, task, true, true);
    }));
    // 8. Check Local Ollama Status Command
    context.subscriptions.push(vscode.commands.registerCommand('tael.checkOllamaStatus', async () => {
        const status = await ollamaClient.checkStatus();
        await chatProvider.sendWorkspaceStatusToWebview();
        if (status.online && status.modelAvailable) {
            statusBarItem.text = `$(hubot) TAEL: ${status.activeModel} (Online)`;
            vscode.window.showInformationMessage(`TAEL Connected: Ollama is online at ${status.baseUrl} with model '${status.activeModel}'.`);
        }
        else if (status.online && !status.modelAvailable) {
            statusBarItem.text = `$(warning) TAEL: Model Missing`;
            vscode.window.showWarningMessage(`Ollama is running at ${status.baseUrl}, but model '${status.activeModel}' was not found. Run 'python install_ollama_tael.py' to register it.`);
        }
        else {
            statusBarItem.text = `$(error) TAEL: Ollama Offline`;
            vscode.window.showErrorMessage(`Cannot reach Ollama at ${status.baseUrl} (${status.error || 'Connection refused'}). Start Ollama with 'ollama serve'.`);
        }
    }));
    // 9. Clear History Command
    context.subscriptions.push(vscode.commands.registerCommand('tael.clearHistory', () => {
        chatProvider.clearConversation();
        vscode.window.showInformationMessage('TAEL: Conversation history cleared.');
    }));
}
function deactivate() {
    // Clean deactivation
}
//# sourceMappingURL=extension.js.map