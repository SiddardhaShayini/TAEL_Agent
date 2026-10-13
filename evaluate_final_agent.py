import os
import sys
import time
import json
from llama_cpp import Llama

MODEL_PATH = r"d:\TAEL_V2_Adaptive_AI\Granite-Final-Agent-GGUF\granite-3.1-2b-instruct.Q4_K_M.gguf"
OUTPUT_JSON = r"d:\TAEL_V2_Adaptive_AI\final_agent_evaluation.json"
OUTPUT_MD = r"d:\TAEL_V2_Adaptive_AI\final_agent_evaluation.md"

TEST_PROMPTS = [
    {
        "id": "domain_1_programming",
        "category": "01. Programming & Algorithms",
        "system": "You are TAEL, a specialized autonomous software engineering AI assistant.",
        "user": "Write a clean, production-grade Python function `find_kth_largest(nums: list[int], k: int) -> int` using the Quickselect algorithm with average O(n) time complexity. Include type annotations, docstring, and handling for edge cases."
    },
    {
        "id": "domain_2_debugging",
        "category": "02. Debugging & Error Diagnosis",
        "system": "You are TAEL, a specialized autonomous software engineering AI assistant.",
        "user": "Diagnose and fix the bug in this asynchronous Python code:\n\n```python\nimport asyncio\n\nasync def fetch_data(item_id):\n    await asyncio.sleep(0.1)\n    return f'data_{item_id}'\n\nasync def process_all(items):\n    results = []\n    for item in items:\n        results.append(fetch_data(item))\n    return await results\n```\n\nExplain why it fails with a TypeError and provide the corrected concurrent implementation using `asyncio.gather`."
    },
    {
        "id": "domain_3_refactoring",
        "category": "03. Code Refactoring & Clean Code",
        "system": "You are TAEL, a specialized autonomous software engineering AI assistant.",
        "user": "Refactor this deeply nested conditional function into clean, idiomatic Python using Guard Clauses and early returns:\n\n```python\ndef process_transaction(user, amount, account):\n    if user is not None:\n        if user.is_active:\n            if account is not None:\n                if account.balance >= amount:\n                    account.balance -= amount\n                    return {'status': 'success', 'new_balance': account.balance}\n                else:\n                    return {'status': 'error', 'message': 'Insufficient funds'}\n            else:\n                return {'status': 'error', 'message': 'Invalid account'}\n        else:\n            return {'status': 'error', 'message': 'Inactive user'}\n    else:\n        return {'status': 'error', 'message': 'User required'}\n```"
    },
    {
        "id": "domain_4_architecture",
        "category": "04. Software Architecture & Design",
        "system": "You are TAEL, a specialized autonomous software engineering AI assistant.",
        "user": "Outline the architecture for a lightweight local task-adaptive multi-agent coding system that runs on an 8GB RAM laptop. List the core components (Router, Context Engine, LLM Runtime, Tool Executors) and how they communicate with minimal RAM footprint."
    },
    {
        "id": "domain_5_terminal_git",
        "category": "05. Terminal Execution & Git Operations",
        "system": "You are TAEL, a specialized autonomous software engineering AI assistant.",
        "user": "A git branch `feature/payment` is 5 commits ahead of `main`, but `main` has advanced by 3 commits. Provide the exact sequence of git commands to rebase `feature/payment` onto `main`, resolve potential conflicts, and safely update the remote branch."
    },
    {
        "id": "domain_6_swe_tooluse",
        "category": "06. Tool Calling & SWE-Agent Trajectory",
        "system": "You are TAEL, a specialized autonomous software engineering AI assistant. When needing to inspect the environment, output structured tool calls in `<tool_call>` tags with parameters.",
        "user": "A bug was reported: 'test_auth.py fails with status 401 when token has expired'. What exact initial terminal commands and code search tools would you execute to investigate and reproduce this issue?"
    }
]

def run_evaluation():
    print("=" * 70)
    print("TAEL V2: GRANITE-FINAL-AGENT (3-PHASE CURRICULUM) EVALUATION")
    print("=" * 70)

    print(f"\nLoading model from: {MODEL_PATH}")
    t0 = time.time()
    llm = Llama(
        model_path=MODEL_PATH,
        n_ctx=2048,
        n_threads=6,
        verbose=False
    )
    load_time = time.time() - t0
    print(f"Model successfully loaded in {load_time:.2f}s\n")

    results = []

    for item in TEST_PROMPTS:
        pid = item["id"]
        category = item["category"]
        print(f"[{pid}] Running: {category}...")
        
        messages = [
            {"role": "system", "content": item["system"]},
            {"role": "user", "content": item["user"]}
        ]

        start_time = time.time()
        response = llm.create_chat_completion(
            messages=messages,
            temperature=0.2,
            max_tokens=650
        )
        elapsed = time.time() - start_time
        
        choice = response["choices"][0]
        content = choice["message"]["content"]
        usage = response.get("usage", {})
        completion_tokens = usage.get("completion_tokens", 0)
        prompt_tokens = usage.get("prompt_tokens", 0)
        tps = completion_tokens / elapsed if elapsed > 0 else 0
        
        print(f"  -> Generated {completion_tokens} tokens in {elapsed:.2f}s ({tps:.2f} t/s)")

        results.append({
            "id": pid,
            "category": category,
            "system_prompt": item["system"],
            "user_prompt": item["user"],
            "response": content,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "elapsed_seconds": round(elapsed, 2),
            "tokens_per_second": round(tps, 2)
        })

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "model_path": MODEL_PATH,
            "model_name": "Granite-Final-Agent-GGUF (Q4_K_M)",
            "load_time_seconds": round(load_time, 2),
            "results": results
        }, f, indent=2, ensure_ascii=False)
    print(f"\nJSON results saved to: {OUTPUT_JSON}")

    # Build Markdown Report
    md = "# TAEL V2: Granite-Final-Agent Comprehensive Evaluation Report\n\n"
    md += "## Executive Summary\n"
    md += f"- **Model Evaluated**: `Granite-Final-Agent-GGUF/granite-3.1-2b-instruct.Q4_K_M.gguf`\n"
    md += f"- **Model Size**: 1,473.71 MB (~1.47 GB)\n"
    md += f"- **Training Pipeline**: 3-Phase Progressive LoRA Curriculum (Unsloth, r=16, alpha=32) -> Merged FP16 -> Q4_K_M GGUF\n"
    md += f"- **Base Foundation Model**: `ibm-granite/granite-3.1-2b-instruct` (Apache 2.0 License)\n"
    md += f"- **Hardware Constraint**: 8GB RAM Laptop (Inference RAM footprint: ~1.5 GB, 0 Dedicated VRAM required)\n"
    md += f"- **Engine**: `llama.cpp` CPU (6 threads)\n\n"
    md += "---\n\n"
    md += "## Performance & Latency Metrics\n\n"
    md += "| Test Domain | Tokens Generated | Latency (s) | Throughput (tokens/sec) |\n"
    md += "| :--- | :--- | :--- | :--- |\n"
    for r in results:
        md += f"| **{r['category']}** | {r['completion_tokens']} | {r['elapsed_seconds']}s | {r['tokens_per_second']} t/s |\n"
    md += "\n---\n\n"
    md += "## Detailed Domain Evaluation Results\n\n"

    for r in results:
        md += f"### {r['category']}\n\n"
        md += f"**User Prompt:**\n> {r['user_prompt'].replace(chr(10), chr(10) + '> ')}\n\n"
        md += f"**Generation Metrics:** `{r['completion_tokens']} tokens` | `{r['elapsed_seconds']}s` | `{r['tokens_per_second']} t/s`\n\n"
        md += f"**Model Output:**\n\n```markdown\n{r['response']}\n```\n\n"
        md += "---\n\n"

    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Markdown report saved to: {OUTPUT_MD}")

if __name__ == "__main__":
    run_evaluation()
