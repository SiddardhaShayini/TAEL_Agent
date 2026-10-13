# Release Notes — TAEL-Agent `v2.0.0-rc1` (Release Candidate 1)

> **Release Tag:** `v2.0.0-rc1`  
> **Status:** **Release Candidate 1 (RC1)**  
> **Release Date:** October 13, 2026  
> **License:** Apache 2.0  
> **GitHub Repository:** [https://github.com/SiddardhaShayini/TAEL_Agent](https://github.com/SiddardhaShayini/TAEL_Agent)  
> **Hugging Face Model Hub:** [https://huggingface.co/SiddardhaShayini/TAEL_Agent](https://huggingface.co/SiddardhaShayini/TAEL_Agent)  

---

## Overview

We are proud to announce **TAEL-Agent `v2.0.0-rc1` (Release Candidate 1)** — a complete, autonomous, local software engineering AI agent engineered to run smoothly on **8GB RAM consumer laptops without a dedicated GPU**.

TAEL (`Task-Adaptive Efficient Language`) combines a **3-phase fine-tuned IBM Granite 3.1 2B Instruct GGUF (`Q4_K_M`, 1.47 GB)** model with a full **Autonomous Agent Runtime**, **9-Category Dynamic Task Router**, **10 Sandboxed Workspace Tools**, **4-Pillar Persistent Memory System**, **Local Ollama Integration**, and a native **Visual Studio Code Extension**.

---

## Major Highlights in `v2.0.0-rc1`

### 1. 3-Phase Progressive Curriculum Fine-Tuning (`29,900` Samples)
- Trained using **Unsloth `FastLanguageModel` (QLoRA)** with rank $r = 16, \alpha = 32$ across all 7 projection layers (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`) and decreasing learning rates to eliminate catastrophic forgetting:
  - **Phase 1 (`Granite-Phase-1`, 18,000 samples, `lr = 2e-4`):** Foundation Programming (15k), Software Architecture (1k), and Unit Testing (2k).
  - **Phase 2 (`Granite-Phase-2`, 4,400 samples, `lr = 1.5e-4`):** Stack-trace Debugging (2.4k) and Guard-Clause Code Refactoring (2.0k).
  - **Phase 3 (`Granite-Final-Agent`, 7,500 samples, `lr = 1e-4`):** Multi-step Trajectory Planning (2k), Structured Tool Use (2k), Terminal/Bash (1k), Git Workflows (1k), SWE-Agent Bug Resolution (1k), and Repository Navigation (500).
- Quantized to **4-bit `Q4_K_M` GGUF (`1,473.71 MB`)**, requiring `< 2.1 GB` RAM at runtime with a `4,096`-token context window.

### 2. Autonomous Agent Runtime Core (`tael_agent_runtime.py`)
- Full multi-turn execution loop: `User → Model → Detect <tool_call> → Execute Sandboxed Tool → Wrap <tool_response> → Model`.
- Fault-tolerant `XMLToolParser` with automatic JSON quote/brace repair and implicit tool name inference (`path` + `content` $\rightarrow$ `write_file`).
- Real-time token streaming and automatic transient error retry.

### 3. Sandboxed Tool System (`tael_tools/`)
- **10 Workspace Tools:** `read_file`, `write_file`, `list_dir`, `search_text`, `git_status`, `git_diff`, `git_log`, `git_branch`, `execute_python`, and `execute_terminal_command`.
- **Defense-in-Depth Security:**
  - `PathSandbox`: Enforces strict workspace confinement (`os.path.commonpath`), blocking `..` traversal and credential files (`.env`, `.pem`, `.key`).
  - `CommandSandbox`: Blocks destructive shell commands (`rm -rf`, `del /f /q`, `format`, `mkfs`, `shutdown`, fork bombs) and enforces `30s` timeouts.

### 4. Dynamic Task Router (`tael_router.py`)
- Classifies prompts into **9 specialized categories** (`Programming`, `Debugging`, `Refactoring`, `SQL`, `Architecture`, `Git`, `Tool Use`, `Math`, `General Chat`).
- Dynamically selects domain-specific system prompts, filtered tool subsets, and sampling parameters (`temperature` from `0.00` for Math to `0.70` for General Chat) with calibrated confidence scoring.

### 5. 4-Pillar Persistent Memory System (`tael_memory/`)
- **Conversation Memory**, **Project Memory (ADRs)**, **File Memory (AST symbol tracking)**, and **Summary Memory**.
- Includes **BM25 Relevance Retrieval** and strict **`ContextBudget` overflow protection** (`max_input_tokens = 2998`, automatic rolling summarization after 8 turns or 1,500 tokens).

### 6. Local Ollama Integration (`tael-agent`)
- Hardened multi-turn ChatML [`Modelfile`](./Granite-Final-Agent-GGUF/Modelfile).
- Automated 5-stage Python validator & installer ([`install_ollama_tael.py`](./install_ollama_tael.py)) and PowerShell installer ([`install_ollama.ps1`](./install_ollama.ps1)).

### 7. Visual Studio Code Extension (`tael-vscode-extension/`)
- Interactive Sidebar Chat Panel (`Ctrl+Shift+T`), Code Generation (`Ctrl+Shift+G`), Refactoring (`Ctrl+Shift+R`), Code Explanation (`Ctrl+Shift+E`), 1-Click Apply Edits, Native Side-by-Side Diff Previews (`tael-diff://`), Workspace/Diagnostic Awareness, and Autonomous Tool Execution.

---

## Empirical Benchmark Verification (`100% Pass Rate`)

| Suite / Component | Tests Passed | Key Metric |
| :--- | :---: | :--- |
| **8-Domain SWE Benchmark (`tael_benchmark_suite.py`)** | **8 / 8 (100%)** | `100% Accuracy`, `100% Tool Success`, `14.21 tok/s` |
| **Sandboxed Tool System (`test_tool_system.py`)** | **11 / 11 (100%)** | `0.59s` execution |
| **Dynamic Task Router (`test_router.py`)** | **14 / 14 (100%)** | `0.013s` execution |
| **Persistent Memory System (`test_memory_system.py`)** | **8 / 8 (100%)** | `0.077s` execution |
| **Ollama 5-Stage Installer (`install_ollama_tael.py`)** | **5 / 5 (100%)** | `1.10s` identity response |
| **VS Code Extension (`test_vscode_extension.js`)** | **14 / 14 (100%)** | `23.01 tok/s` live Ollama streaming |

---

## Checksums & Artifacts (`v2.0.0-rc1`)

- **GGUF Model File:** `granite-3.1-2b-instruct.Q4_K_M.gguf`
  - **Size:** `1,545,295,168 bytes` (`1,473.71 MB`)
  - **GGUF Version:** `v3` (`362` tensors, `36` metadata KV pairs)
  - **First-1MB Header SHA-256:** `43f6e1b33c8b8ef6236b1079ec3c3a8c...`
