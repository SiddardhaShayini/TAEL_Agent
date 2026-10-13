---
license: apache-2.0
base_model: ibm-granite/granite-3.1-2b-instruct
library_name: gguf
pipeline_tag: text-generation
language:
  - en
tags:
  - granite
  - gguf
  - q4_k_m
  - ollama
  - autonomous-agent
  - tool-use
  - code
  - software-engineering
  - unsloth
  - trl
datasets:
  - bigcode/self-oss-instruct-sc2-exec-filter-50k
  - m-a-p/CodeFeedback-Filtered-Instruction
  - nebius/SWE-agent-trajectories
  - SWE-bench/SWE-smith-trajectories
  - tianyang/repobench_python_v1.1
  - open-thoughts/AgentTrove
---

# TAEL-Agent (`v2.0.0-rc1`) — Granite 3.1 2B Instruct GGUF (`Q4_K_M`)

- **GitHub Repository (Agent Runtime, Tool System, Memory & VS Code Extension):** [https://github.com/SiddardhaShayini/TAEL_Agent](https://github.com/SiddardhaShayini/TAEL_Agent)
- **Hugging Face Model Repository:** [https://huggingface.co/SiddardhaShayini/TAEL_Agent](https://huggingface.co/SiddardhaShayini/TAEL_Agent)
- **Base Model:** `ibm-granite/granite-3.1-2b-instruct`
- **Quantization:** `Q4_K_M` (`1,473.71 MB` / `1.44 GiB` on disk)
- **License:** Apache 2.0

**TAEL-Agent** (**T**ask-**A**daptive **E**fficient **L**anguage) is an autonomous software engineering and coding AI model engineered to run smoothly on **8GB RAM consumer laptops without a dedicated GPU** (`14–23 tokens/sec` on CPU AVX2 threads).

---

## 1. Repository Files (`SiddardhaShayini/TAEL_Agent`)

| File | Size | Description |
| :--- | :---: | :--- |
| `granite-3.1-2b-instruct.Q4_K_M.gguf` | `1.47 GB` | 4-bit `Q4_K_M` quantized GGUF v3 model (`362` tensors, `36` KV metadata entries). |
| `Modelfile` | `1.0 KB` | Production Ollama `Modelfile` with ChatML template (`<|im_start|>`/`<|im_end|>`), `num_ctx 4096`, `temperature 0.2`, and stop tokens. |
| `config.json` | `850 B` | Model architecture configuration (`granite`, 32 layers, 2048 hidden size). |
| `README.md` | `6.5 KB` | This Hugging Face Model Card. |

---

## 2. Quickstart with Ollama

```bash
# 1. Download granite-3.1-2b-instruct.Q4_K_M.gguf and Modelfile into the same folder
ollama create tael-agent -f Modelfile

# 2. Run interactive session
ollama run tael-agent
```

---

## 3. Quickstart with `llama-cpp-python`

```python
from llama_cpp import Llama

llm = Llama(
    model_path="granite-3.1-2b-instruct.Q4_K_M.gguf",
    n_ctx=4096,
    n_threads=6,
    verbose=False,
)

resp = llm.create_chat_completion(
    messages=[
        {"role": "system", "content": "You are TAEL, an autonomous software engineering AI assistant."},
        {"role": "user", "content": "Write an O(n) Python function for Two Sum."}
    ],
    temperature=0.15,
    max_tokens=512,
)
print(resp["choices"][0]["message"]["content"])
```

---

## 4. 3-Phase Progressive Curriculum Fine-Tuning (`29,900` Samples)

Trained with **Unsloth `FastLanguageModel` (QLoRA)** ($r=16, \alpha=32$) across all projection modules (`q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj`) with progressively decreasing learning rates:

1. **Phase 1 — Foundation (`18,000` samples, `lr = 2e-4`):** Programming (15k), Software Architecture (1k), Unit Testing (2k).
2. **Phase 2 — Refinement (`4,400` samples, `lr = 1.5e-4`):** Debugging (2.4k) and Guard-Clause Refactoring (2.0k).
3. **Phase 3 — Agentic SWE (`7,500` samples, `lr = 1e-4`):** Multi-step Planning (2k), Tool Calling (2k), Terminal (1k), Git (1k), SWE-Agent (1k), Repository Context (500).

---

## 5. Benchmark Performance (`100% Pass Rate`)

Evaluated on an 8GB RAM CPU environment (6 CPU threads, AVX2):

| Domain | Task | Accuracy | Throughput | Verdict |
| :--- | :--- | :---: | :---: | :---: |
| **Python** | Optimal $O(n)$ Two Sum (3 live unit tests) | **100%** | 16.2 tok/s | **PASS** |
| **SQL** | Multi-table `JOIN`, `GROUP BY`, `HAVING`, `ORDER BY` (SQLite) | **100%** | 12.1 tok/s | **PASS** |
| **Git** | Interactive commit squashing (`git rebase -i HEAD~3`) | **100%** | 17.2 tok/s | **PASS** |
| **Terminal** | Large file search (`find +100M`), RAM (`free -h`), port PID (`lsof`) | **100%** | 16.6 tok/s | **PASS** |
| **Refactoring** | Deeply nested conditionals $\rightarrow$ flat Guard Clauses | **100%** | 15.0 tok/s | **PASS** |
| **Architecture** | 100k events/sec Notification System (Kafka, Redis, FCM/WS, DLQ) | **100%** | 16.5 tok/s | **PASS** |
| **Tool Calling** | Structured XML `<tool_call>` emission & schema check | **100%** | 7.8 tok/s | **PASS** |
| **SWE Tasks** | Autonomous file creation (`write_file`) + live subprocess unit test | **100%** | 12.2 tok/s | **PASS** |
