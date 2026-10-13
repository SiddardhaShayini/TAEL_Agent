#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAEL Persistent Memory System (tael_memory)
-------------------------------------------
4 Pillars of Memory:
  - ConversationMemory: Multi-turn dialogue, tool logs, session persistence
  - ProjectMemory: Architecture decisions, technical constraints, conventions
  - FileMemory: Tracked files, mutations, summaries, symbols, hashes
  - SummaryMemory: Rolling executive summaries, auto-compaction
Features:
  - Automatic summarization of long conversations
  - Relevance retrieval (only relevant context pulled)
  - Strict context overflow prevention via ContextBudget
"""

from .base import (
    ContextBudget,
    TokenCounter,
    MemoryItem,
    StorageHelper,
)
from .conversation import (
    ConversationMemory,
    ConversationTurn,
)
from .project import (
    ProjectMemory,
    ArchitectureDecision,
)
from .file_tracker import (
    FileMemory,
    TrackedFile,
)
from .summary import (
    SummaryMemory,
    SummaryState,
)
from .retriever import (
    MemoryRetriever,
)
from .manager import (
    MemoryManager,
    create_memory_manager,
)

__all__ = [
    "ContextBudget",
    "TokenCounter",
    "MemoryItem",
    "StorageHelper",
    "ConversationMemory",
    "ConversationTurn",
    "ProjectMemory",
    "ArchitectureDecision",
    "FileMemory",
    "TrackedFile",
    "SummaryMemory",
    "SummaryState",
    "MemoryRetriever",
    "MemoryManager",
    "create_memory_manager",
]
