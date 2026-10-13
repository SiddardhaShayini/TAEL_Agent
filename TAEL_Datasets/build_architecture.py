from datasets import load_dataset
import jsonlines
import random
import os

# Ensure target directory exists
os.makedirs("dataset", exist_ok=True)

print("Loading CodeFeedback dataset from Hugging Face...")

# Load CodeFeedback (Apache 2.0)
codefeedback_ds = load_dataset("m-a-p/CodeFeedback-Filtered-Instruction", split="train")

architecture_data = []

# Keywords that strongly indicate system design or architectural planning
arch_keywords = [
    "system design", "architecture", "microservice", "microservices", 
    "database schema", "schema design", "uml", "design pattern", 
    "scalability", "load balancing", "api design"
]

print("Scanning for architecture and system design tasks (Target: 1,000)...")

for i, row in enumerate(codefeedback_ds):
    query = row.get("query", "")
    answer = row.get("answer", "")
    
    if not query or not answer:
        continue
        
    query_lower = query.lower()
    
    # Check if the query is asking for high-level design
    if any(keyword in query_lower for keyword in arch_keywords):
        architecture_data.append({
            "id": f"cf_arch_{i}",
            "conversations": [
                {"from": "human", "value": query},
                {"from": "gpt", "value": answer}
            ]
        })

print(f"Found {len(architecture_data)} architecture examples.")

# Set seed for reproducibility
random.seed(42)

# Shuffle the data
random.shuffle(architecture_data)

# Sample exactly 1,000 examples
target_size = 1000
if len(architecture_data) >= target_size:
    final_architecture_dataset = architecture_data[:target_size]
else:
    print(f"Warning: Only found {len(architecture_data)} examples, using all of them.")
    final_architecture_dataset = architecture_data

output_file = "dataset/06_architecture.jsonl"
print(f"Saving {len(final_architecture_dataset)} examples to {output_file}...")

with jsonlines.open(output_file, mode="w") as writer:
    writer.write_all(final_architecture_dataset)

print("✅ Done! 06_architecture.jsonl is ready. Your model will now understand system design and high-level structure.")
