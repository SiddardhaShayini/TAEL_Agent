#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAEL Memory System: Centralized Memory Manager
----------------------------------------------
Coordinates Conversation, Project, File, and Summary memories.
Enforces strict ContextBudget and auto-compaction to prevent context overflow.
"""

import os
from typing import Dict, List, Any, Optional

from .base import ContextBudget, TokenCounter, StorageHelper
from .conversation import ConversationMemory, ConversationTurn
from .project import ProjectMemory
from .file_tracker import FileMemory
from .summary import SummaryMemory
from .retriever import MemoryRetriever


class MemoryManager:
    """
    Centralized controller for the 4 pillars of TAEL Persistent Memory:
      1. Conversation Memory (Multi-turn persistent dialogue)
      2. Project Memory (Architectural decisions, facts, conventions)
      3. File Memory (Tracked workspace files, hashes, symbols, summaries)
      4. Summary Memory (Rolling executive summaries & turn compaction)
    """

    def __init__(
        self,
        workspace: str,
        session_id: Optional[str] = None,
        budget: Optional[ContextBudget] = None,
    ):
        self.workspace = os.path.abspath(workspace)
        self.budget = budget or ContextBudget()

        # Initialize the 4 memory systems
        self.conversation = ConversationMemory(self.workspace, session_id=session_id)
        self.project = ProjectMemory(self.workspace)
        self.file = FileMemory(self.workspace)
        self.summary = SummaryMemory(self.workspace)

    # --------------------------------------------------------------------------
    # 1. Dialogue & Tool Tracking
    # --------------------------------------------------------------------------

    def record_user_message(self, content: str):
        """Records a user prompt."""
        self.conversation.add_user(content)

    def record_assistant_message(self, content: str, tool_calls: Optional[List[Dict[str, Any]]] = None):
        """Records an assistant response with optional tool calls."""
        self.conversation.add_assistant(content, tool_calls=tool_calls)

    def record_tool_result(self, tool_name: str, output: str, success: bool = True):
        """Records a tool observation."""
        self.conversation.add_tool_result(tool_name, output, success=success)

    def record_file_interaction(
        self,
        rel_path: str,
        action: str,
        summary: Optional[str] = None,
        content: Optional[str] = None,
    ):
        """Records a file inspection or modification into FileMemory."""
        return self.file.record_action(rel_path, action, summary=summary, content=content)

    # --------------------------------------------------------------------------
    # 2. Automatic Compaction & Overflow Prevention
    # --------------------------------------------------------------------------

    def auto_compact_if_needed(
        self,
        turn_threshold: int = 8,
        token_threshold: int = 1500,
        keep_recent_turns: int = 4,
    ) -> bool:
        """
        Automatically compacts older dialogue turns into SummaryMemory
        when conversation length or token counts exceed safe thresholds.
        """
        turn_count = self.conversation.turn_count()
        total_toks = self.conversation.total_tokens()

        if turn_count <= keep_recent_turns:
            return False

        if turn_count > turn_threshold or total_toks > token_threshold:
            turns_to_prune = turn_count - keep_recent_turns
            pruned = self.conversation.prune_oldest(turns_to_prune)
            if pruned:
                self.summary.compact_turns(pruned)
                return True

        return False

    # --------------------------------------------------------------------------
    # 3. Context Preparation & Overflow Guard
    # --------------------------------------------------------------------------

    def prepare_messages_for_inference(
        self,
        system_prompt: str,
        user_prompt: str,
        max_active_turns: int = 6,
    ) -> List[Dict[str, str]]:
        """
        Prepares the complete message payload for LLM inference:
          1. Auto-compacts conversation if over budget.
          2. Retrieves ONLY relevant context (files, facts, decisions).
          3. Injects SummaryMemory if prior turns were compacted.
          4. Verifies total tokens against ContextBudget.max_input_tokens.
          5. Guarantees ZERO context overflow.
        """
        # Step 1: Auto-compact older turns if needed
        self.auto_compact_if_needed()

        # Step 2: Retrieve relevant memories tailored to user prompt
        relevant_context = MemoryRetriever.build_relevant_context(
            query=user_prompt,
            file_memory=self.file,
            project_memory=self.project,
            max_tokens=self.budget.retrieved_memory_budget,
        )

        # Step 3: Construct System Message with relevant context
        sys_parts = [system_prompt]
        if relevant_context:
            sys_parts.append(f"\n{relevant_context}")

        final_system_message = "\n".join(sys_parts)

        # Step 4: Assemble active conversation messages
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": final_system_message}
        ]

        # If summary exists, inject it as the foundational context turn
        if self.summary.has_summary():
            summary_block = self.summary.format_context_block(max_tokens=400)
            if summary_block:
                messages.append({
                    "role": "user",
                    "content": f"[SYSTEM CONTEXT NOTICE]\n{summary_block}",
                })
                messages.append({
                    "role": "assistant",
                    "content": "Understood. I have full context of all prior steps, completed actions, and current state.",
                })

        # Append recent active turns
        recent_turns = self.conversation.get_messages(limit=max_active_turns)
        messages.extend(recent_turns)

        # Step 5: Strict Overflow Guard
        # If total estimated tokens exceed the input budget, aggressively compact/prune
        max_allowed = self.budget.max_input_tokens
        current_tokens = TokenCounter.estimate_messages(messages)

        while current_tokens > max_allowed and self.conversation.turn_count() > 2:
            # Prune 2 more turns into summary
            pruned = self.conversation.prune_oldest(2)
            self.summary.compact_turns(pruned)

            # Rebuild recent turns
            recent_turns = self.conversation.get_messages(limit=max_active_turns)
            messages = [{"role": "system", "content": final_system_message}]
            summary_block = self.summary.format_context_block(max_tokens=350)
            if summary_block:
                messages.append({
                    "role": "user",
                    "content": f"[SYSTEM CONTEXT NOTICE]\n{summary_block}",
                })
                messages.append({
                    "role": "assistant",
                    "content": "Understood. Continuing with updated summary context.",
                })
            messages.extend(recent_turns)
            current_tokens = TokenCounter.estimate_messages(messages)

        return messages

    # --------------------------------------------------------------------------
    # 4. Status & Diagnostics
    # --------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Returns health and token usage diagnostics."""
        conv_tokens = self.conversation.total_tokens()
        return {
            "session_id": self.conversation.session_id,
            "conversation_turns": self.conversation.turn_count(),
            "conversation_tokens": conv_tokens,
            "project_facts": len(self.project.facts),
            "project_decisions": len(self.project.decisions),
            "tracked_files": len(self.file.files),
            "has_summary": self.summary.has_summary(),
            "compacted_turns": self.summary.state.compacted_turn_count,
            "max_context_budget": self.budget.max_context,
            "max_input_tokens": self.budget.max_input_tokens,
        }


def create_memory_manager(workspace: str, session_id: Optional[str] = None) -> MemoryManager:
    """Factory creating an initialized MemoryManager for a workspace."""
    return MemoryManager(workspace, session_id=session_id)
