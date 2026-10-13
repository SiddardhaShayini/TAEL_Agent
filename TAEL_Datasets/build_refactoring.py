from datasets import load_dataset
import jsonlines
import random
import os

# Ensure target directory exists
os.makedirs("dataset", exist_ok=True)

print("Loading CodeFeedback dataset from Hugging Face...")

# Load CodeFeedback (Apache 2.0)
codefeedback_ds = load_dataset("m-a-p/CodeFeedback-Filtered-Instruction", split="train")

refactoring_data = []

# Keywords that indicate a structural/refactoring task
# (These are the exact keywords we excluded in step 1 to prevent data leakage)
refactor_keywords = [
    "refactor", "clean up", "optimize", "rename", 
    "split", "extract", "dry", "modernize"
]

print("Scanning for refactoring and optimization tasks...")

for i, row in enumerate(codefeedback_ds):
    query = row.get("query", "")
    answer = row.get("answer", "")
    
    if not query or not answer:
        continue
        
    query_lower = query.lower()
    
    # We only want queries asking the model to improve/refactor existing code
    if any(keyword in query_lower for keyword in refactor_keywords):
        refactoring_data.append({
            "id": f"cf_refactor_{i}",
            "conversations": [
                {"from": "human", "value": query},
                {"from": "gpt", "value": answer}
            ]
        })

print(f"Found {len(refactoring_data)} refactoring examples.")

# Set seed for reproducibility
random.seed(42)

# Shuffle the data
random.shuffle(refactoring_data)

# Sample exactly 2,000 examples
target_size = 2000
if len(refactoring_data) >= target_size:
    final_refactoring_dataset = refactoring_data[:target_size]
else:
    print(f"Warning: Only found {len(refactoring_data)} examples, using all of them.")
    final_refactoring_dataset = refactoring_data

output_file = "dataset/03_refactoring.jsonl"
print(f"Saving {len(final_refactoring_dataset)} examples to {output_file}...")

with jsonlines.open(output_file, mode="w") as writer:
    writer.write_all(final_refactoring_dataset)

print("✅ Done! 03_refactoring.jsonl is ready. Your model will now learn how to maintain and clean code.")
