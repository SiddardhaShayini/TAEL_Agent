from datasets import load_dataset
import jsonlines
import random
import os
import json

# Ensure target directory exists
os.makedirs("dataset", exist_ok=True)

print("Loading datasets from Hugging Face... (This may take a moment for SWE-agent)")

# 1. Load CodeFeedback
codefeedback_ds = load_dataset("m-a-p/CodeFeedback-Filtered-Instruction", split="train")

# 2. Load SWE-agent trajectories
swe_ds = load_dataset("nebius/SWE-agent-trajectories", split="train")

codefeedback_data = []
swe_data = []

# Keywords that indicate a debugging task
debug_keywords = ["fix", "bug", "traceback", "error", "issue", "crash", "exception", "fail", "not working"]

print("Processing CodeFeedback dataset (Target: 2,400)...")
for i, row in enumerate(codefeedback_ds):
    query = row.get("query", "")
    answer = row.get("answer", "")
    
    if not query or not answer:
        continue
        
    # Only keep queries that contain debugging keywords
    if any(keyword in query.lower() for keyword in debug_keywords):
        codefeedback_data.append({
            "id": f"cf_debug_{i}",
            "conversations": [
                {"from": "human", "value": query},
                {"from": "gpt", "value": answer}
            ]
        })

print("Processing SWE-agent-trajectories (Target: 1,600 successful episodes)...")
for i, row in enumerate(swe_ds):
    # CRITICAL: We only want trajectories where the agent successfully fixed the bug
    if not row.get("resolved", False):
        continue
        
    raw_trajectory = row.get("trajectory", []) 
    
    # If the trajectory is stored as a JSON string, parse it
    if isinstance(raw_trajectory, str):
        try:
            raw_trajectory = json.loads(raw_trajectory)
        except:
            continue
            
    if not raw_trajectory:
        continue
        
    formatted_convo = []
    
    # Map SWE-agent roles to ShareGPT roles
    for turn in raw_trajectory:
        role = turn.get("role", "")
        content = turn.get("content", "")
        
        if role == "system":
            # Skip system prompts or prepend them to the first human turn later
            continue 
        elif role == "user":
            formatted_convo.append({"from": "human", "value": str(content)})
        elif role == "assistant":
            # Standardize tool calls into text-based Action blocks for the 2B model
            tool_calls = turn.get("tool_calls", [])
            if tool_calls:
                action_str = content + "\n\n" if content else ""
                for tc in tool_calls:
                    func = tc.get("function", {})
                    name = func.get("name", "tool")
                    args = func.get("arguments", "{}")
                    # Format as Action: <tool> \n Arguments: <args>
                    action_str += f"Action: `{name}`\nArguments: {args}\n"
                formatted_convo.append({"from": "gpt", "value": action_str.strip()})
            else:
                formatted_convo.append({"from": "gpt", "value": str(content)})
        elif role in ["tool", "observation", "environment"]:
            formatted_convo.append({"from": "observation", "value": str(content)})
            
    # Ensure there's actually a conversation
    if len(formatted_convo) > 1:
        swe_data.append({
            "id": f"swe_debug_{row.get('instance_id', i)}",
            "conversations": formatted_convo
        })

# Set seed for reproducibility
random.seed(42)

# Shuffle before sampling
random.shuffle(codefeedback_data)
random.shuffle(swe_data)

# Sample exact target numbers (60% / 40% split of 4K)
target_cf = codefeedback_data[:2400]
target_swe = swe_data[:1600]

final_debugging_dataset = target_cf + target_swe
random.shuffle(final_debugging_dataset)

output_file = "dataset/02_debugging.jsonl"
print(f"Saving {len(final_debugging_dataset)} examples to {output_file}...")

with jsonlines.open(output_file, mode="w") as writer:
    writer.write_all(final_debugging_dataset)

print("✅ Done! 02_debugging.jsonl is ready. We have blended Q&A debugging with autonomous multi-turn debugging.")
