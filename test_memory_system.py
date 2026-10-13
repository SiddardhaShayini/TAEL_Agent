#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Test Suite for TAEL Persistent Memory System (tael_memory)
--------------------------------------------------------------
Tests:
  - Conversation Memory (persistence, turns, pruning)
  - Project Memory (facts, ADRs, conventions, persistence)
  - File Memory (file actions, hashing, symbol extraction)
  - Summary Memory (rolling auto-compaction of long dialogue)
  - Relevance Retrieval (retrieving ONLY relevant context)
  - Context Overflow Prevention (ContextBudget enforcement)
"""

import os
import shutil
import tempfile
import unittest

from tael_memory import (
    MemoryManager,
    ConversationMemory,
    ProjectMemory,
    FileMemory,
    SummaryMemory,
    MemoryRetriever,
    ContextBudget,
    TokenCounter,
)


class TestTaelMemorySystem(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="tael_memory_test_")
        self.manager = MemoryManager(self.test_dir, session_id="test_session_001")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # --------------------------------------------------------------------------
    # 1. Conversation Memory Tests
    # --------------------------------------------------------------------------

    def test_conversation_memory_turns_and_persistence(self):
        """Verifies adding turns, saving to disk, and loading."""
        conv = self.manager.conversation
        conv.add_user("Write a python script for quicksort.")
        conv.add_assistant("Here is the script.", tool_calls=[{"tool": "write_file", "path": "quicksort.py"}])
        conv.add_tool_result("write_file", "File written successfully.", success=True)

        self.assertEqual(conv.turn_count(), 3)
        self.assertGreater(conv.total_tokens(), 10)
        self.assertTrue(os.path.exists(conv.file_path))

        # Test reload in fresh instance
        reloaded = ConversationMemory(self.test_dir, session_id="test_session_001")
        self.assertEqual(reloaded.turn_count(), 3)
        self.assertEqual(reloaded.turns[0].content, "Write a python script for quicksort.")

    def test_conversation_list_sessions(self):
        """Verifies listing multiple saved sessions."""
        self.manager.record_user_message("Hello from session 1")
        sess2 = ConversationMemory(self.test_dir, session_id="session_test_two")
        sess2.add_user("Hello from session 2")

        sessions = ConversationMemory.list_sessions(self.test_dir)
        self.assertGreaterEqual(len(sessions), 2)
        session_ids = [s["session_id"] for s in sessions]
        self.assertIn("test_session_001", session_ids)
        self.assertIn("session_test_two", session_ids)

    # --------------------------------------------------------------------------
    # 2. Project Memory Tests
    # --------------------------------------------------------------------------

    def test_project_memory_facts_and_decisions(self):
        """Verifies storing and retrieving facts and architectural decisions."""
        pm = self.manager.project
        pm.set_fact("database", "SQLite 3 with WAL mode")
        self.assertEqual(pm.get_fact("database"), "SQLite 3 with WAL mode")

        adr_id = pm.add_decision(
            title="Use GGUF Q4_K_M for local inference",
            description="Fits in 1.47GB RAM budget on 8GB laptops.",
            tags=["quantization", "gguf", "ram"]
        )
        self.assertIn("ADR-", adr_id)

        decisions = pm.list_decisions(tag="gguf")
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].title, "Use GGUF Q4_K_M for local inference")

        # Test context block formatting
        block = pm.format_context_block()
        self.assertIn("[PROJECT MEMORY]", block)
        self.assertIn("SQLite 3", block)

    # --------------------------------------------------------------------------
    # 3. File Memory Tests
    # --------------------------------------------------------------------------

    def test_file_memory_actions_and_symbol_extraction(self):
        """Verifies tracking file mutations, calculating hashes, and extracting symbols."""
        fm = self.manager.file
        code = (
            "class AuthService:\n"
            "    def authenticate(self, username, password):\n"
            "        return True\n"
            "\n"
            "def verify_token(token):\n"
            "    pass\n"
        )
        tracked = fm.record_action(
            rel_path="src/auth.py",
            action="created",
            summary="User authentication and JWT token verification service.",
            content=code,
        )

        self.assertEqual(tracked.path, "src/auth.py")
        self.assertEqual(tracked.line_count, 6)
        self.assertIn("AuthService", tracked.symbols)
        self.assertIn("authenticate", tracked.symbols)
        self.assertIn("verify_token", tracked.symbols)
        self.assertTrue(len(tracked.content_hash) > 0)

        # Context block formatting
        block = fm.format_context_block()
        self.assertIn("[FILE MEMORY]", block)
        self.assertIn("src/auth.py", block)
        self.assertIn("AuthService", block)

    # --------------------------------------------------------------------------
    # 4. Summary Memory & Auto-Compaction Tests
    # --------------------------------------------------------------------------

    def test_auto_summarize_long_conversations(self):
        """Verifies that long conversations are automatically compacted into Summary Memory."""
        conv = self.manager.conversation
        summary = self.manager.summary

        # Add 12 turns exceeding the 8-turn threshold
        for i in range(1, 13):
            conv.add_user(f"Task step {i}: Inspect and modify module_{i}.py")
            conv.add_assistant(
                f"Completed step {i}.",
                tool_calls=[{"tool": "write_file", "path": f"module_{i}.py"}]
            )

        self.assertEqual(conv.turn_count(), 24)

        # Trigger auto-compaction (keep 4 most recent turns)
        compacted = self.manager.auto_compact_if_needed(turn_threshold=8, keep_recent_turns=4)
        self.assertTrue(compacted)

        # Active turns reduced to 4
        self.assertEqual(conv.turn_count(), 4)

        # Summary contains compacted history
        self.assertTrue(summary.has_summary())
        self.assertEqual(summary.state.compacted_turn_count, 20)
        self.assertIn("write_file", summary.state.tools_invoked)

        # Format context block
        block = summary.format_context_block()
        self.assertIn("[SUMMARY OF PRIOR CONVERSATION]", block)
        self.assertIn("20 turns compacted", block)

    # --------------------------------------------------------------------------
    # 5. Relevance Retrieval Engine Tests
    # --------------------------------------------------------------------------

    def test_retrieve_only_relevant_context(self):
        """Verifies that the retriever ONLY pulls context relevant to the user query."""
        fm = self.manager.file
        pm = self.manager.project

        # Track 3 different files
        fm.record_action(
            "src/auth.py",
            action="created",
            summary="Authentication service handling user login and JWT verification.",
            symbols=["AuthService", "verify_token"],
        )
        fm.record_action(
            "src/database.py",
            action="created",
            summary="PostgreSQL connection pool and transaction manager.",
            symbols=["DBPool", "execute_query"],
        )
        fm.record_action(
            "frontend/styles.css",
            action="created",
            summary="CSS styles for responsive button and navigation layout.",
        )

        # Add an ADR
        pm.add_decision(
            title="JWT Token Expiration Policy",
            description="Tokens expire after 15 minutes; refresh tokens after 7 days.",
            tags=["auth", "jwt", "security"],
        )

        # Query specifically about authentication
        auth_query = "Why is verify_token throwing an exception in auth.py?"
        relevant_files = MemoryRetriever.retrieve_relevant_files(auth_query, fm)
        self.assertEqual(len(relevant_files), 1)
        self.assertEqual(relevant_files[0].path, "src/auth.py")

        # Verify that unrelated files (styles.css, database.py) were NOT retrieved
        retrieved_paths = [rf.path for rf in relevant_files]
        self.assertNotIn("frontend/styles.css", retrieved_paths)
        self.assertNotIn("src/database.py", retrieved_paths)

        # Test combined context block
        context_block = MemoryRetriever.build_relevant_context(auth_query, fm, pm)
        self.assertIn("src/auth.py", context_block)
        self.assertIn("JWT Token Expiration Policy", context_block)
        self.assertNotIn("styles.css", context_block)

    def test_retriever_empty_when_no_relevance(self):
        """Verifies that queries with no relevant tracked files return empty context to save tokens."""
        fm = self.manager.file
        pm = self.manager.project
        fm.record_action("backend/worker.py", "created", summary="Celery background task queue.")

        irrelevant_query = "What is the capital city of France?"
        context = MemoryRetriever.build_relevant_context(irrelevant_query, fm, pm)
        # Should not include worker.py
        self.assertNotIn("backend/worker.py", context)

    # --------------------------------------------------------------------------
    # 6. Context Overflow Prevention Tests
    # --------------------------------------------------------------------------

    def test_prevent_context_overflow(self):
        """
        Verifies that prepare_messages_for_inference strictly caps input tokens
        and prevents context overflow by auto-compacting and enforcing budget.
        """
        # Create a small custom budget to test boundary enforcement
        tight_budget = ContextBudget(
            max_context=1000,
            reserved_generation=300,
            safety_margin=50,
        )
        tight_manager = MemoryManager(self.test_dir, session_id="overflow_test", budget=tight_budget)

        # Add multiple large conversation turns
        large_text = "Here is a large piece of code data: " + ("x" * 200) + "\n"
        for i in range(10):
            tight_manager.record_user_message(f"Step {i}: {large_text}")
            tight_manager.record_assistant_message(f"Assistant response {i}: {large_text}")

        # Prepare messages
        messages = tight_manager.prepare_messages_for_inference(
            system_prompt="You are TAEL assistant.",
            user_prompt="Continue the work.",
            max_active_turns=4,
        )

        # Total tokens in prepared messages must NOT exceed max_input_tokens (650 tokens)
        total_tokens = TokenCounter.estimate_messages(messages)
        self.assertLessEqual(total_tokens, tight_budget.max_input_tokens)
        self.assertTrue(tight_manager.summary.has_summary())


if __name__ == "__main__":
    unittest.main()
