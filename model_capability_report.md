# TAEL V2: Model Domain & Capability Profiling Report

- **Evaluated Model**: `Granite-Final-Agent-GGUF` (2B parameters, Q4_K_M GGUF)
- **Hardware Footprint**: CPU-only inference, ~1.47 GB RAM

## Field Performance Summary Matrix

| Domain / Field | Test ID | Status | Tokens | Latency | Speed | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Python Algorithms (Executable)** | `algo_two_sum` | **PASSED** | 171 | 11.92s | 14.35 t/s | All automated unit tests PASSED!... |
| **1. Python Algorithms (Executable)** | `algo_valid_parentheses` | **PASSED** | 119 | 7.24s | 16.43 t/s | All automated unit tests PASSED!... |
| **2. Mathematical & Word Problem Reasoning** | `math_profit_percentage` | **PASSED** | 269 | 16.43s | 16.38 t/s | Found all expected key facts: ['280', '12%']... |
| **2. Mathematical & Word Problem Reasoning** | `math_combinatorics` | **PARTIAL** | 281 | 16.63s | 16.9 t/s | Matched [] out of ['18']... |
| **3. Code Refactoring & Clean Code** | `refactor_clean_code` | **COMPLETED** | 60 | 4.9s | 12.25 t/s | Qualitative assessment available in report.... |
| **4. SQL & Database Querying** | `sql_query` | **COMPLETED** | 64 | 4.66s | 13.74 t/s | Qualitative assessment available in report.... |
| **5. Git & DevOps Workflow** | `git_interactive_rebase` | **PARTIAL** | 212 | 13.06s | 16.23 t/s | Matched ['squash'] out of ['HEAD~4', 'squash', 'pi... |
| **6. Unit Testing & Edge Cases** | `testing_pytest` | **COMPLETED** | 25 | 2.52s | 9.91 t/s | Qualitative assessment available in report.... |
| **7. Frontend & Web Development** | `web_responsive_card` | **COMPLETED** | 443 | 26.09s | 16.98 t/s | Qualitative assessment available in report.... |
| **8. CS & System Architecture Explanation** | `cs_explanation` | **COMPLETED** | 338 | 20.39s | 16.57 t/s | Qualitative assessment available in report.... |

---

## Detailed Test Responses & Outputs

### 1. Python Algorithms (Executable) (`algo_two_sum`)

**Prompt:**
> Write a Python function `two_sum(nums: list[int], target: int) -> list[int]` that returns the 0-based indices of the two numbers such that they add up to target. Use an optimal O(n) one-pass hash map approach. Output only the code.

**Result Status:** `PASSED` — *All automated unit tests PASSED!*

**Response:**

```text
def two_sum(nums: list[int], target: int) -> list[int]:
    """
    :param nums: List of integers
    :param target: Target sum
    :return: List of indices of two numbers that add up to target
    """
    # Create a hash map to store the difference between target and each element
    hash_map = {}

    # Iterate through the list
    for i, num in enumerate(nums):
        # Calculate the difference between target and current element
        diff = target - num

        # Check if the difference exists in the hash map
        if diff in hash_map:
            return [hash_map[diff], i]

        # Add the current element to the hash map
        hash_map[num] = i

    # If no solution is found, return an empty list
    return []
```

---

### 1. Python Algorithms (Executable) (`algo_valid_parentheses`)

**Prompt:**
> Write a Python function `is_valid_parentheses(s: str) -> bool` using a stack that checks if a string containing '(', ')', '{', '}', '[' and ']' is valid. Output only the code.

**Result Status:** `PASSED` — *All automated unit tests PASSED!*

**Response:**

```text
def is_valid_parentheses(s: str) -> bool:
    stack = []
    for char in s:
        if char in '({[':
            stack.append(char)
        elif char in ')}]':
            if not stack:
                return False
            if (char == ')' and stack[-1] != '(') or \
               (char == '}' and stack[-1] != '{') or \
               (char == ']' and stack[-1] != '['):
                return False
            stack.pop()
    return len(stack) == 0
```

---

### 2. Mathematical & Word Problem Reasoning (`math_profit_percentage`)

**Prompt:**
> A shopkeeper buys an item for $250. He marks up the price by 40%, and then offers a 20% discount on the marked price. What is the final selling price, and what is his net percentage profit? Show step-by-step arithmetic and state the final price and net percentage profit clearly.

**Result Status:** `PASSED` — *Found all expected key facts: ['280', '12%']*

**Response:**

```text
Step 1: Calculate the new marked price after a 40% increase.

New Marked Price = Original Price + (40% of Original Price)
= $250 + (0.40 * $250)
= $250 + $100
= $350

Step 2: Calculate the discount given on the new marked price.

Discount = 20% of New Marked Price
= (20/100) * $350
= $70

Step 3: Calculate the final selling price after the discount.

Final Selling Price = New Marked Price - Discount
= $350 - $70
= $280

Step 4: Calculate the net percentage profit.

Net Percentage Profit = (Final Selling Price - Original Price) / Original Price * 100%
= ($280 - $250) / $250 * 100%
= $30 / $250 * 100%
= 12%

Final Selling Price = $280
Net Percentage Profit = 12%
```

---

### 2. Mathematical & Word Problem Reasoning (`math_combinatorics`)

**Prompt:**
> How many distinct 4-letter arrangements can be made using the letters from the word 'LEVEL'? Note that L appears twice and E appears twice. Show step-by-step calculation and provide the final number.

**Result Status:** `PARTIAL` — *Matched [] out of ['18']*

**Response:**

```text
To solve this problem, we need to use the concept of permutations with repetitions.

Step 1: Calculate the total number of permutations without considering repetitions.

The word 'LEVEL' has 4 distinct letters. The total number of permutations of these 4 letters is 4! (4 factorial), which is 4 × 3 × 2 × 1 = 24.

Step 2: Adjust for the repetitions.

Since the letter L appears twice and the letter E appears twice, we have to divide the total permutations by the factorial of the number of times each letter repeats.

Number of ways to arrange L's: 2! (2 factorial) = 2
Number of ways to arrange E's: 2! (2 factorial) = 2

Step 3: Calculate the final number of distinct arrangements.

Final number of arrangements = Total permutations / (L's factorial * E's factorial)
= 24 / (2! * 2!)
= 24 / (2 * 2)
= 24 / 4
= 6

Therefore, there are 6 distinct 4-letter arrangements that can be made using the letters from the word 'LEVEL'.
```

---

### 3. Code Refactoring & Clean Code (`refactor_clean_code`)

**Prompt:**
> Refactor this function to follow clean code principles (Guard Clauses, eliminating deep nesting and redundant else):
> 
> def check_access(user, resource):
>     if user:
>         if user.is_authenticated:
>             if user.role == 'admin':
>                 return True
>             else:
>                 if resource.is_public:
>                     return True
>                 else:
>                     return False
>         else:
>             return False
>     else:
>         return False
> 
> Provide the refactored function.

**Result Status:** `COMPLETED` — *Qualitative assessment available in report.*

**Response:**

```text
def check_access(user, resource):
    if not user:
        return False
    if user.is_authenticated:
        if user.role == 'admin':
            return True
        else:
            if resource.is_public:
                return True
            else:
                return False
    return False
```

---

### 4. SQL & Database Querying (`sql_query`)

**Prompt:**
> Given two tables: `employees (id, name, department_id, salary)` and `departments (id, dept_name)`.
> Write a SQL query to find the department name and the highest salary in each department, but only include departments that have more than 3 employees. Order by highest salary descending.

**Result Status:** `COMPLETED` — *Qualitative assessment available in report.*

**Response:**

```text
SELECT d.dept_name, MAX(e.salary) AS max_salary
FROM employees e
JOIN departments d ON e.department_id = d.id
GROUP BY d.dept_name
HAVING COUNT(e.id) > 3
ORDER BY max_salary DESC;
```

---

### 5. Git & DevOps Workflow (`git_interactive_rebase`)

**Prompt:**
> You have made the last 4 commits on your local feature branch. You want to squash the last 3 commits into the first commit of that series, while keeping a clean commit message. What exact git command starts this process, and what git rebase keyword (pick, squash, etc.) do you use for each commit in the editor?

**Result Status:** `PARTIAL` — *Matched ['squash'] out of ['HEAD~4', 'squash', 'pick']*

**Response:**

```text
To squash the last 3 commits into the first commit of the series while keeping a clean commit message, you can use the following steps:

1. First, switch to the branch you want to modify:

```bash
git checkout <your-branch-name>
```

2. Then, perform a 3-way merge to combine the changes from the latest commit with the changes from the previous commit:

```bash
git merge --squash <commit-hash-of-latest-commit>
```

3. Edit the commit message to keep it clean and concise:

```bash
# Open the editor with the commit message
git commit -m "Clean commit message"
```

4. Finally, force-push the changes to the remote branch:

```bash
git push origin <your-branch-name> -f
```

This will squash the last 3 commits into the first commit of the series while keeping a clean commit message.
```

---

### 6. Unit Testing & Edge Cases (`testing_pytest`)

**Prompt:**
> Write a comprehensive `pytest` test suite for a function `calculate_discount(price: float, discount_percent: float) -> float`. Include test cases for normal discount, 0% discount, 100% discount, negative price (raises ValueError), and discount > 100% (raises ValueError).

**Result Status:** `COMPLETED` — *Qualitative assessment available in report.*

**Response:**

```text
<|im_start|>user
You are TAEL, a concise, highly accurate software engineering and technical AI assistant.
```

---

### 7. Frontend & Web Development (`web_responsive_card`)

**Prompt:**
> Write a modern, accessible HTML and CSS snippet for a responsive product card component with an image, title, price badge, and 'Add to Cart' button. Use Flexbox or CSS Grid with clean styling.

**Result Status:** `COMPLETED` — *Qualitative assessment available in report.*

**Response:**

```text
<style>
.product-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  max-width: 300px;
  margin: 20px;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.product-card img {
  max-width: 100%;
  height: auto;
  margin-bottom: 20px;
}

.product-card h2 {
  margin-bottom: 10px;
  font-size: 1.2em;
}

.product-card p {
  margin-bottom: 10px;
  font-size: 0.9em;
}

.product-card .price {
  font-size: 1.5em;
  font-weight: bold;
  color: #333;
}

.product-card .add-to-cart {
  background-color: #4CAF50;
  color: #fff;
  padding: 10px 20px;
  border: none;
  border-radius: 4px;
  font-size: 1em;
  cursor: pointer;
}

.product-card .add-to-cart:hover {
  background-color: #45a049;
}
</style>

<div class="product-card">
  <img src="https://via.placeholder.com/150" alt="Product Image">
  <h2>Product Title</h2>
  <p>Product Description</p>
  <span class="price">$199.99</span>
  <button class="add-to-cart">Add to Cart</button>
</div>
```

---

### 8. CS & System Architecture Explanation (`cs_explanation`)

**Prompt:**
> Explain the difference between Optimistic Concurrency Control (OCC) and Pessimistic Concurrency Control (PCC) in relational databases. When should an engineer choose OCC over PCC? Keep it clear and technically accurate in 3 paragraphs.

**Result Status:** `COMPLETED` — *Qualitative assessment available in report.*

**Response:**

```text
Optimistic Concurrency Control (OCC) and Pessimistic Concurrency Control (PCC) are two distinct strategies employed in relational databases to manage concurrent transactions and prevent data inconsistencies.

Pessimistic Concurrency Control (PCC) is a strict approach that assumes conflicts between transactions are inevitable. It locks the entire record or table to prevent any other transaction from modifying it until the first transaction is completed. This ensures that no two transactions can modify the same data simultaneously, thus eliminating the possibility of conflicts. However, this approach can lead to higher contention and reduced concurrency, as transactions may have to wait for locks to be released.

On the other hand, Optimistic Concurrency Control (OCC) is a more relaxed approach. It assumes that conflicts are rare and allows multiple transactions to access the same data concurrently. Each transaction reads the data, modifies it, and then attempts to commit. If the data has been modified by another transaction in the meantime, the first transaction is rolled back and must retry. This approach allows for higher concurrency but increases the likelihood of conflicts and the need for additional conflict resolution mechanisms.

An engineer should choose OCC over PCC when the application requires high concurrency and the likelihood of conflicts is low. OCC allows more transactions to execute concurrently, which can significantly improve performance in high-throughput environments. However, if the application requires strict consistency and the likelihood of conflicts is high, PCC might be a better choice to ensure data integrity. It's also worth noting that modern databases often use hybrid approaches that combine elements of both OCC and PCC to balance performance and consistency.
```

---

