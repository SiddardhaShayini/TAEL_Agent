from datasets import load_dataset
import jsonlines
import random
import os
import json

os.makedirs("dataset", exist_ok=True)

print("Loading SWE-agent-trajectories from Hugging Face...")
print("Connecting to nebius/SWE-agent-trajectories (train split)...")

# Use streaming to avoid downloading all 80,000+ trajectories
swe_ds = load_dataset("nebius/SWE-agent-trajectories", split="train", streaming=True)

swe_data = []

print("Extracting successful end-to-end pull request resolutions (Target: 1,000)...")

for i, row in enumerate(swe_ds):
    if len(swe_data) >= 1000:
        break
        
    # FIX 1: The success condition in this specific dataset is called 'target', not 'resolved'
    if not row.get("target", False):
        continue
        
    raw_trajectory = row.get("trajectory") or row.get("messages") or []
    
    if isinstance(raw_trajectory, str):
        try: raw_trajectory = json.loads(raw_trajectory)
        except: continue
            
    if not raw_trajectory or not isinstance(raw_trajectory, list):
        continue

    formatted_convo = []
    is_first_user_turn = True
    
    for turn in raw_trajectory:
        role = turn.get("role", "")
        # Handle custom system prompt keys
        content = turn.get("content") or turn.get("value") or turn.get("system_prompt") or ""
        content_str = str(content).strip() if content else ""
        
        if role == "system":
            continue 
            
        # FIX 2: Nebius logs environment terminal outputs under the 'user' role
        elif role in ["user", "human"]:
            if is_first_user_turn:
                # The very first 'user' message is the GitHub Issue description
                formatted_convo.append({"from": "human", "value": content_str})
                is_first_user_turn = False
            else:
                # Subsequent 'user' messages are actually terminal/tool observations
                obs_str = content_str
                if "def " in obs_str or "class " in obs_str:
                    obs_str = f"<file_content>\n{obs_str}\n</file_content>"
                formatted_convo.append({"from": "observation", "value": obs_str})
            
        # FIX 3: Nebius logs the model's actions under the 'ai' role
        elif role in ["ai", "assistant", "gpt"]:
            action_str = content_str + "\n\n" if content_str else ""
            
            tool_calls = turn.get("tool_calls") or []
            for tc in tool_calls:
                func = tc.get("function") or {}
                name = func.get("name", "tool")
                args = func.get("arguments", "{}")
                action_str += f"Action: `{name}`\nArguments: {args}\n"
                    
            formatted_convo.append({"from": "gpt", "value": action_str.strip()})

    # Ensure it is a multi-step trajectory
    if len(formatted_convo) >= 4:
        swe_data.append({
            "id": f"swe_e2e_{row.get('instance_id', i)}",
            "conversations": formatted_convo
        })

print(f"Extracted {len(swe_data)} successful SWE-agent trajectories.")

random.seed(42)
random.shuffle(swe_data)

output_file = "dataset/11_swe_agent.jsonl"
print(f"Saving to {output_file}...")

with jsonlines.open(output_file, mode="w") as writer:
    writer.write_all(swe_data)

print("✅ Done! 11_swe_agent.jsonl is ready.")
print("🎉 THE GRANITE-CLAUDE-CODE DATASET IS COMPLETE! 🎉")
