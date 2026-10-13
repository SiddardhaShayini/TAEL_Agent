# TAEL VS Code Extension (`tael-vscode-extension`)

Local autonomous software engineering assistant for Visual Studio Code, powered by **TAEL (`tael-agent` / IBM Granite 3.1 2B Instruct Q4_K_M GGUF)** running on the **local Ollama runtime**.

---

## Core Features

1. **Interactive Sidebar Chat Panel (`tael.chatView`)**
   - Real-time token streaming from local Ollama (`http://127.0.0.1:11434/api/chat`).
   - Live **Dynamic Task Router** badges displaying detected category (`Programming`, `Refactoring`, `Debugging`, `SQL`, `Architecture`, `Git`, `Tool Use`, `Math`, `General Chat`), confidence percentage, and active sampling temperature.
   - Live throughput metrics (`tok/s` and latency) on every response.
   - Quick-action toolbar (`✨ Generate`, `🛠️ Refactor`, `📖 Explain`, `🩺 Fix Problems`, `🗑️ Clear`).

2. **Code Generation (`tael.generateCode` / `Ctrl+Shift+G`)**
   - Generates idiomatic, well-typed code tailored to the active editor's language and surrounding context.
   - Offers instant **Apply to Editor** or **Preview Diff** upon completion.

3. **Code Refactoring (`tael.refactorCode` / `Ctrl+Shift+R`)**
   - Refactors highlighted code using Guard Clauses, reduced cyclomatic complexity, and SOLID principles while preserving external behavior.

4. **Explain Code (`tael.explainCode` / `Ctrl+Shift+E`)**
   - Explains selected code or the active file (high-level purpose, step-by-step control flow, and algorithmic complexity).

5. **1-Click Apply Edits & Side-by-Side Diff Preview (`tael.applyEdit`)**
   - Every fenced code block in the Chat Panel features **✓ Apply Edit**, **⇄ Diff**, and **📋 Copy** buttons.
   - **⇄ Diff** opens VS Code's native side-by-side diff view (`tael-diff://`) comparing the original selection/file against TAEL's proposed changes before modifying your file.

6. **Autonomous Sandboxed Tool Execution (`ToolRegistry` & `XMLToolParser`)**
   - Supports multi-step `<tool_call>` $\rightarrow$ `<tool_response>` agent loops directly inside the VS Code workspace.
   - Exposes 10 sandboxed tools: `read_file`, `write_file`, `list_dir`, `search_text`, `git_status`, `git_diff`, `git_log`, `git_branch`, `execute_python`, and `execute_terminal_command`.
   - Protected by `PathSandbox` (blocks directory traversal outside workspace root and `.env`/`.pem` files) and `CommandSandbox` (blocks destructive shell commands).

7. **Workspace Awareness (`WorkspaceContextProvider`)**
   - Automatically tracks workspace root, top-level project files, active file path, language ID, selected lines, and active VS Code compiler/linter diagnostics (`vscode.languages.getDiagnostics`).

---

## Quick Start

### 1. Ensure Local Ollama & `tael-agent` Are Running
From the repository root (`d:\TAEL_V2_Adaptive_AI`):
```powershell
python install_ollama_tael.py
```

### 2. Compile & Test the Extension
```powershell
cd d:\TAEL_V2_Adaptive_AI\tael-vscode-extension
npm install
npm run compile
npm test
```

### 3. Launch in VS Code
- Open `d:\TAEL_V2_Adaptive_AI\tael-vscode-extension` in VS Code and press **`F5`** to launch the **Extension Development Host**, or:
- Symlink/copy `tael-vscode-extension` into `~/.vscode/extensions/tael-ai.tael-vscode-extension-2.0.0`.
