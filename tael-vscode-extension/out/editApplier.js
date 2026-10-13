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
exports.EditApplier = exports.TaelDiffContentProvider = void 0;
const vscode = __importStar(require("vscode"));
class TaelDiffContentProvider {
    static scheme = 'tael-diff';
    contents = new Map();
    onDidChangeEmitter = new vscode.EventEmitter();
    onDidChange = this.onDidChangeEmitter.event;
    setContent(uri, content) {
        this.contents.set(uri.toString(), content);
        this.onDidChangeEmitter.fire(uri);
    }
    provideTextDocumentContent(uri) {
        return this.contents.get(uri.toString()) || '';
    }
}
exports.TaelDiffContentProvider = TaelDiffContentProvider;
class EditApplier {
    lastSuggestedCode = '';
    diffProvider;
    constructor(diffProvider) {
        this.diffProvider = diffProvider;
    }
    setLastSuggestedCode(code) {
        const extracted = EditApplier.extractFirstCodeBlock(code);
        this.lastSuggestedCode = extracted || code;
    }
    getLastSuggestedCode() {
        return this.lastSuggestedCode;
    }
    static extractFirstCodeBlock(markdown) {
        const match = markdown.match(/```(?:[a-zA-Z0-9_+-]*)?\r?\n([\s\S]*?)```/);
        if (match && match[1]) {
            return match[1].trimEnd();
        }
        return '';
    }
    /**
     * Applies the provided code (or last suggested code) to the active editor.
     * Replaces selection if non-empty; otherwise inserts at cursor position.
     */
    async applyToActiveEditor(rawCode, mode = 'auto') {
        const codeToApply = (rawCode ? EditApplier.extractFirstCodeBlock(rawCode) || rawCode : this.lastSuggestedCode).trimEnd();
        if (!codeToApply) {
            vscode.window.showWarningMessage('TAEL: No code block available to apply.');
            return false;
        }
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            // If no active editor is open, create a new untitled document with the code
            const doc = await vscode.workspace.openTextDocument({ content: codeToApply });
            await vscode.window.showTextDocument(doc);
            vscode.window.showInformationMessage('TAEL: Opened generated code in a new editor tab.');
            return true;
        }
        const selection = editor.selection;
        const success = await editor.edit((editBuilder) => {
            if (mode === 'replaceAll') {
                const fullRange = new vscode.Range(editor.document.positionAt(0), editor.document.positionAt(editor.document.getText().length));
                editBuilder.replace(fullRange, codeToApply);
            }
            else if (mode === 'insertAtCursor') {
                editBuilder.insert(selection.active, codeToApply);
            }
            else {
                // 'auto' or 'replaceSelection'
                if (!selection.isEmpty) {
                    editBuilder.replace(selection, codeToApply);
                }
                else {
                    editBuilder.insert(selection.active, codeToApply);
                }
            }
        });
        if (success) {
            vscode.window.showInformationMessage('TAEL: Successfully applied code edit to active editor.');
        }
        return success;
    }
    /**
     * Opens VS Code's native side-by-side Diff view comparing current selection/file vs TAEL's proposed code.
     */
    async previewDiff(proposedCode) {
        const code = (proposedCode ? EditApplier.extractFirstCodeBlock(proposedCode) || proposedCode : this.lastSuggestedCode).trimEnd();
        if (!code) {
            vscode.window.showWarningMessage('TAEL: No proposed code block to diff.');
            return;
        }
        const editor = vscode.window.activeTextEditor;
        const originalText = editor
            ? !editor.selection.isEmpty
                ? editor.document.getText(editor.selection)
                : editor.document.getText()
            : '';
        const ext = editor ? editor.document.fileName.split('.').pop() || 'txt' : 'txt';
        const leftUri = vscode.Uri.parse(`${TaelDiffContentProvider.scheme}:/original.${ext}`);
        const rightUri = vscode.Uri.parse(`${TaelDiffContentProvider.scheme}:/tael-proposed.${ext}`);
        this.diffProvider.setContent(leftUri, originalText);
        this.diffProvider.setContent(rightUri, code);
        await vscode.commands.executeCommand('vscode.diff', leftUri, rightUri, 'TAEL Diff Preview: Original ↔ Proposed Edit');
    }
}
exports.EditApplier = EditApplier;
//# sourceMappingURL=editApplier.js.map