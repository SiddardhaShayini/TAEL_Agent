#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAEL Dynamic Task Router
------------------------
An intelligent task classifier and parameter router for TAEL.
Analyzes user intent and context to dynamically select:
  1. Category-specific System Prompt
  2. Optimal Tool Subset (from tael_tools)
  3. Generation Parameters (temperature, top_p, max_tokens, stop tokens)
  4. Confidence Scoring with automatic fallback to General Chat

Categories:
  - Programming
  - Debugging
  - Refactoring
  - SQL
  - Architecture
  - Git
  - Tool Use
  - Math
  - General Chat (Fallback default)
"""

import re
import math
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field


# ==============================================================================
# 1. Category Definitions
# ==============================================================================

class TaskCategory(str, Enum):
    PROGRAMMING = "Programming"
    DEBUGGING = "Debugging"
    REFACTORING = "Refactoring"
    SQL = "SQL"
    ARCHITECTURE = "Architecture"
    GIT = "Git"
    TOOL_USE = "Tool Use"
    MATH = "Math"
    GENERAL_CHAT = "General Chat"


# ==============================================================================
# 2. Routing Decision Dataclass
# ==============================================================================

@dataclass
class RouteDecision:
    """Represents the complete routing outcome for a given input."""
    category: TaskCategory
    confidence: float
    all_scores: Dict[str, float]
    system_prompt: str
    tool_names: List[str]
    generation_params: Dict[str, Any]
    reasoning: str
    is_fallback: bool = False

    def format_summary(self) -> str:
        """Returns a formatted human-readable summary of the routing decision."""
        tools_str = ", ".join(self.tool_names) if self.tool_names else "None (Pure Generation)"
        temp = self.generation_params.get("temperature", "N/A")
        top_p = self.generation_params.get("top_p", "N/A")
        max_tok = self.generation_params.get("max_tokens", "N/A")
        fallback_str = " [FALLBACK]" if self.is_fallback else ""

        return (
            f"=== TAEL ROUTER DECISION{fallback_str} ===\n"
            f"  Category:          {self.category.value}\n"
            f"  Confidence:        {self.confidence:.1%}\n"
            f"  Reasoning:         {self.reasoning}\n"
            f"  Tools Selected:    {tools_str}\n"
            f"  Generation Params: temp={temp}, top_p={top_p}, max_tokens={max_tok}\n"
            f"================================="
        )

    def to_dict(self) -> Dict[str, Any]:
        """Converts the decision into a serializable dictionary."""
        return {
            "category": self.category.value,
            "confidence": round(self.confidence, 4),
            "all_scores": {k: round(v, 4) for k, v in self.all_scores.items()},
            "tool_names": self.tool_names,
            "generation_params": self.generation_params,
            "reasoning": self.reasoning,
            "is_fallback": self.is_fallback,
            "system_prompt": self.system_prompt,
        }


# ==============================================================================
# 3. Category Profiles: Prompts, Tools & Presets
# ==============================================================================

@dataclass
class CategoryProfile:
    category: TaskCategory
    description: str
    system_prompt: str
    tool_names: List[str]
    generation_params: Dict[str, Any]
    primary_keywords: List[str] = field(default_factory=list)
    secondary_keywords: List[str] = field(default_factory=list)
    regex_patterns: List[re.Pattern] = field(default_factory=list)
    negative_keywords: List[str] = field(default_factory=list)


# ------------------------------------------------------------------------------
# System Prompts Tailored for 2B Granite Architecture
# ------------------------------------------------------------------------------

SYSTEM_PROMPT_BASE = (
    "You are TAEL, a specialized autonomous software engineering and coding AI assistant. "
    "You run locally with high efficiency. Be direct, precise, and rigorous."
)

PROMPT_PROGRAMMING = (
    f"{SYSTEM_PROMPT_BASE}\n"
    "ROLE: Senior Software Engineer & Algorithm Specialist.\n"
    "GOALS:\n"
    "1. Write clean, robust, and idiomatic production code with full type annotations.\n"
    "2. Handle edge cases (empty inputs, boundaries, invalid types) defensively.\n"
    "3. Prioritize algorithmic efficiency (optimal time/space Big-O complexity).\n"
    "4. When creating or testing code files in the workspace, emit structured <tool_call> blocks."
)

PROMPT_DEBUGGING = (
    f"{SYSTEM_PROMPT_BASE}\n"
    "ROLE: Systems Debugger & Error Diagnostic Expert.\n"
    "GOALS:\n"
    "1. Perform surgical root-cause analysis on stack traces, exceptions, and failing tests.\n"
    "2. Reproduce and inspect the issue using tools (`read_file`, `search_text`, `execute_python`).\n"
    "3. Explain precisely WHY the failure occurred before providing the minimal fix.\n"
    "4. Verify the fix by running tests or executing code in the workspace."
)

PROMPT_REFACTORING = (
    f"{SYSTEM_PROMPT_BASE}\n"
    "ROLE: Code Quality & Architecture Refactoring Specialist.\n"
    "GOALS:\n"
    "1. Eliminate code smells, deep nested if/else statements, and duplicate logic.\n"
    "2. Apply Guard Clauses, early returns, and Single Responsibility Principle.\n"
    "3. Preserve 100% functional equivalence without altering external interfaces.\n"
    "4. Ensure idiomatic naming and enhanced readability."
)

PROMPT_SQL = (
    f"{SYSTEM_PROMPT_BASE}\n"
    "ROLE: Database Architect & Query Optimization Specialist.\n"
    "GOALS:\n"
    "1. Write clean, standard ANSI SQL queries, CTEs, and schema migrations.\n"
    "2. Optimize for performance: index usage, selective filtering, avoiding SELECT *.\n"
    "3. Handle NULL semantics, JOIN types, and window functions accurately.\n"
    "4. Provide schema context and query execution trade-offs."
)

PROMPT_ARCHITECTURE = (
    f"{SYSTEM_PROMPT_BASE}\n"
    "ROLE: Principal Systems Architect.\n"
    "GOALS:\n"
    "1. Design scalable, modular, and maintainable software systems and microservices.\n"
    "2. Clearly analyze architectural trade-offs (CAP theorem, latency vs throughput, memory constraints).\n"
    "3. Define concrete component interfaces, data flows, and storage strategies.\n"
    "4. Tailor solutions to practical infrastructure realities (e.g. 8GB RAM local constraints)."
)

PROMPT_GIT = (
    f"{SYSTEM_PROMPT_BASE}\n"
    "ROLE: Git & Version Control Operations Specialist.\n"
    "GOALS:\n"
    "1. Provide safe, verified git workflows (rebase, conflict resolution, cherry-pick, branch strategy).\n"
    "2. Always inspect repository status (`git_status`, `git_diff`) before suggesting mutations.\n"
    "3. Avoid destructive operations (force-pushing to main, hard resets without stash).\n"
    "4. Provide concise step-by-step terminal instructions."
)

PROMPT_TOOL_USE = (
    f"{SYSTEM_PROMPT_BASE}\n"
    "ROLE: Autonomous Agentic SWE Executor.\n"
    "GOALS:\n"
    "1. Execute tasks autonomously in the local workspace using tool calls.\n"
    "2. Emit valid XML <tool_call> JSON blocks sequentially to read, write, and verify files.\n"
    "3. Always inspect execution results from <tool_response> before proceeding.\n"
    "4. When the task is complete and verified, call the `finish` tool."
)

PROMPT_MATH = (
    f"{SYSTEM_PROMPT_BASE}\n"
    "ROLE: Mathematical Reasoning & Numerical Computation Specialist.\n"
    "GOALS:\n"
    "1. Solve mathematical, statistical, and algorithmic complexity problems rigorously.\n"
    "2. Show explicit step-by-step reasoning with clear variable definitions.\n"
    "3. For complex arithmetic, execute Python scripts via `execute_python` to ensure 100% precision.\n"
    "4. State final answers clearly in bold or boxed notation."
)

PROMPT_GENERAL_CHAT = (
    f"{SYSTEM_PROMPT_BASE}\n"
    "ROLE: Helpful & Adaptive AI Assistant.\n"
    "GOALS:\n"
    "1. Provide friendly, clear, concise, and helpful answers to general inquiries.\n"
    "2. Answer questions about software engineering, concepts, and everyday workflows.\n"
    "3. If a coding or agentic task is requested, offer to execute it with tools."
)


# ==============================================================================
# 4. Profile Registry Map
# ==============================================================================

CATEGORY_PROFILES: Dict[TaskCategory, CategoryProfile] = {
    TaskCategory.PROGRAMMING: CategoryProfile(
        category=TaskCategory.PROGRAMMING,
        description="Writing algorithms, code implementation, classes, functions, and unit tests.",
        system_prompt=PROMPT_PROGRAMMING,
        tool_names=["read_file", "write_file", "list_dir", "execute_python", "execute_terminal_command", "finish"],
        generation_params={
            "temperature": 0.15,
            "top_p": 0.90,
            "max_tokens": 2048,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.1,
        },
        primary_keywords=[
            "implement", "algorithm", "function", "class", "leetcode", "two sum",
            "quickselect", "sort", "binary search", "data structure", "tree", "graph",
            "linked list", "decorator", "generator", "asyncio", "script", "program",
        ],
        secondary_keywords=[
            "write code", "python code", "javascript", "typescript", "c++", "golang",
            "rust", "java", "oop", "recursion", "dynamic programming", "memoization",
            "time complexity", "unit test", "pytest",
        ],
        regex_patterns=[
            re.compile(r"\b(write\s+(a\s+)?(python|javascript|typescript|c\+\+|java|go|rust|code|function|class|script))\b", re.I),
            re.compile(r"\b(implement\s+(a\s+)?(function|class|algorithm|solution|method))\b", re.I),
            re.compile(r"\b(solve\s+this\s+in\s+(python|c\+\+|java|go))\b", re.I),
            re.compile(r"```(python|javascript|typescript|cpp|java|go|rust)\b", re.I),
        ],
        negative_keywords=["bug", "traceback", "fix error", "git rebase", "select * from"],
    ),

    TaskCategory.DEBUGGING: CategoryProfile(
        category=TaskCategory.DEBUGGING,
        description="Diagnosing errors, analyzing stack traces, fixing exceptions, and resolving bugs.",
        system_prompt=PROMPT_DEBUGGING,
        tool_names=["read_file", "search_text", "execute_python", "execute_terminal_command", "write_file", "finish"],
        generation_params={
            "temperature": 0.20,
            "top_p": 0.90,
            "max_tokens": 2048,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
        },
        primary_keywords=[
            "bug", "error", "traceback", "exception", "typeerror", "valueerror",
            "indexerror", "keyerror", "attributeerror", "stacktrace", "fix this bug",
            "debug", "segfault", "broken", "failing", "crash", "401 unauthorized", "500 error",
        ],
        secondary_keywords=[
            "why is this failing", "issue", "reproduce", "assertion error",
            "null pointer", "undefined", "unhandled exception", "syntaxerror",
        ],
        regex_patterns=[
            re.compile(r"\btraceback\s+\(most\s+recent\s+call\s+last\)", re.I),
            re.compile(r"\b(fix\s+(this\s+)?(bug|error|issue|exception|crash|failure))\b", re.I),
            re.compile(r"\b(why\s+(is\s+this|does\s+it)\s+(failing|crashing|broken|throwing))\b", re.I),
            re.compile(r"\b(line\s+\d+,\s+in\s+[a-zA-Z0-9_]+)\b", re.I),
            re.compile(r"\b(TypeError|ValueError|KeyError|IndexError|AttributeError|ZeroDivisionError):", re.I),
        ],
        negative_keywords=["system design", "microservice", "create website"],
    ),

    TaskCategory.REFACTORING: CategoryProfile(
        category=TaskCategory.REFACTORING,
        description="Improving code quality, reducing nesting, applying guard clauses, and cleaning architecture.",
        system_prompt=PROMPT_REFACTORING,
        tool_names=["read_file", "write_file", "search_text", "execute_python", "git_diff", "finish"],
        generation_params={
            "temperature": 0.20,
            "top_p": 0.90,
            "max_tokens": 2048,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.05,
        },
        primary_keywords=[
            "refactor", "guard clause", "clean code", "code smell", "nesting",
            "reduce nesting", "cyclomatic complexity", "simplify", "extract function",
            "dry principle", "single responsibility", "decouple",
        ],
        secondary_keywords=[
            "make cleaner", "improve readability", "nested if", "spaghetti code",
            "optimize code", "modularize", "idiomatic", "cleanup",
        ],
        regex_patterns=[
            re.compile(r"\b(refactor\s+(this|the|my)?\s*(code|function|class|method|module)?)\b", re.I),
            re.compile(r"\b(reduce\s+nesting|guard\s+clauses?|eliminate\s+nested\s+if)\b", re.I),
            re.compile(r"\b(clean\s+up\s+(this|the)\s+code|improve\s+code\s+quality)\b", re.I),
            re.compile(r"\b(code\s+smell|cyclomatic\s+complexity)\b", re.I),
        ],
        negative_keywords=["git log", "select from where", "what is your name"],
    ),

    TaskCategory.SQL: CategoryProfile(
        category=TaskCategory.SQL,
        description="Writing, optimizing, and explaining relational SQL queries, schemas, and CTEs.",
        system_prompt=PROMPT_SQL,
        tool_names=["read_file", "write_file", "execute_python", "execute_terminal_command", "finish"],
        generation_params={
            "temperature": 0.10,
            "top_p": 0.85,
            "max_tokens": 1024,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
        },
        primary_keywords=[
            "sql", "select", "from", "where", "group by", "order by", "having",
            "join", "inner join", "left join", "cte", "postgres", "mysql", "sqlite",
            "foreign key", "primary key", "database", "query", "window function",
        ],
        secondary_keywords=[
            "table", "schema", "indexing", "aggregate", "partition by", "count",
            "sum", "subquery", "insert into", "update set", "alter table",
        ],
        regex_patterns=[
            re.compile(r"\b(select\s+.+\s+from\s+[a-zA-Z0-9_]+)\b", re.I),
            re.compile(r"\b(write\s+(a\s+)?(sql\s+)?query)\b", re.I),
            re.compile(r"\b(create\s+table|alter\s+table|foreign\s+key)\b", re.I),
            re.compile(r"\b(left|right|inner|outer|cross)\s+join\b", re.I),
            re.compile(r"```sql\b", re.I),
        ],
        negative_keywords=["git commit", "def ", "class ", "system design"],
    ),

    TaskCategory.ARCHITECTURE: CategoryProfile(
        category=TaskCategory.ARCHITECTURE,
        description="High-level system design, distributed architectures, microservices, and trade-off analysis.",
        system_prompt=PROMPT_ARCHITECTURE,
        tool_names=["list_dir", "read_file", "search_text", "finish"],
        generation_params={
            "temperature": 0.35,
            "top_p": 0.92,
            "max_tokens": 2048,
            "presence_penalty": 0.1,
            "frequency_penalty": 0.1,
        },
        primary_keywords=[
            "architecture", "system design", "microservice", "monolith", "scalability",
            "high-level design", "c4 model", "event-driven", "message queue", "kafka",
            "rabbitmq", "load balancer", "cap theorem", "concurrency model", "trade-off",
            "payment processing", "microservices architecture",
        ],
        secondary_keywords=[
            "distributed system", "api design", "rest vs grpc", "caching strategy",
            "redis", "database sharding", "horizontal scaling", "resilience",
        ],
        regex_patterns=[
            re.compile(r"\b(system\s+design|architectural\s+pattern|system\s+architecture)\b", re.I),
            re.compile(r"\b(how\s+should\s+we\s+architect|design\s+a\s+system)\b", re.I),
            re.compile(r"\b(microservices?\s+vs\s+monolith|event[- ]driven\s+architecture)\b", re.I),
            re.compile(r"\b(design\s+(a\s+)?(system|architecture|microservices?|service|platform|pipeline))\b", re.I),
            re.compile(r"\b(microservices?\s+architecture)\b", re.I),
            re.compile(r"\b(trade[- ]offs?\s+between|concurrency\s+control\s+(pcc|occ))\b", re.I),
        ],
        negative_keywords=["fix syntax error", "git push", "calculate 2+2"],
    ),

    TaskCategory.GIT: CategoryProfile(
        category=TaskCategory.GIT,
        description="Version control, branching strategies, rebase, merge conflicts, and commit history.",
        system_prompt=PROMPT_GIT,
        tool_names=["git_status", "git_diff", "git_log", "git_branch", "execute_terminal_command", "finish"],
        generation_params={
            "temperature": 0.10,
            "top_p": 0.85,
            "max_tokens": 1024,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
        },
        primary_keywords=[
            "git", "rebase", "merge conflict", "commit", "checkout", "branch",
            "stash", "cherry-pick", "git log", "git diff", "git status",
            "pull request", "fast-forward", "detached head",
        ],
        secondary_keywords=[
            "squash", "amend", "origin/main", "upstream", "working tree",
            "staging area", "index", "repo", "repository",
        ],
        regex_patterns=[
            re.compile(r"\b(git\s+(checkout|commit|push|pull|rebase|merge|status|diff|log|branch|stash|reset|revert))\b", re.I),
            re.compile(r"\b(merge\s+conflict|resolve\s+conflicts?|interactive\s+rebase)\b", re.I),
            re.compile(r"\b(how\s+to\s+(squash|rebase|undo\s+a\s+commit))\b", re.I),
        ],
        negative_keywords=["select *", "math equation", "what is your name"],
    ),

    TaskCategory.TOOL_USE: CategoryProfile(
        category=TaskCategory.TOOL_USE,
        description="Explicit agentic instructions to create files, execute shell commands, or run workflows in workspace.",
        system_prompt=PROMPT_TOOL_USE,
        tool_names=[
            "read_file", "write_file", "list_dir", "search_text",
            "git_status", "git_diff", "git_log", "git_branch",
            "execute_python", "execute_terminal_command", "finish"
        ],
        generation_params={
            "temperature": 0.15,
            "top_p": 0.90,
            "max_tokens": 2048,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
        },
        primary_keywords=[
            "create file", "write file", "make folder", "create website", "run command",
            "in the workspace", "in folder", "create a script", "execute terminal",
            "check logs", "create directory", "in temp_tael", "build project",
        ],
        secondary_keywords=[
            "tool_call", "execute and verify", "save to file", "run python",
            "list files", "mkdir", "touch", "terminal execution",
        ],
        regex_patterns=[
            re.compile(r"\b(create|write|generate)\s+(a\s+)?(file|files|folder|directory|script|website|project)\b", re.I),
            re.compile(r"\b(in\s+[a-zA-Z0-9_\-\./\\]+\s+(folder|directory))\b", re.I),
            re.compile(r"\b(run|execute)\s+(the\s+)?(command|terminal|script|bash|powershell)\b", re.I),
            re.compile(r"\b(check\s+logs|verify\s+(the\s+)?(files?|output))\b", re.I),
        ],
        negative_keywords=["what is the definition", "explain conceptually"],
    ),

    TaskCategory.MATH: CategoryProfile(
        category=TaskCategory.MATH,
        description="Mathematical reasoning, arithmetic, algebra, calculus, discrete math, and complexity analysis.",
        system_prompt=PROMPT_MATH,
        tool_names=["execute_python", "finish"],
        generation_params={
            "temperature": 0.00,
            "top_p": 0.80,
            "max_tokens": 1536,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
        },
        primary_keywords=[
            "calculate", "math", "arithmetic", "integral", "derivative", "equation",
            "probability", "percentage", "algebra", "discrete math", "matrix",
            "harmonic mean", "permutation", "combination", "factorial",
            "area", "volume", "radius", "geometry", "ratio", "mean", "median",
        ],
        secondary_keywords=[
            "solve for", "sum of", "product of", "divisible", "prime number",
            "theorem", "logarithm", "formula", "proof", "square root",
        ],
        regex_patterns=[
            re.compile(r"\b(\d+\s*[\+\-\*\/\^]\s*\d+)\b"),
            re.compile(r"\b(calculate\s+(the\s+)?(value|sum|product|percentage|integral|derivative|probability|area|volume|perimeter|radius|ratio|mean|average))\b", re.I),
            re.compile(r"\b(area\s+of|volume\s+of|circumference\s+of|radius\s+of)\b", re.I),
            re.compile(r"\b(solve\s+for\s+[a-zA-Z0-9_]+)\b", re.I),
            re.compile(r"\b(what\s+is\s+\d+(\.\d+)?\s*[\+\-\*\/]\s*\d+)\b", re.I),
            re.compile(r"\b(find\s+the\s+(roots?|eigenvalues?|determinant|limit))\b", re.I),
        ],
        negative_keywords=["git checkout", "create file", "select from where"],
    ),

    TaskCategory.GENERAL_CHAT: CategoryProfile(
        category=TaskCategory.GENERAL_CHAT,
        description="Conversational chit-chat, greetings, questions about TAEL, and non-technical dialogue.",
        system_prompt=PROMPT_GENERAL_CHAT,
        tool_names=["finish"],
        generation_params={
            "temperature": 0.70,
            "top_p": 0.95,
            "max_tokens": 1024,
            "presence_penalty": 0.2,
            "frequency_penalty": 0.2,
        },
        primary_keywords=[
            "hello", "hi", "hey", "who are you", "what is your name", "what can you do",
            "good morning", "good evening", "how are you", "thank you", "thanks", "bye",
        ],
        secondary_keywords=[
            "tell me about yourself", "chat", "joke", "weather", "help",
            "introduce yourself", "greetings", "nice to meet you",
        ],
        regex_patterns=[
            re.compile(r"^(hi|hello|hey|greetings|howdy)[!\?\.\s]*$", re.I),
            re.compile(r"\b(who\s+are\s+you|what\s+is\s+tael|what\s+can\s+you\s+do)\b", re.I),
            re.compile(r"\b(how\s+are\s+you\s*(today)?|tell\s+me\s+about\s+yourself)\b", re.I),
            re.compile(r"^(thanks?|thank\s+you|goodbye|bye)[!\?\.\s]*$", re.I),
        ],
        negative_keywords=["def ", "class ", "git ", "select ", "bug", "traceback"],
    ),
}


# ==============================================================================
# 5. Dynamic Task Router Engine
# ==============================================================================

class DynamicTaskRouter:
    """
    Intelligent Task Router with confidence scoring, specialized prompts,
    custom tool subsets, fine-tuned generation parameters, and robust fallback.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.35,
        fallback_category: TaskCategory = TaskCategory.GENERAL_CHAT,
    ):
        self.confidence_threshold = confidence_threshold
        self.fallback_category = fallback_category
        self.profiles = CATEGORY_PROFILES

    def route(self, prompt: str, context: Optional[List[Dict[str, str]]] = None) -> RouteDecision:
        """
        Evaluates the prompt, computes confidence scores, selects category,
        and constructs the complete RouteDecision.
        """
        cleaned_prompt = prompt.strip()
        if not cleaned_prompt:
            return self._build_fallback_decision(prompt, "Empty prompt provided.")

        # Compute raw scores across all categories
        raw_scores, matched_signals = self._compute_scores(cleaned_prompt)

        # Normalize scores to [0.0, 1.0] confidence scale
        confidence_scores = self._normalize_confidence(raw_scores)

        # Select top candidate
        sorted_candidates = sorted(
            confidence_scores.items(), key=lambda item: item[1], reverse=True
        )
        top_cat_str, top_conf = sorted_candidates[0]
        top_category = TaskCategory(top_cat_str)

        # Check for fallback conditions:
        # 1. Zero domain signals matched in prompt
        # 2. Top confidence is below threshold (and not an explicitly matched General Chat greeting)
        max_raw = max(raw_scores.values())
        has_chat_match = raw_scores[TaskCategory.GENERAL_CHAT] > 0.001

        if max_raw <= 0.001 or (top_conf < self.confidence_threshold and not has_chat_match):
            reason = (
                f"No strong domain signals matched or confidence {top_conf:.1%} "
                f"fell below threshold {self.confidence_threshold:.1%}."
            )
            return self._build_fallback_decision(
                prompt=cleaned_prompt,
                reason=reason,
                all_scores=confidence_scores
            )

        # Retrieve profile for winning category
        profile = self.profiles[top_category]
        signals_desc = ", ".join(matched_signals.get(top_category, ["lexical matching"]))

        reasoning = (
            f"Classified as '{top_category.value}' with {top_conf:.1%} confidence "
            f"based on: {signals_desc}."
        )

        return RouteDecision(
            category=top_category,
            confidence=top_conf,
            all_scores=confidence_scores,
            system_prompt=profile.system_prompt,
            tool_names=list(profile.tool_names),
            generation_params=dict(profile.generation_params),
            reasoning=reasoning,
            is_fallback=False,
        )

    # --------------------------------------------------------------------------
    # Scoring Algorithm
    # --------------------------------------------------------------------------

    def _compute_scores(self, text: str) -> Tuple[Dict[TaskCategory, float], Dict[TaskCategory, List[str]]]:
        """
        Multi-signal feature extractor computing weighted relevance per category.
        Weights:
          - Regex patterns: +4.0 to +5.0 (High precision intent/syntax)
          - Primary keywords: +2.5
          - Secondary keywords: +1.0
          - Negative keywords: -2.0
        """
        raw_scores: Dict[TaskCategory, float] = {cat: 0.0 for cat in self.profiles}
        matched_signals: Dict[TaskCategory, List[str]] = {cat: [] for cat in self.profiles}
        lower_text = text.lower()

        # Special priority: Explicit Tool Creation Intent ("create file in folder X")
        # boosts TOOL_USE above pure PROGRAMMING even if code is mentioned.
        is_tool_intent = bool(
            re.search(r"\b(create|in\s+[a-zA-Z0-9_\-\./\\]+\s+folder|run\s+command)\b", lower_text)
        )

        for cat, prof in self.profiles.items():
            score = 0.0

            # 1. Regex Pattern Matching (Highest Signal)
            for pat in prof.regex_patterns:
                matches = pat.findall(text)
                if matches:
                    weight = 5.0
                    score += weight * min(len(matches), 3)
                    matched_signals[cat].append(f"pattern '{pat.pattern[:24]}...'")

            # 2. Primary Keywords
            for kw in prof.primary_keywords:
                # Word-boundary matching
                pattern = r"\b" + re.escape(kw) + r"\b"
                if re.search(pattern, lower_text):
                    score += 3.0
                    matched_signals[cat].append(f"keyword '{kw}'")

            # 3. Secondary Keywords
            for kw in prof.secondary_keywords:
                pattern = r"\b" + re.escape(kw) + r"\b"
                if re.search(pattern, lower_text):
                    score += 1.5
                    matched_signals[cat].append(f"kw '{kw}'")

            # 4. Negative Keywords
            for nkw in prof.negative_keywords:
                pattern = r"\b" + re.escape(nkw) + r"\b"
                if re.search(pattern, lower_text):
                    score = max(0.0, score - 2.5)

            # 5. Contextual Adjustments
            if cat == TaskCategory.TOOL_USE and is_tool_intent:
                score *= 1.3
            elif cat == TaskCategory.PROGRAMMING and is_tool_intent:
                # If they say "in folder X, create index.html and js", tool use takes precedence
                if "folder" in lower_text or "create" in lower_text:
                    score *= 0.8

            raw_scores[cat] = score

        return raw_scores, matched_signals

    def _normalize_confidence(self, raw_scores: Dict[TaskCategory, float]) -> Dict[str, float]:
        """
        Converts raw scores to calibrated probabilities in [0.0, 1.0].
        Combines Softmax temperature scaling with raw-evidence capping.
        """
        max_score = max(raw_scores.values())

        # If zero signals detected across all categories, General Chat gets baseline
        if max_score <= 0.001:
            res = {cat.value: 0.05 for cat in raw_scores}
            res[TaskCategory.GENERAL_CHAT.value] = 0.60
            return res

        # Softmax with temperature tau=2.0 for balanced contrast
        tau = 2.0
        exp_scores = {cat: math.exp(score / tau) for cat, score in raw_scores.items()}
        total_exp = sum(exp_scores.values())

        # Softmax probabilities
        probabilities = {cat.value: exp_scores[cat] / total_exp for cat in raw_scores}

        # Evidence scaling: if top score is modest, cap maximum confidence
        top_cat = max(raw_scores, key=raw_scores.get)
        top_raw = raw_scores[top_cat]
        evidence_scale = min(1.0, 0.40 + (top_raw / 12.0) * 0.60)

        # Calibrate top candidate
        probabilities[top_cat.value] = min(0.99, probabilities[top_cat.value] * evidence_scale + (1.0 - evidence_scale) * 0.2)

        return probabilities

    # --------------------------------------------------------------------------
    # Fallback Generator
    # --------------------------------------------------------------------------

    def _build_fallback_decision(
        self,
        prompt: str,
        reason: str,
        all_scores: Optional[Dict[str, float]] = None,
    ) -> RouteDecision:
        """Constructs a clean RouteDecision falling back to General Chat."""
        profile = self.profiles[self.fallback_category]

        if all_scores is None:
            all_scores = {cat.value: 0.1 for cat in self.profiles}
            all_scores[self.fallback_category.value] = 0.70

        return RouteDecision(
            category=self.fallback_category,
            confidence=all_scores.get(self.fallback_category.value, 0.50),
            all_scores=all_scores,
            system_prompt=profile.system_prompt,
            tool_names=list(profile.tool_names),
            generation_params=dict(profile.generation_params),
            reasoning=f"Fallback to General Chat. Reason: {reason}",
            is_fallback=True,
        )


# ==============================================================================
# 6. Global Singleton & Convenience Functions
# ==============================================================================

_DEFAULT_ROUTER = DynamicTaskRouter()

def route_task(prompt: str, context: Optional[List[Dict[str, str]]] = None) -> RouteDecision:
    """Convenience function routing a user prompt through the default DynamicTaskRouter."""
    return _DEFAULT_ROUTER.route(prompt, context=context)

def get_category_profile(category: TaskCategory) -> CategoryProfile:
    """Retrieves the profile configuration for a specific task category."""
    return CATEGORY_PROFILES[category]
