# Installation Guide (`INSTALL.md`)

This guide walks through installing and verifying **TAEL V2** across its three deployment interfaces:
1. **Local Ollama Runtime (`tael-agent`)**
2. **Python Autonomous Agent Runtime (`tael_agent_runtime.py`)**
3. **Visual Studio Code Extension (`tael-vscode-extension`)**

---

## 1. System Prerequisites & Hardware Requirements

### Hardware Requirements
- **System RAM:** **8 GB minimum** (`~2.0 GB` available free RAM required during inference); 16 GB recommended.
- **Processor:** 64-bit CPU with **AVX2** instruction set support (Intel Haswell / AMD Excavator or newer, or Apple Silicon M1/M2/M3).
- **Disk Space:** **2.0 GB** free space for the quantized GGUF model (`1.47 GB`), runtime scripts, and persistent memory store.
- **GPU:** None required (100% CPU execution supported out-of-the-box).

### Software Prerequisites
- **Python:** `3.10+` (`3.11` or `3.12` recommended)
- **Ollama:** `0.5.0+` (verified on `0.40.3`) — Download from [https://ollama.com/download](https://ollama.com/download)
- **Node.js & npm:** `v18+` or `v20+` (required only for building/testing the VS Code Extension)
- **Git:** `2.30+` (for Git tool integrations)

---

## 2. Verify the GGUF Model Artifact

Ensure the quantized GGUF model and `Modelfile` are present in `Granite-Final-Agent-GGUF/`:
```text
d:\TAEL_V2_Adaptive_AI\Granite-Final-Agent-GGUF\
├── granite-3.1-2b-instruct.Q4_K_M.gguf   (1,545,295,168 bytes / 1.47 GB)
└── Modelfile
```

---

## 3. Install & Verify Local Ollama Model (`tael-agent`)

### Option A: Automated 5-Stage Python Installer & Validator (Recommended)
From the repository root (`d:\TAEL_V2_Adaptive_AI`), run:
```powershell
python install_ollama_tael.py
```
This script automatically:
1. Validates the binary GGUF header (`GGUF` v3 magic bytes, `362` tensors, `36` KV pairs, SHA-256 checksum).
2. Validates `Granite-Final-Agent-GGUF/Modelfile` directives and ChatML template.
3. Checks the Ollama CLI and local daemon status.
4. Executes `ollama create tael-agent -f Modelfile`.
5. Runs live identity and Python coding verification prompts against `tael-agent` and writes `ollama_verification_report.json`.

### Option B: One-Click Windows PowerShell Installer
```powershell
powershell -ExecutionPolicy Bypass -File install_ollama.ps1
```

### Option C: Manual Ollama Registration
```powershell
cd Granite-Final-Agent-GGUF
ollama create tael-agent -f Modelfile
ollama show tael-agent
```

---

## 4. Install the Python Autonomous Agent Runtime

To run the standalone Python Agent Runtime (`tael_agent_runtime.py`), Dynamic Task Router (`tael_router.py`), Sandboxed Tool System (`tael_tools/`), Persistent Memory (`tael_memory/`), and Benchmark Suite (`tael_benchmark_suite.py`):

### 1. Install `llama-cpp-python`
```powershell
pip install llama-cpp-python
```
*(Tip for Windows users without a C++ compiler: install pre-built CPU AVX2 wheels using `pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu`)*

### 2. Run the Unit Test Suites
Verify that the Tool System, Dynamic Router, and Persistent Memory System pass all checks:
```powershell
python test_tool_system.py
python test_router.py
python test_memory_system.py
```

---

## 5. Install the VS Code Extension (`tael-vscode-extension`)

### 1. Install Dependencies & Compile TypeScript
```powershell
cd tael-vscode-extension
npm install
npm run compile
```

### 2. Run Extension Verification & Live Ollama Streaming Tests
```powershell
npm test
```
You should see `ALL 14/14 VS CODE EXTENSION TESTS PASSED!`.

### 3. Launch or Install in VS Code
- **Development Host (Instant):** Open `d:\TAEL_V2_Adaptive_AI\tael-vscode-extension` in VS Code and press **`F5`**.
- **Permanent Local Installation:** Copy or symlink the `tael-vscode-extension` folder into your VS Code extensions directory:
  ```powershell
  # Windows PowerShell
  Copy-Item -Path "d:\TAEL_V2_Adaptive_AI\tael-vscode-extension" -Destination "$HOME\.vscode\extensions\tael-ai.tael-vscode-extension-2.0.0" -Recurse -Force
  ```
  Then reload VS Code (`Ctrl+Shift+P` $\rightarrow$ `Developer: Reload Window`).

---

## 6. Troubleshooting

If you encounter port conflicts (`11434`), `file does not exist` errors during `ollama create`, or 8GB RAM memory pressure, consult **[OLLAMA_TROUBLESHOOTING.md](./OLLAMA_TROUBLESHOOTING.md)**.
