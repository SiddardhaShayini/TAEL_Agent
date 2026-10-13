import * as fs from 'fs';
import * as path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

export interface ParsedToolCall {
  name: string;
  arguments: Record<string, unknown>;
  rawBlock: string;
}

export interface ToolExecutionResult {
  toolName: string;
  status: 'success' | 'error';
  output: string;
  durationMs: number;
  xmlResponse: string;
}

/**
 * Sandboxes file paths to ensure TAEL never reads or writes outside the active workspace root.
 */
export class PathSandbox {
  private workspaceRoot: string;

  constructor(workspaceRoot: string) {
    this.workspaceRoot = path.resolve(workspaceRoot);
  }

  public resolveSafePath(targetPath: string): string {
    const cleaned = (targetPath || '.').trim().replace(/^["']|["']$/g, '');
    const resolved = path.resolve(this.workspaceRoot, cleaned);

    const rel = path.relative(this.workspaceRoot, resolved);
    if (rel.startsWith('..') || path.isAbsolute(rel)) {
      throw new Error(`Security Sandbox Violation: Path '${targetPath}' resolves outside workspace root.`);
    }

    const baseName = path.basename(resolved).toLowerCase();
    if (baseName === '.env' || baseName === '.env.local' || baseName.endsWith('.pem') || baseName.endsWith('.key')) {
      throw new Error(`Security Sandbox Violation: Access to sensitive credential file '${baseName}' is blocked.`);
    }

    return resolved;
  }
}

/**
 * Sandboxes terminal commands to prevent destructive operations.
 */
export class CommandSandbox {
  private static readonly BLOCKED_PATTERNS: RegExp[] = [
    /\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive)\b/i,
    /\bdel\s+\/[fqs]/i,
    /\brmdir\s+\/s/i,
    /\bRemove-Item\b.*-Recurse/i,
    /\b(format|mkfs|fdisk|diskpart|shutdown|reboot|halt|poweroff)\b/i,
    /\breg\s+(delete|add)\b/i,
    /:\(\)\{\s*:\|:&\s*\};:/,
    /\b(curl|wget|Invoke-WebRequest)\b.*\|\s*(sh|bash|powershell|cmd|python)/i,
  ];

  public static validate(command: string): void {
    const trimmed = (command || '').trim();
    if (!trimmed) {
      throw new Error('Empty command is not allowed.');
    }
    for (const pattern of CommandSandbox.BLOCKED_PATTERNS) {
      if (pattern.test(trimmed)) {
        throw new Error(`Security Sandbox Violation: Command blocked by safety policy (${pattern}).`);
      }
    }
  }
}

/**
 * Fault-tolerant XML <tool_call> parser supporting JSON payloads, key-value recovery,
 * and implicit tool inference for 2B models.
 */
export class XMLToolParser {
  public static extractToolCalls(text: string): ParsedToolCall[] {
    if (!text || !text.includes('<tool_call>')) {
      return [];
    }

    const results: ParsedToolCall[] = [];
    const regex = /<tool_call>([\s\S]*?)(?:<\/tool_call>|$)/gi;
    let match: RegExpExecArray | null;

    while ((match = regex.exec(text)) !== null) {
      const rawBlock = match[0];
      let inner = match[1].trim();
      inner = inner.replace(/^```(?:json|xml|python|bash)?\s*/i, '').replace(/\s*```$/i, '').trim();

      const parsed = XMLToolParser.parseInnerPayload(inner, rawBlock);
      if (parsed) {
        results.push(parsed);
      }
    }

    return results;
  }

  private static parseInnerPayload(inner: string, rawBlock: string): ParsedToolCall | null {
    // 1. Try standard JSON parse
    const jsonCandidate = XMLToolParser.extractJsonObject(inner);
    if (jsonCandidate) {
      try {
        const obj = JSON.parse(jsonCandidate);
        const normalized = XMLToolParser.normalizeObject(obj);
        if (normalized) {
          return { ...normalized, rawBlock };
        }
      } catch {
        // Attempt repair of unescaped newlines inside JSON strings
        try {
          const repaired = jsonCandidate.replace(/\r?\n/g, '\\n');
          const obj = JSON.parse(repaired);
          const normalized = XMLToolParser.normalizeObject(obj);
          if (normalized) {
            return { ...normalized, rawBlock };
          }
        } catch {
          // Fall through to regex extraction
        }
      }
    }

    // 2. Fallback regex extraction for {"name": "...", "arguments": {...}}
    const nameMatch = inner.match(/["']?(?:name|tool)["']?\s*:\s*["']([a-zA-Z0-9_]+)["']/i);
    if (nameMatch) {
      const name = nameMatch[1];
      const args: Record<string, unknown> = {};
      const pathMatch = inner.match(/["']path["']\s*:\s*["']([^"']+)["']/);
      if (pathMatch) {
        args.path = pathMatch[1];
      }
      const queryMatch = inner.match(/["']query["']\s*:\s*["']([^"']+)["']/);
      if (queryMatch) {
        args.query = queryMatch[1];
      }
      const cmdMatch = inner.match(/["']command["']\s*:\s*["']([^"']+)["']/);
      if (cmdMatch) {
        args.command = cmdMatch[1];
      }
      return { name, arguments: args, rawBlock };
    }

    return null;
  }

  private static extractJsonObject(str: string): string | null {
    const start = str.indexOf('{');
    const end = str.lastIndexOf('}');
    if (start !== -1 && end !== -1 && end > start) {
      return str.slice(start, end + 1);
    }
    return null;
  }

  private static normalizeObject(obj: Record<string, unknown>): { name: string; arguments: Record<string, unknown> } | null {
    if (!obj || typeof obj !== 'object') {
      return null;
    }

    const explicitName = (obj.name || obj.tool || obj.function) as string | undefined;
    const rawArgs = (obj.arguments || obj.args || obj.parameters) as Record<string, unknown> | undefined;

    if (explicitName && typeof explicitName === 'string') {
      const args: Record<string, unknown> =
        rawArgs && typeof rawArgs === 'object'
          ? rawArgs
          : Object.fromEntries(Object.entries(obj).filter(([k]) => !['name', 'tool', 'function'].includes(k)));
      return { name: explicitName, arguments: args };
    }

    // Implicit tool inference when 2B model omits "name"
    if ('path' in obj && 'content' in obj) {
      return { name: 'write_file', arguments: obj };
    }
    if ('path' in obj && !('content' in obj) && !('query' in obj)) {
      return { name: 'read_file', arguments: obj };
    }
    if ('query' in obj) {
      return { name: 'search_text', arguments: obj };
    }
    if ('command' in obj) {
      return { name: 'execute_terminal_command', arguments: obj };
    }
    if ('code' in obj) {
      return { name: 'execute_python', arguments: obj };
    }

    return null;
  }
}

/**
 * Sandboxed TAEL Tool Registry for the VS Code Workspace
 */
export class ToolRegistry {
  private sandbox: PathSandbox;
  private workspaceRoot: string;

  constructor(workspaceRoot: string) {
    this.workspaceRoot = path.resolve(workspaceRoot);
    this.sandbox = new PathSandbox(this.workspaceRoot);
  }

  public setWorkspaceRoot(workspaceRoot: string): void {
    this.workspaceRoot = path.resolve(workspaceRoot);
    this.sandbox = new PathSandbox(this.workspaceRoot);
  }

  public async execute(call: ParsedToolCall): Promise<ToolExecutionResult> {
    const start = Date.now();
    try {
      const output = await this.dispatch(call.name, call.arguments);
      const durationMs = Date.now() - start;
      const xmlResponse = `<tool_response>\n${JSON.stringify(
        {
          tool: call.name,
          status: 'success',
          output,
        },
        null,
        2
      )}\n</tool_response>`;
      return {
        toolName: call.name,
        status: 'success',
        output,
        durationMs,
        xmlResponse,
      };
    } catch (err: unknown) {
      const durationMs = Date.now() - start;
      const errMsg = err instanceof Error ? err.message : String(err);
      const xmlResponse = `<tool_response>\n${JSON.stringify(
        {
          tool: call.name,
          status: 'error',
          error: errMsg,
        },
        null,
        2
      )}\n</tool_response>`;
      return {
        toolName: call.name,
        status: 'error',
        output: errMsg,
        durationMs,
        xmlResponse,
      };
    }
  }

  private async dispatch(name: string, args: Record<string, unknown>): Promise<string> {
    switch (name) {
      case 'read_file':
        return this.readFile(args);
      case 'write_file':
        return this.writeFile(args);
      case 'list_dir':
        return this.listDir(args);
      case 'search_text':
        return this.searchText(args);
      case 'git_status':
        return this.runGit('git status --short --branch');
      case 'git_diff':
        return this.runGit(args.staged ? 'git diff --staged' : 'git diff');
      case 'git_log': {
        const maxCount = Math.min(20, Math.max(1, Number(args.max_count || 5)));
        return this.runGit(`git log -n ${maxCount} --oneline`);
      }
      case 'git_branch':
        return this.runGit('git branch -a');
      case 'execute_python':
        return this.executePython(args);
      case 'execute_terminal_command':
        return this.executeTerminal(args);
      default:
        throw new Error(`Unknown tool '${name}'.`);
    }
  }

  private readFile(args: Record<string, unknown>): string {
    const filePath = this.sandbox.resolveSafePath(String(args.path || ''));
    if (!fs.existsSync(filePath)) {
      throw new Error(`File not found: ${args.path}`);
    }
    const content = fs.readFileSync(filePath, 'utf8');
    const lines = content.split(/\r?\n/);
    const startLine = Math.max(1, Number(args.start_line || 1));
    const endLine = Math.min(lines.length, Number(args.end_line || Math.min(lines.length, startLine + 250)));

    const sliced = lines
      .slice(startLine - 1, endLine)
      .map((line, idx) => `${startLine + idx}: ${line}`)
      .join('\n');

    return `File: ${args.path} (Lines ${startLine}-${endLine} of ${lines.length})\n${sliced}`;
  }

  private writeFile(args: Record<string, unknown>): string {
    const filePath = this.sandbox.resolveSafePath(String(args.path || ''));
    const content = String(args.content ?? '');
    fs.mkdirSync(path.dirname(filePath), { recursive: true });
    fs.writeFileSync(filePath, content, 'utf8');
    const bytes = Buffer.byteLength(content, 'utf8');
    return `Successfully wrote ${bytes} bytes to ${args.path}`;
  }

  private listDir(args: Record<string, unknown>): string {
    const dirPath = this.sandbox.resolveSafePath(String(args.path || '.'));
    if (!fs.existsSync(dirPath)) {
      throw new Error(`Directory not found: ${args.path || '.'}`);
    }
    const entries = fs.readdirSync(dirPath, { withFileTypes: true });
    const formatted = entries
      .filter((e) => !['.git', 'node_modules', '__pycache__', '.venv'].includes(e.name))
      .slice(0, 100)
      .map((e) => (e.isDirectory() ? `[DIR]  ${e.name}/` : `[FILE] ${e.name}`));
    return formatted.length > 0 ? formatted.join('\n') : '(Directory is empty)';
  }

  private searchText(args: Record<string, unknown>): string {
    const query = String(args.query || args.pattern || '').trim();
    if (!query) {
      throw new Error('search_text requires a non-empty "query" parameter.');
    }
    const rootDir = this.sandbox.resolveSafePath(String(args.path || '.'));
    const matches: string[] = [];
    const lowerQuery = query.toLowerCase();

    const walk = (dir: string) => {
      if (matches.length >= 40) {
        return;
      }
      let entries: fs.Dirent[] = [];
      try {
        entries = fs.readdirSync(dir, { withFileTypes: true });
      } catch {
        return;
      }
      for (const entry of entries) {
        if (matches.length >= 40) {
          return;
        }
        if (['.git', 'node_modules', '__pycache__', 'out', 'dist', 'Granite-Final-Agent-GGUF', 'Granite-Final-Agent-Merged', 'TAEL_Datasets'].includes(entry.name)) {
          continue;
        }
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          walk(fullPath);
        } else if (entry.isFile()) {
          try {
            const stat = fs.statSync(fullPath);
            if (stat.size > 1024 * 512) {
              continue; // Skip files > 512KB
            }
            const text = fs.readFileSync(fullPath, 'utf8');
            const lines = text.split(/\r?\n/);
            for (let i = 0; i < lines.length; i++) {
              if (lines[i].toLowerCase().includes(lowerQuery)) {
                const rel = path.relative(this.workspaceRoot, fullPath).replace(/\\/g, '/');
                matches.push(`${rel}:${i + 1}: ${lines[i].trim().slice(0, 140)}`);
                if (matches.length >= 40) {
                  break;
                }
              }
            }
          } catch {
            // Ignore binary/unreadable files
          }
        }
      }
    };

    if (fs.statSync(rootDir).isFile()) {
      const text = fs.readFileSync(rootDir, 'utf8');
      const lines = text.split(/\r?\n/);
      const rel = path.relative(this.workspaceRoot, rootDir).replace(/\\/g, '/');
      lines.forEach((line, i) => {
        if (line.toLowerCase().includes(lowerQuery) && matches.length < 40) {
          matches.push(`${rel}:${i + 1}: ${line.trim().slice(0, 140)}`);
        }
      });
    } else {
      walk(rootDir);
    }

    return matches.length > 0
      ? `Found ${matches.length} match(es) for "${query}":\n${matches.join('\n')}`
      : `No matches found for "${query}".`;
  }

  private async runGit(cmd: string): Promise<string> {
    const { stdout, stderr } = await execAsync(cmd, {
      cwd: this.workspaceRoot,
      timeout: 10000,
    });
    return (stdout || stderr || '(No git output)').trim();
  }

  private async executePython(args: Record<string, unknown>): Promise<string> {
    const code = String(args.code || '').trim();
    if (!code) {
      throw new Error('execute_python requires a non-empty "code" parameter.');
    }
    CommandSandbox.validate(code);
    const escaped = code.replace(/"/g, '\\"');
    const { stdout, stderr } = await execAsync(`python -c "${escaped}"`, {
      cwd: this.workspaceRoot,
      timeout: 15000,
    });
    return (stdout + (stderr ? `\n[STDERR]\n${stderr}` : '')).trim() || '(Executed with no output)';
  }

  private async executeTerminal(args: Record<string, unknown>): Promise<string> {
    const command = String(args.command || '').trim();
    CommandSandbox.validate(command);
    const { stdout, stderr } = await execAsync(command, {
      cwd: this.workspaceRoot,
      timeout: 15000,
    });
    return (stdout + (stderr ? `\n[STDERR]\n${stderr}` : '')).trim() || '(Command completed with exit code 0)';
  }
}
