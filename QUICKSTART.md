# Quickstart Guide (`QUICKSTART.md`)

Get **TAEL V2** up and running in under 3 minutes across Ollama, the Autonomous Python Agent Runtime, and Visual Studio Code.

---

## 1. Quickstart: Local Ollama CLI (30 Seconds)

Register and verify `tael-agent` in Ollama:
```powershell
python install_ollama_tael.py
```

Start an interactive chat in your terminal:
```powershell
ollama run tael-agent
```

Or run a single-shot coding prompt:
```powershell
ollama run tael-agent "Write an O(n) Python function to find the first non-repeating character in a string."
```

> **Note:** Raw `ollama run` is a pure text-generation chat interface. To let TAEL autonomously create files, search your codebase, and run terminal commands, use the **Python Agent Runtime** (Section 2) or the **VS Code Extension** (Section 3) below!

---

## 2. Quickstart: Autonomous Agent Runtime (`tael_agent_runtime.py`)

The Python Agent Runtime connects the TAEL model to the **Dynamic Task Router**, **4-Pillar Persistent Memory**, and **10 Sandboxed Workspace Tools** (`read_file`, `write_file`, `list_dir`, `search_text`, `git_*`, `execute_python`, `execute_terminal_command`).

### Run an Autonomous Task from the Command Line
```powershell
# Note: If Ollama is currently holding the model in RAM on an 8GB laptop, stop it first:
ollama stop tael-agent

# Launch the interactive autonomous agent runtime:
python tael_agent_runtime.py
```

### Programmatic Usage in Python
```python
from tael_agent_runtime import TaelAgentRuntime

agent = TaelAgentRuntime(
    model_path="Granite-Final-Agent-GGUF/granite-3.1-2b-instruct.Q4_K_M.gguf",
    workspace_dir=".",
    n_ctx=4096,
    n_threads=6,
)

# TAEL automatically routes the task, emits <tool_call>, executes tools, and verifies output:
response = agent.execute_task(
    "Search for 'class TaskRouter' in the workspace and summarize the supported categories."
)
print(response)
```

---

## 3. Quickstart: VS Code Extension (`tael-vscode-extension`)

Make sure Ollama is serving (`ollama list`), then open the extension in VS Code:
```powershell
code tael-vscode-extension
```
Press **`F5`** to launch the **Extension Development Host**.

### Key Workflows Inside VS Code
1. **Open the TAEL Chat Panel (`Ctrl+Shift+T`):**
   - Click the **TAEL AI Assistant** icon on the Activity Bar.
   - Notice the live status indicator (`Ollama: tael-agent (Online)`), active file badge, and Dynamic Task Router badge (`Category • Confidence% • Temp`).
2. **Generate Code (`Ctrl+Shift+G`):**
   - Press `Ctrl+Shift+G` inside any file, describe what you want to build, and click **Apply to Editor** or **Preview Diff**.
3. **Refactor Selected Code (`Ctrl+Shift+R`):**
   - Highlight a nested or complex function, right-click $\rightarrow$ **TAEL: Refactor Selected Code**.
   - Click **`⇄ Diff`** on the generated code block to inspect a side-by-side comparison before clicking **`✓ Apply Edit`**.
4. **Explain Selected Code (`Ctrl+Shift+E`):**
   - Highlight any code block, right-click $\rightarrow$ **TAEL: Explain Selected Code** for an architectural and control-flow breakdown.
5. **Fix Compiler/Linter Problems (`🩺 Fix Problems`):**
   - Click **🩺 Fix Problems** in the TAEL toolbar to automatically feed active VS Code diagnostics (`vscode.languages.getDiagnostics`) to TAEL for root-cause resolution.
6. **Autonomous Agent Tools (`🤖 Agent Tools`):**
   - Keep **🤖 Agent Tools** checked in the chat panel and ask:
     *"Create a file `utils/validators.py` with an email validation regex function and test it."*
   - TAEL will emit `<tool_call>`, execute `write_file` inside your workspace sandbox, and report the `<tool_response>` card inline.

---

## 4. Quickstart: Run the Full SWE Benchmark Suite

To reproduce TAEL's **100% Pass Rate (8/8 domains)** across Python, SQL, Git, Terminal, Refactoring, Architecture, Tool Calling, and SWE Tasks:
```powershell
ollama stop tael-agent
python tael_benchmark_suite.py
```
View the generated report in **[benchmark_report.md](./benchmark_report.md)**.
