#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAEL Memory System: Base Models & Budget Management
--------------------------------------------------
Foundational data structures, token budgeting, and persistence helpers.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict


# ==============================================================================
# 1. Token Counting & Budgeting
# ==============================================================================

class TokenCounter:
    """
    Lightweight, fast token estimator.
    Uses ~3.8 characters per token (standard empirical ratio for code + English).
    """

    CHARS_PER_TOKEN = 3.8

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        if not text:
            return 0
        return max(1, int(len(text) / cls.CHARS_PER_TOKEN))

    @classmethod
    def estimate_messages(cls, messages: List[Dict[str, str]]) -> int:
        total = 0
        for m in messages:
            total += 4  # Formatting overhead per message
            total += cls.estimate_tokens(m.get("content", ""))
        return total


@dataclass
class ContextBudget:
    """
    Strict context window allocation to prevent context overflow.
    Default tailored for 4096-token local Granite-2B inference.
    """
    max_context: int = 4096
    reserved_generation: int = 1024     # Guaranteed tokens for model generation
    system_prompt_budget: int = 800     # System prompt + base tool specifications
    retrieved_memory_budget: int = 600  # Relevant project/file/summary memories
    conversation_budget: int = 1600     # Sliding window conversation turns
    safety_margin: int = 72

    @property
    def max_input_tokens(self) -> int:
        """Maximum tokens allowed in prompt before triggering generation."""
        return self.max_context - self.reserved_generation - self.safety_margin


# ==============================================================================
# 2. Base Memory Item
# ==============================================================================

@dataclass
class MemoryItem:
    """Universal memory unit with timestamp and metadata."""
    id: str
    content: str
    category: str
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryItem":
        return cls(**data)


# ==============================================================================
# 3. Persistent JSON Storage Helper
# ==============================================================================

class StorageHelper:
    """Safely reads and writes JSON memory structures to disk."""

    @staticmethod
    def ensure_dir(dir_path: str):
        os.makedirs(dir_path, exist_ok=True)

    @staticmethod
    def load_json(file_path: str, default: Any = None) -> Any:
        if not os.path.exists(file_path):
            return default if default is not None else {}
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Failed to load JSON from {file_path}: {e}")
            return default if default is not None else {}

    @staticmethod
    def save_json(file_path: str, data: Any):
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        tmp_path = file_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        # Atomic rename
        if os.path.exists(file_path):
            os.remove(file_path)
        os.rename(tmp_path, file_path)
