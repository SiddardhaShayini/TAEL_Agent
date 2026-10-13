import * as vscode from 'vscode';

export class TaelDiffContentProvider implements vscode.TextDocumentContentProvider {
  public static readonly scheme = 'tael-diff';
  private contents = new Map<string, string>();
  private onDidChangeEmitter = new vscode.EventEmitter<vscode.Uri>();
  public readonly onDidChange = this.onDidChangeEmitter.event;

  public setContent(uri: vscode.Uri, content: string): void {
    this.contents.set(uri.toString(), content);
    this.onDidChangeEmitter.fire(uri);
  }

  public provideTextDocumentContent(uri: vscode.Uri): string {
    return this.contents.get(uri.toString()) || '';
  }
}

export class EditApplier {
  private lastSuggestedCode: string = '';
  private diffProvider: TaelDiffContentProvider;

  constructor(diffProvider: TaelDiffContentProvider) {
    this.diffProvider = diffProvider;
  }

  public setLastSuggestedCode(code: string): void {
    const extracted = EditApplier.extractFirstCodeBlock(code);
    this.lastSuggestedCode = extracted || code;
  }

  public getLastSuggestedCode(): string {
    return this.lastSuggestedCode;
  }

  public static extractFirstCodeBlock(markdown: string): string {
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
  public async applyToActiveEditor(
    rawCode?: string,
    mode: 'auto' | 'replaceSelection' | 'insertAtCursor' | 'replaceAll' = 'auto'
  ): Promise<boolean> {
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
        const fullRange = new vscode.Range(
          editor.document.positionAt(0),
          editor.document.positionAt(editor.document.getText().length)
        );
        editBuilder.replace(fullRange, codeToApply);
      } else if (mode === 'insertAtCursor') {
        editBuilder.insert(selection.active, codeToApply);
      } else {
        // 'auto' or 'replaceSelection'
        if (!selection.isEmpty) {
          editBuilder.replace(selection, codeToApply);
        } else {
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
  public async previewDiff(proposedCode?: string): Promise<void> {
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

    await vscode.commands.executeCommand(
      'vscode.diff',
      leftUri,
      rightUri,
      'TAEL Diff Preview: Original ↔ Proposed Edit'
    );
  }
}
