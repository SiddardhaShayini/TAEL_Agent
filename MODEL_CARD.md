# Model Card: TAEL V2 (`Granite-Final-Agent-GGUF`)

## 1. Model Details

| Attribute | Specification |
| :--- | :--- |
| **Model Name** | **TAEL V2 (`tael-agent` / `Granite-Final-Agent-GGUF`)** |
| **Base Architecture** | `ibm-granite/granite-3.1-2b-instruct` (Decoder-only Transformer) |
| **Total Parameters** | ~2.53 Billion (`362` tensors, 32 layers, 2048 embedding dimension) |
| **Quantization Format** | GGUF v3 `Q4_K_M` (4-bit k-quants, medium) |
| **Model Footprint** | `1,545,295,168 bytes` (`1,473.71 MB` / `1.44 GiB` on disk) |
| **Context Window** | Native `131,072` tokens; configured to `4,096` tokens in production for 8GB RAM efficiency |
| **Chat Template** | ChatML (`<|im_start|>system`, `<|im_start|>user`, `<|im_start|>assistant`, `<|im_end|>`) |
| **Fine-Tuning Method** | 3-Phase Progressive Curriculum QLoRA via Unsloth ($r = 16$, $\alpha = 32$) |
| **License** | **Apache 2.0** (100% permissive commercial & open-source use) |

---

## 2. Intended Use

### Primary Intended Uses
- **Autonomous Local Software Engineering:** Reading, writing, searching, and executing code inside a sandboxed developer workspace without sending proprietary source code to external cloud APIs.
- **Algorithmic & Backend Code Generation:** Generating idiomatic Python, SQL, JavaScript/TypeScript, HTML/CSS, and shell scripts.
- **Code Refactoring & Bug Diagnosis:** Eliminating deep conditional nesting using Guard Clauses, diagnosing stack traces, and fixing linter/compiler diagnostics.
- **IDE Co-Pilot on Resource-Constrained Hardware:** Running inside Visual Studio Code (`tael-vscode-extension`) or terminal workflows on consumer laptops with only **8GB RAM** and no discrete GPU.

### Out-of-Scope Uses
- Executing unrestricted system administration commands outside a sandboxed workspace.
- High-stakes medical, legal, financial, or safety-critical industrial control decisions without human verification.
- Generating malicious software, exploit payloads, or bypassing security controls.

---

## 3. Training Process & Progressive Curriculum Architecture

Rather than mixing heterogeneous datasets into a single SFT pass—which degrades either general coding accuracy or structured XML tool calling—TAEL V2 was trained using a **3-Phase Progressive Curriculum** with monotonically decreasing learning rates (`2e-4` $\rightarrow$ `1.5e-4` $\rightarrow$ `1e-4`):

### LoRA Configuration (All 3 Phases)
- **Framework:** Unsloth `FastLanguageModel` + HuggingFace TRL `SFTTrainer`
- **LoRA Rank ($r$):** `16`
- **LoRA Alpha ($\alpha$):** `32`
- **Target Modules:** `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`
- **LoRA Dropout:** `0` (optimized for Unsloth fast kernels)
- **Optimizer:** `adamw_8bit`

### Phase Breakdown

1. **Phase 1 — Core Foundation & Software Architecture (`Granite-Phase-1`)**
   - **Input Weights:** `ibm-granite/granite-3.1-2b-instruct`
   - **Dataset:** `01_programming.jsonl` (15,000) + `06_architecture.jsonl` (1,000) + `07_testing.jsonl` (2,000) = **18,000 samples**
   - **Hyperparameters:** `learning_rate = 2e-4`, `lr_scheduler_type = "linear"`, `warmup_steps = 50`, `max_steps = 1000`
   - **Adapter Output:** `Granite-Phase-1/adapter_model.safetensors` (`107.6 MB`)

2. **Phase 2 — Code Refinement, Debugging & Refactoring (`Granite-Phase-2`)**
   - **Input Weights:** `Granite-Phase-1`
   - **Dataset:** `02_debugging.jsonl` (2,400) + `03_refactoring.jsonl` (2,000) = **4,400 samples**
   - **Hyperparameters:** `learning_rate = 1.5e-4`, `lr_scheduler_type = "cosine"`, `warmup_steps = 30`, `num_train_epochs = 1`
   - **Adapter Output:** `Granite-Phase-2/adapter_model.safetensors` (`107.6 MB`)

3. **Phase 3 — Agentic Autonomy, Tool Calling & SWE Workflows (`Granite-Final-Agent`)**
   - **Input Weights:** `Granite-Phase-2`
   - **Dataset:** `04_repository.jsonl` (500) + `05_planning.jsonl` (2,000) + `08_terminal.jsonl` (1,000) + `09_git.jsonl` (1,000) + `10_tooluse.jsonl` (2,000) + `11_swe_agent.jsonl` (1,000) = **7,500 samples**
   - **Hyperparameters:** `learning_rate = 1e-4`, `lr_scheduler_type = "cosine"`, `warmup_steps = 40`, `num_train_epochs = 1`
   - **Adapter Output:** `Granite-Final-Agent/adapter_model.safetensors` (`107.6 MB`)

4. **Weight Merging & GGUF Quantization**
   - Merged Phase 3 LoRA weights into 16-bit base weights (`Granite-Final-Agent-Merged/`, `4.8 GB`).
   - Quantized to GGUF `Q4_K_M` (`Granite-Final-Agent-GGUF/granite-3.1-2b-instruct.Q4_K_M.gguf`, `1.47 GB`).

---

## 4. Dataset Sources & Curation

The training corpus totals **29,900 curated instruction and multi-turn trajectory samples (~365 MB)** built via `TAEL_Datasets/build_*.py`:

- **Algorithmic & General Programming (17,000 samples):** Filtered from `bigcode/self-oss-instruct-sc2-exec-filter-50k` (execution-verified StarCoder2 instructions) and `m-a-p/CodeFeedback-Filtered-Instruction`.
- **Debugging, Refactoring & Architecture (5,400 samples):** Curated from `m-a-p/CodeFeedback-Filtered-Instruction` and `nebius/SWE-agent-trajectories`.
- **Multi-Step Planning & Repository Navigation (2,500 samples):** Extracted from `SWE-bench/SWE-smith-trajectories` and `tianyang/repobench_python_v1.1`.
- **Terminal, Git & Structured Tool Calling (5,000 samples):** Extracted and normalized into `<tool_call>` XML format from `open-thoughts/AgentTrove` and `nebius/SWE-agent-trajectories`.

---

## 5. Evaluation & Benchmark Results

### 5.1 Automated 8-Domain SWE Benchmark (`tael_benchmark_suite.py`)

Evaluated on an 8GB RAM Windows laptop (CPU inference, 6 threads, `Q4_K_M` GGUF):

| Category | Task Description | Verification Method | Accuracy | Latency | Throughput | Verdict |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: |
| **Python** | `two_sum` in $O(n)$ time | Live Python execution against 3 test cases | **100%** | 12.36s | 16.2 t/s | **PASS** |
| **SQL** | Multi-table `JOIN` + `GROUP BY` + `HAVING` | Live in-memory SQLite3 execution & row check | **100%** | 4.78s | 12.1 t/s | **PASS** |
| **Git** | Squash last 3 commits interactively | Command & rebase editor keyword verification | **100%** | 18.38s | 17.2 t/s | **PASS** |
| **Terminal** | Find files >100MB, RAM usage, port 8080 PID | Command flag & pipeline verification | **100%** | 15.99s | 16.6 t/s | **PASS** |
| **Refactoring** | Eliminate 5-level nested `if/else` with Guard Clauses | Live Python execution across 4 customer edge cases | **100%** | 13.10s | 15.0 t/s | **PASS** |
| **Architecture** | 100k events/sec real-time notification design | Component verification (Kafka, Redis, WS/FCM, DLQ) | **100%** | 24.82s | 16.5 t/s | **PASS** |
| **Tool Calling** | Emit `<tool_call>` for `search_text` | `XMLToolParser` extraction & JSON schema check | **100%** | 3.73s | 7.8 t/s | **PASS** |
| **SWE Tasks** | Create `temp_swe_benchmark_math.py` & test `factorial` | Sandboxed `write_file` execution + unit test run | **100%** | 7.93s | 12.2 t/s | **PASS** |

- **Overall Pass Rate:** `100.0% (8/8)`
- **Tool Execution Success Rate:** `100.0% (2/2)`
- **Mean CPU Throughput:** `14.21 tokens/sec` (`llama-cpp-python`), up to `23.01 tokens/sec` via Ollama HTTP streaming.

### 5.2 Empirical Domain Strength Profile

| Capability Tier | Domains | Empirical Observations |
| :--- | :--- | :--- |
| **Tier 1: Super-Powers (Grade A+)** | Python Algorithms, SQL Queries, Guard-Clause Refactoring, System Architecture, Single/Sequential Tool Calling | Generates clean, execution-verified code and accurate SQL joins on the first pass with zero schema hallucinations. |
| **Tier 2: Strong (Grade A-/B+)** | Stack Trace Debugging, Bash Diagnostics, Frontend HTML/CSS/JS | Accurately identifies bug causes and produces responsive layouts; complex async concurrency edge cases benefit from feeding back runtime tracebacks via `execute_python`. |
| **Tier 3: Assisted (Grade B)** | Advanced Combinatorics, Complex Multi-Branch Git Internals | Best paired with TAEL's `execute_python` tool (for exact math computation) and `git_*` inspection tools. |

---

## 6. Hardware Requirements & Resource Budget

Designed specifically for **8GB RAM laptops**:
- **Disk Footprint:** `1.47 GB` (`granite-3.1-2b-instruct.Q4_K_M.gguf`)
- **Runtime RAM Usage (4096 context):** `~1.85 GB – 2.15 GB` total RSS (Model weights + KV cache)
- **CPU Requirements:** x86_64 CPU with AVX2 support (4+ physical cores recommended) or Apple Silicon M-series
- **GPU Requirements:** None required (100% CPU compatible; supports optional CUDA/Metal offloading via Ollama or `llama.cpp`)

---

## 7. Known Limitations & Failure Modes

1. **Tool Call JSON Formatting Variance:** Under long context windows, a 2B model may occasionally omit the `"name"` field inside `<tool_call>{...}</tool_call>` (providing only `"path"` and `"content"`) or leave a trailing quote unclosed. Mitigation: `XMLToolParser` implements automatic JSON repair and implicit tool inference.
2. **Context Window Truncation on Massive Files:** To stay under 2.2 GB RAM on 8GB machines, the active context window is capped at `4,096` tokens. Reading a 5,000-line file in one chunk would overflow context. Mitigation: `read_file` enforces line-range slicing (`start_line`, `end_line`) and `tael_memory` enforces a strict `ContextBudget` (`max_input_tokens = 2998`) with automatic rolling summarization.
3. **Hallucination of Non-Existent CLI Flags:** On obscure UNIX utilities, the model may occasionally suggest flags from GNU coreutils on Windows PowerShell. Mitigation: The Dynamic Task Router and sandboxed `ToolRegistry` provide cross-platform native Python tools (`list_dir`, `search_text`, `read_file`, `write_file`).

---

## 8. Safety & Security Considerations

- **No Unrestricted Shell Access:** All model-generated `<tool_call>` requests pass through `PathSandbox` and `CommandSandbox` before touching the OS.
- **Zero External Telemetry:** TAEL runs 100% offline on local hardware via `llama.cpp` or local Ollama (`127.0.0.1:11434`). No source code, prompts, or file contents ever leave the user's machine.
- **Permissive Licensing Compliance:** Both the base model (`ibm-granite/granite-3.1-2b-instruct`) and the TAEL runtime/extension are licensed under **Apache 2.0**.
