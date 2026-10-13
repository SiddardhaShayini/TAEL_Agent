from datasets import load_dataset
import jsonlines
import random
import os
import json

os.makedirs("dataset", exist_ok=True)

print("Hugging Face script execution blocked for CommitPackFT.")
print("Pivoting to AgentTrove to extract active Git CLI workflows...")

print("Connecting to open-thoughts/AgentTrove (streaming mode)...")
trove_ds = load_dataset("open-thoughts/AgentTrove", split="train", streaming=True)

git_data = []

# Keywords specifically targeting version control operations
git_commands = [
    "git status", "git add", "git commit", 
    "git push", "git clone", "git checkout", 
    "git branch", "git diff", "git pull"
]

print("Scanning for Git Version Control trajectories (Target: 1,000)...")

for i, row in enumerate(trove_ds):
    if len(git_data) >= 1000:
        break

    # Agnostic extraction for agent schemas
    raw_messages = row.get("conversations") or row.get("messages") or row.get("trajectory") or []
    
    if isinstance(raw_messages, str):
        try: raw_messages = json.loads(raw_messages)
        except: continue

    if not raw_messages or not isinstance(raw_messages, list):
        continue

    # Quick check: does this trajectory involve active git commands?
    dumped_row = json.dumps(raw_messages).lower()
    has_git_cmds = any(cmd in dumped_row for cmd in git_commands)
    
    if not has_git_cmds:
        continue

    formatted_convo = []
    
    for turn in raw_messages:
        role = turn.get("role") or turn.get("from") or ""
        content = turn.get("content") or turn.get("value") or ""
        content_str = str(content).strip() if content else ""
        
        if role in ["system"]:
            continue
            
        elif role in ["user", "human"]:
            formatted_convo.append({"from": "human", "value": content_str})
            
        elif role in ["assistant", "gpt"]:
            action_str = content_str + "\n\n" if content_str else ""
            
            tool_calls = turn.get("tool_calls") or []
            for tc in tool_calls:
                func = tc.get("function") or {}
                name = func.get("name", "tool")
                args = func.get("arguments", "{}")
                # Format the tool call for the model
                action_str += f"Action: `{name}`\nArguments: {args}\n"
                    
            formatted_convo.append({"from": "gpt", "value": action_str.strip()})
            
        elif role in ["tool", "observation", "environment"]:
            formatted_convo.append({"from": "observation", "value": content_str})

    # Ensure it's a valid multi-turn interaction
    if len(formatted_convo) >= 2:
        git_data.append({
            "id": f"trove_git_{i}",
            "conversations": formatted_convo
        })

print(f"Extracted {len(git_data)} Git trajectories.")

# Set seed for reproducibility and shuffle
random.seed(42)
random.shuffle(git_data)

output_file = "dataset/09_git.jsonl"
print(f"Saving to {output_file}...")

with jsonlines.open(output_file, mode="w") as writer:
    writer.write_all(git_data)

print("✅ Done! 09_git.jsonl is ready. Your model will now know how to autonomously use Git via the command line.")
