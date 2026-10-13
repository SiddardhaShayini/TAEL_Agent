# TAEL V2: Adaptive AI Startup Plan

## The Goal (Unchanged)
Build a specialized, adaptive AI assistant that excels in programming, reasoning, math, AI, ML, and internet search. It must be highly optimized to run locally on consumer hardware (as low as 8GB RAM laptops) while delivering top-tier performance. 

## The Pivot (The Strategy Change)
**Old Plan:** Train a custom architecture from scratch. (Failed: requires massive compute budget and billions of tokens to learn basic language).
**New Plan:** Fine-tune open-weight foundation models using QLoRA and DPO, and achieve "adaptivity" through dynamic system-level routing and Multi-LoRA architecture.

---

## 1. Foundation Model & Legal Strategy (Startup Ready)
To ensure the model can be used, modified, and monetized without legal friction, we strictly use foundation models with permissive open-source licenses.

*   **Selected Primary Foundation Model:**
    *   `IBM Granite 3.3 2B Instruct` (`ibm-granite/granite-3.3-2b-instruct`) — **License: Apache 2.0**
*   **Why IBM Granite 3.3 2B Instruct?**
    1.  **Fully Open Commercial License:** Apache 2.0 allows free commercial use, distribution, fine-tuning, and monetization with zero MAU or revenue constraints.
    2.  **Top-Tier Efficiency-to-Capability Ratio:** At 2 billion parameters, it punches well above its weight class in instruction-following, math, and code generation.
    3.  **Low Memory Footprint:** At Q4_K_M quantization, it occupies only ~1.5 GB RAM, leaving over 6 GB of RAM on an 8GB laptop for the OS and application runtime.
    4.  **Permissive Pretraining Data & Safety:** IBM published full data governance and safety transparency for the Granite family.

*   **Secondary / Specialized Candidates:**
    *   `Qwen2.5-Coder` (1.5B, 3B) — **License: Apache 2.0**
    *   `Phi-3-Mini` (3.8B) — **License: MIT**

---

## 2. Hardware Strategy (The 8GB RAM Constraint)
To run reliably on an 8GB laptop, the entire AI application (Model + OS + App UI + Router) must use less than ~5GB of RAM.

*   **Quantization:** All foundation models and adapters are exported to **GGUF format** (typically **Q4_K_M** or **Q5_K_M**).
    *   `Granite 3.3 2B` in Q4_K_M: **~1.5 GB RAM**.
    *   LoRA Adapters (Rank 8, Alpha 16): **~56 MB** each.
    *   OS Overhead: ~2.5 GB.
    *   Total Working Set: **< 4.5 GB RAM** (smooth performance on 8GB machines).
*   **Inference Engine:** `llama.cpp` (and `llama-cpp-python` / Ollama). Highly optimized C++ runtime utilizing AVX2/AVX-512 CPU instructions and optional GPU offloading, requiring no dedicated NVIDIA GPU to run at interactive speeds (>15 tokens/sec on modern laptop CPUs).

---

## 3. The "Adaptive" Architecture (Multi-LoRA)
Rather than maintaining multiple separate 7B+ models, TAEL achieves task-adaptivity using a **Base Brain + Dynamic Low-Rank Adapters (LoRAs)**:

1.  **The Base Brain:** Quantized `Granite 3.3 2B Instruct` stays loaded in RAM (~1.5 GB).
2.  **Task Expert Adapters:** Tiny adapters trained for specific domains:
    *   `adapter-code-dpo.gguf` (~56 MB) — Algorithmic problem solving and high-quality clean code generation (trained via Magicoder SFT + CodeUltraFeedback DPO).
    *   `adapter-math-logic.gguf` (~56 MB) — Step-by-step mathematical reasoning and chain-of-thought proofs.
    *   `adapter-web-search.gguf` (~56 MB) — Synthesis of retrieved search results and citation formatting.
3.  **The Classifier/Router:** A lightweight heuristic router or micro-classifier determines the task intent from the user query.
4.  **Dynamic LoRA Application:** `llama.cpp` applies the selected adapter weights dynamically at inference time without requiring model reloads or consuming significant additional memory.

---

## 4. Development Pipeline

### Phase A: Data Curation & Preprocessing
*   **SFT Dataset:** High-quality code/instruction datasets formatted into Granite chat templates (`ise-uiuc/Magicoder-OSS-Instruct-75K`).
*   **Preference Alignment Dataset:** Preference pairs with chosen/rejected solutions (`coseal/CodeUltraFeedback`) to steer the model towards clean, correct, and idiomatic answers.

### Phase B: Two-Stage Fine-Tuning (Free GPU Friendly)
*   **Stage 1: QLoRA SFT:** Base model loaded in 4-bit NF4 with BitsAndBytes; train rank-8 LoRA adapter across all projection layers (`q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`).
*   **Stage 2: Direct Preference Optimization (DPO):** Continue training the Stage 1 adapter using `DPOTrainer` (`beta=0.1`, `lr=5e-6`) to reinforce preferred coding patterns.

### Phase C: GGUF Conversion & Local Verification
*   Convert trained PEFT LoRA adapters to GGUF format using `llama.cpp/convert_lora_to_gguf.py`.
*   Verify inference using `llama.cpp` CLI / `llama-cpp-python` with base model + adapter.
*   Systematic benchmark comparisons against the un-tuned base model.

### Phase D: Local App & Adaptive Orchestration
*   Build lightweight desktop UI / CLI agent wrapper.
*   Integrate router for dynamic adapter switching and tool execution (code interpreter, internet search).

---
*“We change the plan but never the goal.”*
