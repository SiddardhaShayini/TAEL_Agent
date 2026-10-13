#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAEL Memory System: Relevance Retrieval Engine
---------------------------------------------
Scores and retrieves ONLY relevant context (files, project decisions, facts)
matching the user query, keeping context tight and preventing overflow.
"""

import re
import math
from typing import Dict, List, Any, Optional, Tuple

from .base import TokenCounter
from .file_tracker import FileMemory, TrackedFile
from .project import ProjectMemory, ArchitectureDecision


class MemoryRetriever:
    """
    Term-frequency and keyword relevance engine.
    Filters through FileMemory and ProjectMemory to pull in only context
    pertinent to the current prompt.
    """

    STOPWORDS = {
        "a", "an", "the", "in", "on", "at", "to", "for", "of", "with",
        "and", "or", "is", "it", "this", "that", "what", "how", "can",
        "you", "i", "we", "my", "me", "do", "be", "as", "by", "from",
    }

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """Normalizes and extracts significant keywords and paths."""
        words = re.findall(r"[a-zA-Z0-9_\-\./\\]+", text.lower())
        return [w for w in words if len(w) > 1 and w not in cls.STOPWORDS]

    @classmethod
    def score_text_similarity(cls, query_tokens: List[str], target_text: str) -> float:
        """Calculates keyword match score between query and target string."""
        if not query_tokens or not target_text:
            return 0.0

        target_tokens = cls.tokenize(target_text)
        if not target_tokens:
            return 0.0

        matches = 0
        target_set = set(target_tokens)
        for qt in query_tokens:
            if qt in target_set:
                matches += 1.5
            elif any(qt in t or t in qt for t in target_set if len(qt) > 3):
                matches += 0.8

        # Length normalization
        return matches / (math.sqrt(len(target_tokens)) + 1.0)

    @classmethod
    def retrieve_relevant_files(
        cls,
        query: str,
        file_memory: FileMemory,
        top_k: int = 3,
        threshold: float = 0.20,
    ) -> List[TrackedFile]:
        """Finds tracked files most relevant to the user prompt."""
        query_tokens = cls.tokenize(query)
        scored: List[Tuple[TrackedFile, float]] = []

        # Check for explicit file mentions in query
        explicit_files = re.findall(r'([a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9]{1,5})', query)

        for tf in file_memory.list_files():
            score = 0.0

            # 1. Exact path match in prompt
            if any(ef.lower() in tf.path.lower() or tf.path.lower() in ef.lower() for ef in explicit_files):
                score += 5.0

            # 2. Path tokens match
            path_tokens = cls.tokenize(tf.path)
            for pt in path_tokens:
                if pt in query_tokens:
                    score += 2.0

            # 3. Symbol match
            for sym in tf.symbols:
                if sym.lower() in query_tokens:
                    score += 3.0

            # 4. Content summary match
            score += cls.score_text_similarity(query_tokens, tf.summary)

            if score >= threshold:
                scored.append((tf, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in scored[:top_k]]

    @classmethod
    def retrieve_relevant_decisions(
        cls,
        query: str,
        project_memory: ProjectMemory,
        top_k: int = 2,
        threshold: float = 0.25,
    ) -> List[ArchitectureDecision]:
        """Finds project architectural decisions matching the query."""
        query_tokens = cls.tokenize(query)
        scored: List[Tuple[ArchitectureDecision, float]] = []

        for adr in project_memory.list_decisions():
            target_text = f"{adr.title} {' '.join(adr.tags)} {adr.description}"
            score = cls.score_text_similarity(query_tokens, target_text)
            if score >= threshold:
                scored.append((adr, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in scored[:top_k]]

    @classmethod
    def retrieve_relevant_facts(
        cls,
        query: str,
        project_memory: ProjectMemory,
        max_facts: int = 4,
    ) -> Dict[str, Any]:
        """Selects project facts matching query terms."""
        query_tokens = cls.tokenize(query)
        matched_facts = {}

        for k, v in project_memory.facts.items():
            fact_str = f"{k} {v}".lower()
            if any(qt in fact_str for qt in query_tokens):
                matched_facts[k] = v
                if len(matched_facts) >= max_facts:
                    break

        return matched_facts

    @classmethod
    def build_relevant_context(
        cls,
        query: str,
        file_memory: FileMemory,
        project_memory: ProjectMemory,
        max_tokens: int = 500,
    ) -> str:
        """
        Retrieves ONLY relevant memories and packages them into a concise prompt block.
        If nothing is relevant, returns minimal/empty string to conserve token budget.
        """
        relevant_files = cls.retrieve_relevant_files(query, file_memory)
        relevant_decisions = cls.retrieve_relevant_decisions(query, project_memory)
        relevant_facts = cls.retrieve_relevant_facts(query, project_memory)

        if not relevant_files and not relevant_decisions and not relevant_facts:
            return ""

        sections = ["[RELEVANT PERSISTENT CONTEXT]"]

        if relevant_facts:
            sections.append("Relevant Project Facts:")
            for k, v in relevant_facts.items():
                sections.append(f"  - {k}: {v}")

        if relevant_decisions:
            sections.append("Relevant Architectural Decisions:")
            for adr in relevant_decisions:
                sections.append(f"  - [{adr.id}] {adr.title}: {adr.description[:90]}")

        if relevant_files:
            sections.append("Relevant Tracked Files:")
            for tf in relevant_files:
                sym_str = f" | Symbols: {', '.join(tf.symbols[:4])}" if tf.symbols else ""
                sections.append(f"  - `{tf.path}` ({tf.action}): {tf.summary[:75]}{sym_str}")

        block = "\n".join(sections)
        if TokenCounter.estimate_tokens(block) > max_tokens:
            lines = block.splitlines()
            while lines and TokenCounter.estimate_tokens("\n".join(lines)) > max_tokens:
                lines.pop()
            block = "\n".join(lines)

        return block
