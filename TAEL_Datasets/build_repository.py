from datasets import load_dataset
import jsonlines
import random
import os
import json

os.makedirs("dataset", exist_ok=True)
print("Loading datasets from Hugging Face...")

# 1. Load RepoBench
print("Connecting to tianyang/repobench_python_v1.1 (cross_file_random split)...")
repobench_ds = load_dataset("tianyang/repobench_python_v1.1", split="cross_file_random", streaming=True)

# 2. Load SWE-agent trajectories
print("Connecting to nebius/SWE-agent-trajectories (train split)...")
swe_ds = load_dataset("nebius/SWE-agent-trajectories", split="train")

repobench_data = []
swe_data = []

print("Processing RepoBench...")
for i, row in enumerate(repobench_ds):
    if len(repobench_data) >= 1500:
        break
        
    # Agnostic extraction (handles various RepoBench formats)
    context = row.get("context", row.get("cross_file_context", ""))
    in_file = row.get("in_file", row.get("code", ""))
    target_code = row.get("next_line", row.get("target", ""))
    
    if not in_file or not target_code or not context:
        continue

    # Convert list context to string if necessary
    if isinstance(context, list):
        context = "\n".join(str(c) for c in context)

    # Build XML prompt
    human_prompt = "I need to complete the code in the current file. Here is the repository context:\n\n"
    human_prompt += f"<repository_context>\n{context}\n</repository_context>\n\n"
    human_prompt += f"Here is the current file:\n\n<file path=\"current_file.py\">\n{in_file}\n</file>\n\n"
    human_prompt += "Write the next logical block of code."

    repobench_data.append({
        "id": f"repo_bench_{i}",
        "conversations": [
            {"from": "human", "value": human_prompt.strip()},
            {"from": "gpt", "value": str(target_code).strip()}
        ]
    })

print("Processing SWE-agent-trajectories...")
for i, row in enumerate(swe_ds):
    if len(swe_data) >= 500:
        break
        
    # Drop explicit failures, but keep if 'resolved' key is missing
    if row.get("resolved") is False or row.get("status") == "failed":
        continue
        
    raw_trajectory = row.get("trajectory", row.get("messages", []))
    if isinstance(raw_trajectory, str):
        try: raw_trajectory = json.loads(raw_trajectory)
        except: continue
            
    if not raw_trajectory or not isinstance(raw_trajectory, list):
        continue

    formatted_convo = []
    
    for turn in raw_trajectory:
        # Agnostic role/content extraction
        role = turn.get("role", turn.get("from", ""))
        content = turn.get("content", turn.get("value", ""))
        
        if role in ["system"]:
            continue 
        elif role in ["user", "human"]:
            formatted_convo.append({"from": "human", "value": str(content)})
        elif role in ["assistant", "gpt"]:
            action_str = str(content) + "\n\n" if content else ""
            tool_calls = turn.get("tool_calls", [])
            for tc in tool_calls:
                name = tc.get("function", {}).get("name", "tool")
                args = tc.get("function", {}).get("arguments", "{}")
                action_str += f"Action: `{name}`\nArguments: {args}\n"
            formatted_convo.append({"from": "gpt", "value": action_str.strip()})
        elif role in ["tool", "observation", "environment"]:
            obs = str(content)
            if "def " in obs or "class " in obs: 
                obs = f"<file_content>\n{obs}\n</file_content>"
            formatted_convo.append({"from": "observation", "value": obs})
            
    if len(formatted_convo) > 2: # Ensure it's an actual multi-turn trajectory
        swe_data.append({
            "id": f"swe_repo_{i}",
            "conversations": formatted_convo
        })

random.seed(42)
final_repo_dataset = repobench_data + swe_data
random.shuffle(final_repo_dataset)

output_file = "dataset/04_repository.jsonl"
with jsonlines.open(output_file, mode="w") as writer:
    writer.write_all(final_repo_dataset)

print(f"✅ Done! Saved {len(final_repo_dataset)} examples to {output_file}.")
