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
exports.WorkspaceContextProvider = void 0;
const vscode = __importStar(require("vscode"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
class WorkspaceContextProvider {
    getWorkspaceRoot() {
        const folders = vscode.workspace.workspaceFolders;
        if (folders && folders.length > 0) {
            return folders[0].uri.fsPath;
        }
        const activeEditor = vscode.window.activeTextEditor;
        if (activeEditor && activeEditor.document.uri.scheme === 'file') {
            return path.dirname(activeEditor.document.uri.fsPath);
        }
        return process.cwd();
    }
    captureSnapshot() {
        const root = this.getWorkspaceRoot();
        const workspaceName = path.basename(root);
        let topLevelFiles = [];
        try {
            const entries = fs.readdirSync(root, { withFileTypes: true });
            topLevelFiles = entries
                .filter((e) => !['.git', 'node_modules', '__pycache__', '.venv', 'out'].includes(e.name))
                .slice(0, 30)
                .map((e) => (e.isDirectory() ? `${e.name}/` : e.name));
        }
        catch {
            topLevelFiles = [];
        }
        const editor = vscode.window.activeTextEditor;
        if (!editor || editor.document.uri.scheme !== 'file') {
            return {
                workspaceName,
                workspaceRoot: root,
                topLevelFiles,
                activeEditor: {
                    hasActiveEditor: false,
                    relativePath: '',
                    absolutePath: '',
                    languageId: '',
                    lineCount: 0,
                    cursorLine: 0,
                    hasSelection: false,
                    selectionStartLine: 0,
                    selectionEndLine: 0,
                    selectedText: '',
                    surroundingText: '',
                    diagnostics: [],
                },
            };
        }
        const doc = editor.document;
        const absPath = doc.uri.fsPath;
        const relPath = path.relative(root, absPath).replace(/\\/g, '/');
        const selection = editor.selection;
        const hasSelection = !selection.isEmpty;
        const selectedText = hasSelection ? doc.getText(selection) : '';
        const cursorLine = selection.active.line + 1;
        const startWindow = Math.max(0, selection.active.line - 20);
        const endWindow = Math.min(doc.lineCount - 1, selection.active.line + 20);
        const range = new vscode.Range(startWindow, 0, endWindow, doc.lineAt(endWindow).text.length);
        const surroundingText = doc.getText(range);
        // Collect Errors and Warnings from VS Code's language diagnostics
        const rawDiags = vscode.languages.getDiagnostics(doc.uri);
        const diagnostics = rawDiags
            .filter((d) => d.severity === vscode.DiagnosticSeverity.Error ||
            d.severity === vscode.DiagnosticSeverity.Warning)
            .slice(0, 10)
            .map((d) => {
            const sev = d.severity === vscode.DiagnosticSeverity.Error ? 'ERROR' : 'WARN';
            const line = d.range.start.line + 1;
            return `[${sev} Line ${line}] ${d.message}`;
        });
        return {
            workspaceName,
            workspaceRoot: root,
            topLevelFiles,
            activeEditor: {
                hasActiveEditor: true,
                relativePath: relPath,
                absolutePath: absPath,
                languageId: doc.languageId,
                lineCount: doc.lineCount,
                cursorLine,
                hasSelection,
                selectionStartLine: selection.start.line + 1,
                selectionEndLine: selection.end.line + 1,
                selectedText: selectedText.slice(0, 3500),
                surroundingText: surroundingText.slice(0, 2000),
                diagnostics,
            },
        };
    }
    /**
     * Builds a concise workspace context header for the prompt while respecting the 4096 token budget.
     */
    formatPromptContext(includeActiveFileCode = true) {
        const snap = this.captureSnapshot();
        const parts = [];
        parts.push(`[WORKSPACE CONTEXT]`);
        parts.push(`Workspace: ${snap.workspaceName} (${snap.workspaceRoot})`);
        if (snap.topLevelFiles.length > 0) {
            parts.push(`Top-Level Entries: ${snap.topLevelFiles.join(', ')}`);
        }
        const ae = snap.activeEditor;
        if (ae.hasActiveEditor) {
            parts.push(`Active File: ${ae.relativePath} (Language: ${ae.languageId}, Lines: ${ae.lineCount}, Cursor Line: ${ae.cursorLine})`);
            if (ae.diagnostics.length > 0) {
                parts.push(`Active File Diagnostics:\n${ae.diagnostics.join('\n')}`);
            }
            if (ae.hasSelection && ae.selectedText) {
                parts.push(`Selected Code (Lines ${ae.selectionStartLine}-${ae.selectionEndLine}):\n\`\`\`${ae.languageId}\n${ae.selectedText}\n\`\`\``);
            }
            else if (includeActiveFileCode && ae.surroundingText) {
                parts.push(`Code Near Cursor (Line ${ae.cursorLine}):\n\`\`\`${ae.languageId}\n${ae.surroundingText}\n\`\`\``);
            }
        }
        return parts.join('\n');
    }
}
exports.WorkspaceContextProvider = WorkspaceContextProvider;
//# sourceMappingURL=workspaceContext.js.map