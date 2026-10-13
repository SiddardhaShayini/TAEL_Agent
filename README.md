<p align="center">
  <img src="./assets/tael-logo.svg" alt="TAEL-Agent Logo" width="160" />
</p>

<h1 align="center">TAEL-Agent</h1>

<p align="center">
  <strong>Task-Adaptive Efficient Language Agent (v2.0.0-rc1)</strong><br />
  <em>An autonomous, local software engineering AI agent engineered for 8GB RAM consumer laptops without dedicated GPUs.</em>
</p>

<p align="center">
  <a href="./RELEASE_NOTES.md"><img src="https://img.shields.io/badge/Release-v2.0.0--rc1_(Release_Candidate_1)-blueviolet.svg" alt="Release: v2.0.0-rc1" /></a>
  <a href="./LICENSE"><img src="https://img.shields.io/badge/License-Apache_2.0-blue.svg" alt="License: Apache 2.0" /></a>
  <a href="./MODEL_CARD.md"><img src="https://img.shields.io/badge/Backbone-IBM_Granite_3.1_2B-0f62fe.svg" alt="Backbone: IBM Granite 3.1 2B" /></a>
  <a href="https://huggingface.co/SiddardhaShayini/TAEL_Agent"><img src="https://img.shields.io/badge/Hugging_Face-SiddardhaShayini%2FTAEL__Agent-ffcc00.svg" alt="Hugging Face Hub" /></a>
  <a href="./benchmark_report.md"><img src="https://img.shields.io/badge/SWE_Benchmark-100%25_Pass_(8%2F8)-brightgreen.svg" alt="Benchmark: 100% Pass" /></a>
  <a href="./CONTRIBUTING.md"><img src="https://img.shields.io/badge/PRs-Welcome-brightgreen.svg" alt="PRs Welcome" /></a>
  <a href="./CODE_OF_CONDUCT.md"><img src="https://img.shields.io/badge/Contributor_Covenant-v2.1-ff69b4.svg" alt="Code of Conduct" /></a>
</p>

---

**TAEL V2 (`v2.0.0-rc1`)** (**T**ask-**A**daptive **E**fficient **L**anguage) is a local, privacy-preserving, autonomous software engineering AI agent engineered to run smoothly on **8GB RAM consumer laptops without a dedicated GPU**.

Built on **IBM Granite 3.1 2B Instruct** (Apache 2.0) and fine-tuned across a **3-phase, 29,900-sample agentic software engineering curriculum**, TAEL combines a **1.47 GB 4-bit GGUF model** with a complete **Autonomous Agent Runtime**, **Dynamic Task Router**, **10 Sandboxed Workspace Tools**, **4-Pillar Persistent Memory System**, **Local Ollama Deployment**, and a full **Visual Studio Code Extension**.

- **GitHub Repository:** [https://github.com/SiddardhaShayini/TAEL_Agent](https://github.com/SiddardhaShayini/TAEL_Agent)
- **Hugging Face Model Hub (GGUF + Modelfile):** [https://huggingface.co/SiddardhaShayini/TAEL_Agent](https://huggingface.co/SiddardhaShayini/TAEL_Agent)

---

## Demo Screenshots

### 1. TAEL Visual Studio Code Extension (Chat, Router Badge, Sandboxed Tools & Diff Preview)
![TAEL VS Code Extension Demo](./assets/screenshots/vscode_extension_demo.svg)

### 2. Autonomous Agent Runtime & 5-Stage Ollama Verification
![TAEL CLI Agent Runtime Demo](./assets/screenshots/cli_agent_runtime_demo.svg)

### 3. 8-Domain SWE Benchmark Profile on 8GB RAM Hardware
![TAEL SWE Benchmark Results](./assets/screenshots/swe_benchmark_results.svg)

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [3-Phase Progressive Curriculum Training](#2-3-phase-progressive-curriculum-training)
3. [Dataset Sources (29,900 Samples)](#3-dataset-sources-29900-samples)
4. [Empirical Benchmarks & Performance](#4-empirical-benchmarks--performance)
5. [Hardware Requirements](#5-hardware-requirements)
6. [Safety & Sandboxing Architecture](#6-safety--sandboxing-architecture)
7. [Known Limitations](#7-known-limitations)
8. [Repository Structure & Release Documentation](#8-repository-structure--release-documentation)

---

## 1. System Architecture

TAEL V2 separates reasoning (**"The Brain"**) from deterministic execution, routing, and context management (**"The Hands & Memory"**):

```mermaid
flowchart TD
    User["Developer (CLI / Ollama / VS Code Extension)"] --> Router["Dynamic Task Router (tael_router.py / router.ts)"]
    Router -->|"Classifies into 9 Domains + Confidence Score"| Memory["4-Pillar Persistent Memory (tael_memory/)"]
    Memory -->|"BM25 Retrieval + 4096 Token ContextBudget"| Runtime["Agent Runtime Core (tael_agent_runtime.py)"]
    Runtime <-->|"ChatML Prompt / Stream"| Model["TAEL Brain: Granite 3.1 2B Q4_K_M GGUF (1.47 GB)"]
    Model -->|"Emits XML <tool_call>"| Parser["Fault-Tolerant XML Tool Parser"]
    Parser --> Sandbox["Security Layer (PathSandbox + CommandSandbox)"]
    Sandbox --> Tools["Centralized Tool Registry (10 Sandboxed Tools)"]
    Tools -->|"Wraps <tool_response>"| Runtime
```

### Core Subsystem Pillars

1. **TAEL Brain (`Granite-Final-Agent-GGUF/granite-3.1-2b-instruct.Q4_K_M.gguf`):**
   - 2.5B parameter transformer quantized to 4-bit `Q4_K_M` (`1,473.71 MB` on disk, `362` tensors).
   - Serves via `llama-cpp-python` or local **Ollama** (`tael-agent:latest`) at **14–23 tokens/sec** on CPU AVX2 threads.
2. **Dynamic Task Router (`tael_router.py` & `tael-vscode-extension/src/router.ts`):**
   - Classifies every incoming request across **9 specialized categories**: `Programming`, `Debugging`, `Refactoring`, `SQL`, `Architecture`, `Git`, `Tool Use`, `Math`, and `General Chat`.
   - Dynamically configures the **System Prompt**, **Allowed Tool Subset**, and **Sampling Hyperparameters** (`temperature` from `0.00` for Math up to `0.70` for General Chat) with calibrated confidence scoring and automatic fallback.
3. **Agent Runtime Core (`tael_agent_runtime.py`):**
   - Executes the autonomous multi-turn loop:
     `User → Model → Detect <tool_call> → Execute Sandboxed Tool → Wrap in <tool_response> → Send back to Model → Repeat until completion`.
   - Features streaming token output, automatic retry logic, and a fault-tolerant XML/JSON parser with heuristic quote/brace repair and implicit tool inference.
4. **Sandboxed Tool System (`tael_tools/`):**
   - Exposes **10 production workspace tools**: `read_file`, `write_file`, `list_dir`, `search_text`, `git_status`, `git_diff`, `git_log`, `git_branch`, `execute_python`, and `execute_terminal_command`.
   - Guarded by `PathSandbox` (strict workspace root confinement) and `CommandSandbox` (destructive command blacklist + `30s` execution timeout).
5. **4-Pillar Persistent Memory System (`tael_memory/`):**
   - **Conversation Memory:** Multi-turn session logs persisted in `.tael/memory/conversations/`.
   - **Project Memory:** Architectural decisions (ADRs) and project conventions in `.tael/memory/project_memory.json`.
   - **File Memory:** Tracks touched files, MD5 hashes, line counts, and AST symbols (`def`, `class`) in `.tael/memory/file_memory.json`.
   - **Summary Memory & `ContextBudget`:** Automatically compacts older dialogue turns when conversations exceed 8 turns or 1,500 tokens, strictly enforcing a `4,096`-token ceiling (`2,998` max input tokens + `1,024` reserved output tokens).
6. **VS Code Extension (`tael-vscode-extension/`):**
   - Full IDE integration featuring a Sidebar Chat Webview, Code Generation (`Ctrl+Shift+G`), Refactoring (`Ctrl+Shift+R`), Code Explanation (`Ctrl+Shift+E`), 1-Click Apply Edits, Native Side-by-Side Diff Previews (`tael-diff://`), Workspace & Diagnostic Awareness, and Autonomous Tool Execution.

---

## 2. 3-Phase Progressive Curriculum Training

To prevent catastrophic forgetting while teaching a 2B model both foundational coding rigor and multi-step SWE agent trajectories, TAEL V2 was trained using **Unsloth `FastLanguageModel` (QLoRA)** with rank $r = 16$, $\alpha = 32$ across all 7 linear projection layers (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`) using progressively decreasing learning rates:

| Training Phase | Artifact Directory | Dataset Composition | Samples | Learning Rate & Schedule | Objective |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **Phase 1: Foundation** | `Granite-Phase-1/` | Programming (15k) + Architecture (1k) + Testing (2k) | **18,000** | `2.0e-4` (`linear`, warmup 50, `adamw_8bit`) | Algorithmic implementation, type safety, system design, unit testing. |
| **Phase 2: Refinement** | `Granite-Phase-2/` | Debugging (2.4k) + Refactoring (2.0k) | **4,400** | `1.5e-4` (`cosine`, warmup 30, 1 epoch) | Stack trace diagnosis, root-cause analysis, Guard Clauses, SOLID refactoring. |
| **Phase 3: Agentic SWE** | `Granite-Final-Agent/` | Planning (2k) + Tool Use (2k) + Terminal (1k) + Git (1k) + SWE Agent (1k) + Repo (500) | **7,500** | `1.0e-4` (`cosine`, warmup 40, 1 epoch) | Multi-step trajectory planning, XML `<tool_call>` emission, bash & git workflows. |
| **Merge & Quantize** | `Granite-Final-Agent-GGUF/` | Merged FP16 (`4.8 GB`) $\rightarrow$ GGUF `Q4_K_M` (`1.47 GB`) | **29,900 Total** | Post-training 4-bit quantization | High-speed local CPU inference on 8GB RAM laptops. |

---

## 3. Dataset Sources (29,900 Samples)

All 11 dataset splits were generated and filtered via reproducible builder scripts in [`TAEL_Datasets/`](./TAEL_Datasets/):

| Split ID | File Name | Samples | Size | Primary Upstream Open-Source Sources |
| :--- | :--- | :---: | :---: | :--- |
| `01` | `01_programming.jsonl` | 15,000 | 23.8 MB | `bigcode/self-oss-instruct-sc2-exec-filter-50k`, `m-a-p/CodeFeedback-Filtered-Instruction` |
| `02` | `02_debugging.jsonl` | 2,400 | 6.9 MB | `nebius/SWE-agent-trajectories`, `m-a-p/CodeFeedback-Filtered-Instruction` |
| `03` | `03_refactoring.jsonl` | 2,000 | 5.7 MB | `m-a-p/CodeFeedback-Filtered-Instruction` |
| `04` | `04_repository.jsonl` | 500 | 0.4 MB | `tianyang/repobench_python_v1.1`, `nebius/SWE-agent-trajectories` |
| `05` | `05_planning.jsonl` | 2,000 | 198.8 MB | `SWE-bench/SWE-smith-trajectories` |
| `06` | `06_architecture.jsonl` | 1,000 | 3.6 MB | `m-a-p/CodeFeedback-Filtered-Instruction` |
| `07` | `07_testing.jsonl` | 2,000 | 2.8 MB | `bigcode/self-oss-instruct-sc2-exec-filter-50k` |
| `08` | `08_terminal.jsonl` | 1,000 | 25.1 MB | `open-thoughts/AgentTrove` |
| `09` | `09_git.jsonl` | 1,000 | 45.4 MB | `open-thoughts/AgentTrove` |
| `10` | `10_tooluse.jsonl` | 2,000 | 50.4 MB | `open-thoughts/AgentTrove` |
| `11` | `11_swe_agent.jsonl` | 1,000 | 1.0 MB | `nebius/SWE-agent-trajectories` |

---

## 4. Empirical Benchmarks & Performance

Evaluated via [`tael_benchmark_suite.py`](./tael_benchmark_suite.py) on an 8GB RAM CPU environment (6 CPU threads, AVX2, `Q4_K_M` GGUF). Full report available in [`benchmark_report.md`](./benchmark_report.md):

| Domain | Benchmark Task | Accuracy | Latency | Throughput | Tool Success | Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Python** | Optimal $O(n)$ Two Sum (3 live unit test assertions) | **100%** | 12.36s | 16.2 tok/s | N/A | **PASS** |
| **SQL** | Multi-table `JOIN`, `GROUP BY`, `HAVING`, `ORDER BY` on live SQLite | **100%** | 4.78s | 12.1 tok/s | N/A | **PASS** |
| **Git** | Interactive commit squashing (`git rebase -i HEAD~3`) | **100%** | 18.38s | 17.2 tok/s | N/A | **PASS** |
| **Terminal** | Large file search (`find +100M`), RAM (`free -h`), port PID (`lsof`) | **100%** | 15.99s | 16.6 tok/s | N/A | **PASS** |
| **Refactoring** | Deeply nested conditionals $\rightarrow$ flat Guard Clauses (4 test cases) | **100%** | 13.10s | 15.0 tok/s | N/A | **PASS** |
| **Architecture** | 100k events/sec Notification System (Kafka, Redis dedup, FCM/WS, DLQ) | **100%** | 24.82s | 16.5 tok/s | N/A | **PASS** |
| **Tool Calling** | Structured XML `<tool_call>` generation & schema validation | **100%** | 3.73s | 7.8 tok/s | **100%** | **PASS** |
| **SWE Tasks** | Autonomous file creation (`write_file`) + live subprocess unit test | **100%** | 7.93s | 12.2 tok/s | **100%** | **PASS** |
| **Aggregate** | **8 / 8 Domains Passed** | **100.0%** | **12.64s avg** | **14.21 tok/s avg** | **100.0%** | **PASS** |

### Subsystem Automated Test Suites
- **Tool System (`test_tool_system.py`):** `11 / 11` tests passed (`0.59s`)
- **Dynamic Task Router (`test_router.py`):** `14 / 14` tests passed (`0.013s`)
- **Persistent Memory System (`test_memory_system.py`):** `8 / 8` tests passed (`0.077s`)
- **Ollama 5-Stage Deployment (`install_ollama_tael.py`):** `5 / 5` stages passed (`100%`)
- **VS Code Extension (`test_vscode_extension.js`):** `14 / 14` tests passed (`23.01 tok/s` streaming)

---

## 5. Hardware Requirements

| Tier | CPU | System RAM | GPU | Disk Space | Expected Speed |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Minimum (Target)** | 4-core x86_64 CPU with AVX2 (Intel Core i5 / AMD Ryzen 5) | **8 GB RAM** (~2.1 GB used by TAEL) | **None required** (100% CPU inference) | **2.0 GB** (GGUF + Runtime) | `12 – 18 tok/s` |
| **Recommended** | 6–8 core modern CPU or Apple Silicon (M1/M2/M3) | **16 GB RAM** | Optional (CUDA / Metal / Vulkan) | **8.0 GB** (if storing FP16 merged weights) | `25 – 65+ tok/s` |

---

## 6. Safety & Sandboxing Architecture

Because TAEL is an autonomous agent capable of writing files and running commands, defense-in-depth safeguards are enforced at the runtime layer:

1. **Workspace Path Confinement (`PathSandbox`):**
   - Resolves canonical paths via `os.path.commonpath` (Python) and `path.relative` (TypeScript) to guarantee TAEL cannot read, write, list, or search any file outside the active project workspace root (`..` traversal and system paths like `C:\Windows` or `/etc` are strictly rejected).
   - Blocks access to sensitive credential files (`.env`, `.env.local`, `*.pem`, `*.key`).
2. **Destructive Command Blacklist (`CommandSandbox`):**
   - Intercepts and blocks dangerous shell patterns before subprocess creation: recursive forced deletions (`rm -rf /`, `del /f /q`, `rmdir /s`), disk formatting (`format`, `mkfs`, `diskpart`), system power states (`shutdown`, `reboot`), encoded payloads (`powershell -enc`, `curl ... | bash`), and fork bombs.
3. **Resource & Context Caps:**
   - All subprocess executions enforce a strict timeout (`15s–30s`) and output truncation (`10,000` characters) so runaway processes or huge logs cannot freeze the host machine or overflow the LLM context window.

---

## 7. Known Limitations

1. **2B Parameter Capacity Trade-offs:**
   - While TAEL achieves 100% pass rates on standard Python algorithms, SQL queries, Guard Clause refactoring, and single/multi-step workspace tool calls, it is a compact 2.5B model. Extremely complex combinatorial math puzzles or massive 50-file cross-repository refactors may require breaking tasks into smaller prompts.
2. **Implicit Tool Name Omission:**
   - Occasionally, the 2B model emits `<tool_call>{"path": "foo.py", "content": "..."}</tool_call>` without the explicit `"name": "write_file"` key. Both `tael_agent_runtime.py` and the VS Code extension's `XMLToolParser` include automatic schema-based tool inference to handle this transparently.
3. **Concurrent Dual-Engine RAM Usage on 8GB Machines:**
   - Loading the GGUF simultaneously in both the Ollama daemon and a separate `llama-cpp-python` process consumes `~3.6 GB` RAM total. On strict 8GB laptops, run `ollama stop tael-agent` before launching standalone `llama-cpp-python` benchmarks.

---

## 8. Repository Structure & Release Documentation

- **[RELEASE_NOTES.md](./RELEASE_NOTES.md):** Release Candidate 1 (`v2.0.0-rc1`) release notes, checksums, and milestone summary.
- **[QUICKSTART.md](./QUICKSTART.md):** Get TAEL running in under 3 minutes via Ollama, Python Agent CLI, or VS Code.
- **[INSTALL.md](./INSTALL.md):** Step-by-step installation guide for Windows, Linux, and macOS.
- **[MODEL_CARD.md](./MODEL_CARD.md):** Detailed model architecture, training hyperparameters, datasets, benchmarks, and ethical/safety analysis.
- **[FAQ.md](./FAQ.md):** Answers to common questions regarding architecture, tool execution, hardware limits, and licensing.
- **[OLLAMA_TROUBLESHOOTING.md](./OLLAMA_TROUBLESHOOTING.md):** Dedicated troubleshooting guide for local Ollama deployment.
- **[CONTRIBUTING.md](./CONTRIBUTING.md):** Open-source contributor guide, tool extension tutorial, and test suite instructions.
- **[CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md):** Contributor Covenant v2.1 code of conduct.
- **[SECURITY.md](./SECURITY.md):** Security policies, sandboxing guarantees, and vulnerability reporting.
- **[Example Notebook 1: Quickstart & Dynamic Router](./examples/01_tael_quickstart_and_routing.ipynb):** Interactive notebook demonstrating 9-category task routing and local Ollama inference.
- **[Example Notebook 2: Sandboxed Tools & Memory](./examples/02_autonomous_agent_and_tools.ipynb):** Interactive notebook demonstrating `tael_tools`, `PathSandbox`, and `tael_memory`.
- **[LICENSE](./LICENSE):** Official Apache License 2.0.
- **[project_memory.md](./project_memory.md):** Complete chronological engineering log and architectural decision record.

---

## 9. Contributing & Community

We welcome open-source contributions! Whether you are adding new tools to `tael_tools/`, tuning task routing heuristics in `tael_router.py`, expanding the VS Code extension, or reporting benchmarks across different hardware, check out **[CONTRIBUTING.md](./CONTRIBUTING.md)** to get started.

- **GitHub Issues:** [https://github.com/SiddardhaShayini/TAEL_Agent/issues](https://github.com/SiddardhaShayini/TAEL_Agent/issues)
- **Hugging Face Hub:** [https://huggingface.co/SiddardhaShayini/TAEL_Agent](https://huggingface.co/SiddardhaShayini/TAEL_Agent)
- **License:** [Apache 2.0](./LICENSE)


