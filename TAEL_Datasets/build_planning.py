from datasets import load_dataset
import jsonlines
import random
import os
import json

os.makedirs("dataset", exist_ok=True)
print("Loading SWE-Smith trajectories from Hugging Face...")

print("Connecting to SWE-bench/SWE-smith-trajectories (tool split)...")
smith_ds = load_dataset("SWE-bench/SWE-smith-trajectories", split="tool", streaming=True)

planning_data = []

print("Extracting Chain-of-Thought (CoT) planning episodes...")
for i, row in enumerate(smith_ds):
    if len(planning_data) >= 2000:
        break
        
    # Safeguard against explicit nulls using `or`
    raw_trajectory = row.get("trajectory") or row.get("messages") or row.get("history") or []
    
    if isinstance(raw_trajectory, str):
        try: raw_trajectory = json.loads(raw_trajectory)
        except: continue
            
    if not raw_trajectory or not isinstance(raw_trajectory, list):
        continue

    formatted_convo = []
    has_good_planning = False
    
    for turn in raw_trajectory:
        role = turn.get("role") or turn.get("from") or ""
        content = turn.get("content") or turn.get("value") or ""
        content_str = str(content).strip()
        
        if role in ["system"]:
            continue
        elif role in ["user", "human"]:
            formatted_convo.append({"from": "human", "value": content_str})
        elif role in ["assistant", "gpt"]:
            # If the model writes a long paragraph (CoT) before acting
            is_planning = len(content_str.split()) > 30
            action_str = ""
            
            if is_planning:
                has_good_planning = True
                if not content_str.lower().startswith("thought:"):
                    action_str += f"Thought: {content_str}\n\n"
                else:
                    action_str += f"{content_str}\n\n"
            else:
                action_str += f"{content_str}\n\n"
            
            # FIX: Handle case where 'tool_calls' is explicitly null in JSON
            tool_calls = turn.get("tool_calls") or []
            
            for tc in tool_calls:
                func = tc.get("function") or {}
                name = func.get("name", "tool")
                args = func.get("arguments", "{}")
                action_str += f"Action: `{name}`\nArguments: {args}\n"
                    
            formatted_convo.append({"from": "gpt", "value": action_str.strip()})
            
        elif role in ["tool", "observation", "environment"]:
            formatted_convo.append({"from": "observation", "value": content_str})

    if has_good_planning and len(formatted_convo) >= 2:
        planning_data.append({
            "id": f"swe_smith_plan_{i}",
            "conversations": formatted_convo
        })

random.seed(42)
random.shuffle(planning_data)

output_file = "dataset/05_planning.jsonl"
with jsonlines.open(output_file, mode="w") as writer:
    writer.write_all(planning_data)

print(f"✅ Done! Saved {len(planning_data)} examples to {output_file}.")
