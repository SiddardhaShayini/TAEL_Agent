# Frequently Asked Questions (`FAQ.md`)

## 1. General & Architecture

### Q1: Why did you choose IBM Granite 3.1 2B Instruct as the foundation model instead of a 7B or 14B model?
**Answer:** TAEL V2 was engineered specifically for **8GB RAM consumer laptops without a dedicated GPU**.
- A 7B or 8B model quantized to 4-bit requires `~4.8 GB – 5.5 GB` of RAM just for weights and KV cache, which causes severe swap thrashing or Out-Of-Memory (OOM) crashes when running alongside Windows 11 (`~3.5 GB`) and VS Code (`~1.2 GB`).
- **Granite 3.1 2B Instruct** quantized to `Q4_K_M` uses only **`1.47 GB` on disk (`~1.9 GB` in RAM)**, delivers **14–23 tokens/sec** on CPU threads, and carries a **100% permissive Apache 2.0 license** with no commercial revenue or user caps.

---

### Q2: Why did `ollama run tael-agent` output bash/code blocks instead of actually creating files on my disk?
**Answer:** An LLM `.gguf` file is only the **"Brain"**—it receives text tokens and predicts text tokens. Raw `ollama run` is a sandboxed chat REPL with zero filesystem or OS execution hooks.
To give TAEL **"Hands"** (just like GitHub Copilot Agent, Claude Code, or Antigravity) so it actually creates files, runs scripts, checks logs, and iterates:
1. Run the **Python Autonomous Agent Runtime** (`python tael_agent_runtime.py`), or
2. Use the **TAEL VS Code Extension** (`tael-vscode-extension`) with **🤖 Agent Tools** enabled.
Both parse `<tool_call>` XML tags emitted by TAEL, execute the tool inside the sandboxed workspace, wrap the result in `<tool_response>`, and feed it back to the model until the task is finished.

---

## 2. Training & Datasets

### Q3: Why was TAEL trained in 3 sequential phases instead of a single combined training run?
**Answer:** Fine-tuning a 2B parameter model on raw SWE-agent trajectories (`<tool_call>` XML) and foundational coding algorithms simultaneously with a single high learning rate causes gradient interference—the model either forgets clean Python/SQL syntax or fails to emit valid JSON inside `<tool_call>` tags.
By using a **3-Phase Progressive Curriculum** with monotonically decreasing learning rates:
- **Phase 1 (`lr = 2e-4`, 18,000 samples):** Builds deep competency in Programming, Architecture, and Unit Testing.
- **Phase 2 (`lr = 1.5e-4`, 4,400 samples):** Refines Debugging and Guard-Clause Refactoring without erasing Phase 1 knowledge.
- **Phase 3 (`lr = 1e-4`, 7,500 samples):** Teaches multi-step Planning, Git, Terminal, and `<tool_call>` SWE trajectories cleanly on top of the refined foundation.

---

### Q4: In which domains is TAEL most accurate and powerful?
**Answer:** Based on our automated benchmarks ([`benchmark_report.md`](./benchmark_report.md) and capability profiling):
- **Grade A+ (100% Benchmark Pass Rate):**
  - **Python Algorithms & Data Structures:** Optimal $O(n)$ implementations (Two Sum, Quickselect, Stack validation, recursion).
  - **SQL Queries:** Multi-table `JOIN`, `GROUP BY`, `HAVING`, and `ORDER BY` queries tested on live SQLite databases.
  - **Code Refactoring:** Converting deeply nested `if/else` trees into clean Guard Clauses while preserving 100% functional equivalence.
  - **System Architecture:** High-throughput distributed systems design (Kafka, Redis deduplication, WebSocket/FCM gateways, dead-letter queues).
  - **Workspace Tool Calling:** Emitting `<tool_call>` blocks for `search_text`, `read_file`, `write_file`, and `git_*` tools.
- **Areas Where Tool Assistance Helps Most:**
  - Complex combinatorics or multi-step arithmetic should use the `execute_python` tool so Python computes the exact numerical result.

---

## 3. Runtime, Memory & Safety

### Q5: How does TAEL prevent Context Window Overflow on long coding sessions?
**Answer:** The `tael_memory` package implements a strict **`ContextBudget`** tailored for a `4,096`-token window (`2,998` max input tokens + `1,024` reserved output tokens + `72` safety margin):
- **BM25 Relevance Retrieval (`MemoryRetriever`):** Injects *only* the project facts and tracked files relevant to your current prompt rather than dumping the entire workspace history.
- **Auto-Compaction (`SummaryMemory`):** Whenever conversation history exceeds 8 turns or 1,500 tokens, older turns are automatically compacted into a rolling executive summary while preserving the most recent turns verbatim.

---

### Q6: Can TAEL accidentally delete files outside my project or run dangerous shell commands?
**Answer:** No. Every tool call is validated by two mandatory security layers in both Python (`tael_tools/security.py`) and TypeScript (`tael-vscode-extension/src/tools.ts`):
- **`PathSandbox`:** Rejects any relative (`../../`) or absolute path that resolves outside the active project workspace root, and blocks sensitive credential files (`.env`, `.pem`, `.key`).
- **`CommandSandbox`:** Blocks destructive shell patterns (`rm -rf`, `del /f /q`, `rmdir /s`, `format`, `mkfs`, `shutdown`, fork bombs, and piped remote scripts) and enforces a strict execution timeout (`15s–30s`).

---

### Q7: How do I free RAM when switching between Ollama and standalone Python scripts on an 8GB laptop?
**Answer:** Run:
```powershell
ollama stop tael-agent
```
This immediately unloads `tael-agent` from the Ollama daemon, freeing `~1.85 GB` of RAM for standalone `llama-cpp-python` scripts like `tael_benchmark_suite.py` or `tael_agent_runtime.py`.
