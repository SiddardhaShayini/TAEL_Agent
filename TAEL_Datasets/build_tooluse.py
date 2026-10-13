from datasets import load_dataset
import jsonlines
import random
import os
import json

os.makedirs("dataset", exist_ok=True)

print("Loading AgentTrove dataset from Hugging Face...")
print("Connecting to open-thoughts/AgentTrove (streaming mode)...")
trove_ds = load_dataset("open-thoughts/AgentTrove", split="train", streaming=True)

tooluse_data = []

# Keywords specifically targeting codebase search, regex parsing, and in-place file editing
tool_keywords = [
    "grep ", "rg ", "ripgrep", "sed ", "awk ", "find ", 
    "xargs", "edit_file", "replace_in_file", "patch "
]

print("Scanning for Advanced Tool Use and File Editing trajectories (Target: 2,000)...")

for i, row in enumerate(trove_ds):
    if len(tooluse_data) >= 2000:
        break

    # Agnostic extraction for agent schemas
    raw_messages = row.get("conversations") or row.get("messages") or row.get("trajectory") or []
    
    if isinstance(raw_messages, str):
        try: raw_messages = json.loads(raw_messages)
        except: continue

    if not raw_messages or not isinstance(raw_messages, list):
        continue

    # Quick check: does this trajectory involve grep, rg, sed, or file patching tools?
    dumped_row = json.dumps(raw_messages).lower()
    has_tool_cmds = any(cmd in dumped_row for cmd in tool_keywords)
    
    if not has_tool_cmds:
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
                # Map the tool calls into our standardized Action format
                action_str += f"Action: `{name}`\nArguments: {args}\n"
                    
            formatted_convo.append({"from": "gpt", "value": action_str.strip()})
            
        elif role in ["tool", "observation", "environment"]:
            formatted_convo.append({"from": "observation", "value": content_str})

    # Ensure it's a valid multi-turn interaction
    if len(formatted_convo) >= 2:
        tooluse_data.append({
            "id": f"trove_tooluse_{i}",
            "conversations": formatted_convo
        })

print(f"Extracted {len(tooluse_data)} tool-use trajectories.")

# Set seed for reproducibility and shuffle
random.seed(42)
random.shuffle(tooluse_data)

output_file = "dataset/10_tooluse.jsonl"
print(f"Saving to {output_file}...")

with jsonlines.open(output_file, mode="w") as writer:
    writer.write_all(tooluse_data)

print("✅ Done! 10_tooluse.jsonl is ready. Your model is now trained to search codebases and mutate files.")
