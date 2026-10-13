from datasets import load_dataset
import jsonlines
import random
import os
import json

# Ensure target directory exists
os.makedirs("dataset", exist_ok=True)

print("Loading AgentTrove dataset from Hugging Face...")

# Use streaming=True because AgentTrove is enormous
print("Connecting to open-thoughts/AgentTrove (streaming mode)...")
# Note: AgentTrove typically uses the 'default' or 'train' split.
trove_ds = load_dataset("open-thoughts/AgentTrove", split="train", streaming=True)

terminal_data = []

# Keywords to ensure the trajectory is actually a Linux/Bash terminal task
terminal_keywords = ["bash", "shell", "terminal", "command line", "linux"]
linux_commands = ["ls -", "cat ", "mkdir ", "cd ", "pwd", "grep ", "chmod ", "rm -"]

print("Scanning for Bash/DevOps terminal trajectories (Target: 1,000)...")

for i, row in enumerate(trove_ds):
    if len(terminal_data) >= 1000:
        break

    # Agnostic extraction for agent schemas
    raw_messages = row.get("conversations") or row.get("messages") or row.get("trajectory") or []
    
    if isinstance(raw_messages, str):
        try: raw_messages = json.loads(raw_messages)
        except: continue

    if not raw_messages or not isinstance(raw_messages, list):
        continue

    # Quick check: does this trajectory involve terminal keywords?
    dumped_row = json.dumps(raw_messages).lower()
    has_terminal_context = any(kw in dumped_row for kw in terminal_keywords)
    has_linux_cmds = any(cmd in dumped_row for cmd in linux_commands)
    
    if not (has_terminal_context and has_linux_cmds):
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
                # Map bash/shell tools explicitly to our standard syntax
                action_str += f"Action: `{name}`\nArguments: {args}\n"
                    
            formatted_convo.append({"from": "gpt", "value": action_str.strip()})
            
        elif role in ["tool", "observation", "environment"]:
            formatted_convo.append({"from": "observation", "value": content_str})

    # Ensure it's a valid multi-turn interaction
    if len(formatted_convo) >= 2:
        terminal_data.append({
            "id": f"trove_term_{i}",
            "conversations": formatted_convo
        })

print(f"Extracted {len(terminal_data)} terminal trajectories.")

# Set seed for reproducibility and shuffle
random.seed(42)
random.shuffle(terminal_data)

output_file = "dataset/08_terminal.jsonl"
print(f"Saving to {output_file}...")

with jsonlines.open(output_file, mode="w") as writer:
    writer.write_all(terminal_data)

print("✅ Done! 08_terminal.jsonl is ready. Your model will now know how to navigate a Linux filesystem.")
