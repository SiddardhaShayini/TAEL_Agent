# Contributing to TAEL-Agent

Thank you for your interest in contributing to **TAEL-Agent**! We welcome contributions from developers, researchers, and open-source enthusiasts.

TAEL-Agent is licensed under the permissive **[Apache 2.0 License](./LICENSE)**.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [How Can I Contribute?](#how-can-i-contribute)
3. [Development Environment Setup](#development-environment-setup)
4. [Project Architecture Overview](#project-architecture-overview)
5. [Adding a New Tool to `tael_tools`](#adding-a-new-tool-to-tael_tools)
6. [Extending the Dynamic Task Router](#extending-the-dynamic-task-router)
7. [Running Test Suites & Benchmarks](#running-test-suites--benchmarks)
8. [Pull Request & Git Workflow](#pull-request--git-workflow)

---

## Code of Conduct

All contributors and participants are expected to adhere to our **[Code of Conduct](./CODE_OF_CONDUCT.md)**. Please report any unacceptable behavior to **siddardhashayini9@gmail.com**.

---

## How Can I Contribute?

- **Report Bugs:** Open an issue with reproduction steps, system specifications (OS, RAM, CPU/GPU), and log outputs.
- **Suggest Features:** Propose new sandboxed tools, router heuristics, or VS Code features.
- **Implement Tools:** Expand `tael_tools/` with new developer tools (e.g., Docker inspection, linter runners, test runner integrations).
- **Benchmark & Capabilities:** Run `tael_benchmark_suite.py` on your machine and share performance metrics.
- **Improve Documentation:** Clarify guides, fix typos, or provide tutorials.

---

## Development Environment Setup

### 1. Fork & Clone Repository
```bash
git clone https://github.com/SiddardhaShayini/TAEL_Agent.git
cd TAEL_Agent
```

### 2. Python Environment Setup
```bash
# Recommended Python 3.10+
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt  # Or pip install llama-cpp-python
```

### 3. Local Ollama Model Setup
Download and install Ollama from [ollama.com](https://ollama.com/download), then register the local model:
```bash
python install_ollama_tael.py
```

### 4. VS Code Extension Setup (Optional)
If working on the VS Code extension:
```bash
cd tael-vscode-extension
npm install
npm run compile
npm test
```

---

## Project Architecture Overview

```text
TAEL_Agent/
├── tael_agent_runtime.py   # Autonomous execution loop (<tool_call> -> <tool_response>)
├── tael_router.py          # 9-domain Dynamic Task Router (Python)
├── tael_tools/             # Centralized Sandboxed Tool System
│   ├── base.py             # BaseTool abstract class & ToolResult
│   ├── security.py         # PathSandbox & CommandSandbox
│   ├── filesystem.py       # read_file, write_file, list_dir, search_text
│   ├── git.py              # git_status, git_diff, git_log, git_branch
│   └── execution.py        # execute_python, execute_terminal_command
├── tael_memory/            # 4-Pillar Persistent Memory & ContextBudget
├── tael-vscode-extension/  # TypeScript VS Code extension
├── Granite-Final-Agent-GGUF/ # Production GGUF model, Modelfile & HF Model Card
└── examples/               # Example Jupyter notebooks
```

---

## Adding a New Tool to `tael_tools`

All tools must inherit from `BaseTool` in [`tael_tools/base.py`](./tael_tools/base.py) and adhere to strict sandboxing:

1. **Inherit from `BaseTool`**:
   ```python
   from tael_tools.base import BaseTool, ToolResult

   class MyNewTool(BaseTool):
       def __init__(self, sandbox):
           super().__init__(
               name="my_new_tool",
               description="Describe what the tool does concisely for the 2B model.",
               parameter_schema={
                   "type": "object",
                   "properties": {
                       "param1": {"type": "string", "description": "Parameter description"}
                   },
                   "required": ["param1"]
               }
           )
           self.sandbox = sandbox

       def execute(self, **kwargs) -> ToolResult:
           # Always validate parameters and paths
           # Return ToolResult(status="success", output="...") or ToolResult(status="error", error="...")
   ```
2. **Register the Tool** in [`tael_tools/registry.py`](./tael_tools/registry.py).
3. **Add Unit Tests** in [`test_tool_system.py`](./test_tool_system.py).
4. **Mirror the Tool** in TypeScript if applicable ([`tael-vscode-extension/src/tools.ts`](./tael-vscode-extension/src/tools.ts)).

---

## Extending the Dynamic Task Router

The Dynamic Task Router maps user queries to one of 9 categories:
- `Programming`, `Debugging`, `Refactoring`, `SQL`, `Architecture`, `Git`, `Tool Use`, `Math`, `General Chat`.

To adjust scoring, add regex patterns or keywords to `CATEGORY_PROFILES` in [`tael_router.py`](./tael_router.py) and sync with [`tael-vscode-extension/src/router.ts`](./tael-vscode-extension/src/router.ts). Always run `python test_router.py` to ensure zero classification regressions.

---

## Running Test Suites & Benchmarks

Before opening a pull request, all automated test suites must pass:

```bash
# 1. Tool System Tests (11 tests)
python test_tool_system.py

# 2. Dynamic Task Router Tests (14 tests)
python test_router.py

# 3. Persistent Memory System Tests (8 tests)
python test_memory_system.py

# 4. VS Code Extension Tests (14 tests)
cd tael-vscode-extension && npm test && cd ..

# 5. Full SWE Benchmark Suite
python tael_benchmark_suite.py
```

---

## Pull Request & Git Workflow

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/my-cool-feature
   ```
2. Write clean, readable code with type annotations and docstrings.
3. Keep commits atomic and descriptive:
   - `feat: add docker_ps tool to tael_tools`
   - `fix: improve XML parser recovery for unescaped newlines`
   - `docs: update installation instructions for Linux`
4. Push your branch and submit a Pull Request to `main`.
5. Clearly describe the problem solved, testing performed, and any trade-offs.
