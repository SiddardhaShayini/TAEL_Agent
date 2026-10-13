from datasets import load_dataset
import jsonlines
import random
import os

# Create the target directory
os.makedirs("dataset", exist_ok=True)

print("Loading datasets from Hugging Face... (this might take a few minutes)")

# 1. Load BigCode Self-OSS-Instruct (Strictly Open/Apache 2.0)
bigcode_ds = load_dataset("bigcode/self-oss-instruct-sc2-exec-filter-50k", split="train")

# 2. Load CodeFeedback Filtered Instruction (Apache 2.0)
codefeedback_ds = load_dataset("m-a-p/CodeFeedback-Filtered-Instruction", split="train")

bigcode_data = []
codefeedback_data = []

print("Processing BigCode dataset...")
# Process BigCode 
for i, row in enumerate(bigcode_ds):
    # BigCode uses 'instruction' and 'response' columns
    instruction = row.get("instruction", "")
    response = row.get("response", "")
    
    if not instruction or not response:
        continue
        
    bigcode_data.append({
        "id": f"bc_prog_{i}",
        "conversations": [
            {"from": "human", "value": instruction},
            {"from": "gpt", "value": response}
        ]
    })

print("Processing CodeFeedback dataset...")
# Process CodeFeedback
# We filter OUT keywords meant for debugging/refactoring to prevent data leakage
exclude_terms = ["refactor", "clean up", "optimize", "rename", "split", "extract", "dry", "modernize", "fix", "bug", "traceback", "error"]

for i, row in enumerate(codefeedback_ds):
    # CodeFeedback uses 'query' and 'answer' columns
    query = row.get("query", "")
    answer = row.get("answer", "")
    
    if not query or not answer:
        continue
        
    query_lower = query.lower()
    
    # Exclude queries that belong in our upcoming debugging or refactoring splits
    if any(term in query_lower for term in exclude_terms):
        continue
        
    codefeedback_data.append({
        "id": f"cf_prog_{i}",
        "conversations": [
            {"from": "human", "value": query},
            {"from": "gpt", "value": answer}
        ]
    })

# Set seed for reproducibility
random.seed(42) 

# Shuffle before sampling
random.shuffle(bigcode_data)
random.shuffle(codefeedback_data)

# Sample exact target numbers (70% / 30% split)
target_bigcode = bigcode_data[:10500]
target_codefeedback = codefeedback_data[:4500]

# Combine and shuffle the final dataset
final_programming_dataset = target_bigcode + target_codefeedback
random.shuffle(final_programming_dataset)

# Save to JSONL
output_file = "dataset/01_programming.jsonl"
print(f"Saving {len(final_programming_dataset)} examples to {output_file}...")

with jsonlines.open(output_file, mode="w") as writer:
    writer.write_all(final_programming_dataset)

print("✅ Done! 01_programming.jsonl is ready and perfectly balanced.")
