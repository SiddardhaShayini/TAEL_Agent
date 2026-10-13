from datasets import load_dataset
import jsonlines
import random
import os

# Ensure target directory exists
os.makedirs("dataset", exist_ok=True)

print("Loading BigCode Self-OSS-Instruct dataset from Hugging Face...")

# Load BigCode (Apache 2.0)
bigcode_ds = load_dataset("bigcode/self-oss-instruct-sc2-exec-filter-50k", split="train")

testing_data = []

# Keywords that indicate testing, mocking, and assertions
test_keywords = [
    "unit test", "pytest", "mock", "test case", 
    "jest", "assert", "testing", "tdd", "test coverage"
]

print("Scanning for testing and mock environment tasks (Target: 2,000)...")

for i, row in enumerate(bigcode_ds):
    # BigCode uses 'instruction' and 'response' columns
    instruction = row.get("instruction", "")
    response = row.get("response", "")
    
    if not instruction or not response:
        continue
        
    instruction_lower = instruction.lower()
    
    # Check if the query is asking to write tests
    if any(keyword in instruction_lower for keyword in test_keywords):
        testing_data.append({
            "id": f"bc_test_{i}",
            "conversations": [
                {"from": "human", "value": instruction},
                {"from": "gpt", "value": response}
            ]
        })

print(f"Found {len(testing_data)} testing examples.")

# Set seed for reproducibility
random.seed(42)

# Shuffle the data
random.shuffle(testing_data)

# Sample exactly 2,000 examples
target_size = 2000
if len(testing_data) >= target_size:
    final_testing_dataset = testing_data[:target_size]
else:
    print(f"Warning: Only found {len(testing_data)} examples, using all of them.")
    final_testing_dataset = testing_data

output_file = "dataset/07_testing.jsonl"
print(f"Saving {len(final_testing_dataset)} examples to {output_file}...")

with jsonlines.open(output_file, mode="w") as writer:
    writer.write_all(final_testing_dataset)

print("✅ Done! 07_testing.jsonl is ready. Your model will now know how to write robust test coverage.")
