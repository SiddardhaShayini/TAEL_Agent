#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit Test Suite for TAEL Dynamic Task Router (tael_router.py)
-----------------------------------------------------------
Tests category classification, confidence scoring, prompt assignment,
tool subset selection, parameter presets, and fallback to General Chat.
"""

import unittest
from tael_router import (
    DynamicTaskRouter,
    TaskCategory,
    RouteDecision,
    route_task,
    get_category_profile,
    CATEGORY_PROFILES,
)


class TestDynamicTaskRouter(unittest.TestCase):

    def setUp(self):
        self.router = DynamicTaskRouter(confidence_threshold=0.35)

    def test_all_categories_defined(self):
        """Verifies that all 9 required categories are defined in the enum and profiles."""
        expected_categories = [
            TaskCategory.PROGRAMMING,
            TaskCategory.DEBUGGING,
            TaskCategory.REFACTORING,
            TaskCategory.SQL,
            TaskCategory.ARCHITECTURE,
            TaskCategory.GIT,
            TaskCategory.TOOL_USE,
            TaskCategory.MATH,
            TaskCategory.GENERAL_CHAT,
        ]
        self.assertEqual(len(expected_categories), 9)
        for cat in expected_categories:
            self.assertIn(cat, CATEGORY_PROFILES)
            profile = get_category_profile(cat)
            self.assertIsNotNone(profile.system_prompt)
            self.assertIsInstance(profile.tool_names, list)
            self.assertIn("temperature", profile.generation_params)
            self.assertIn("top_p", profile.generation_params)
            self.assertIn("max_tokens", profile.generation_params)

    def test_route_programming(self):
        """Tests classification of programming / algorithm prompt."""
        prompt = "Implement a Python function for Quickselect to find the k-th largest element in an array with O(n) average complexity."
        decision = self.router.route(prompt)
        self.assertEqual(decision.category, TaskCategory.PROGRAMMING)
        self.assertGreater(decision.confidence, 0.50)
        self.assertIn("write_file", decision.tool_names)
        self.assertIn("execute_python", decision.tool_names)
        self.assertAlmostEqual(decision.generation_params["temperature"], 0.15, places=2)
        self.assertFalse(decision.is_fallback)

    def test_route_debugging(self):
        """Tests classification of bug / traceback error diagnosis."""
        prompt = "Traceback (most recent call last): line 42, in fetch_data TypeError: object of type 'coroutine' has no len(). Fix this bug."
        decision = self.router.route(prompt)
        self.assertEqual(decision.category, TaskCategory.DEBUGGING)
        self.assertGreater(decision.confidence, 0.50)
        self.assertIn("search_text", decision.tool_names)
        self.assertIn("execute_python", decision.tool_names)
        self.assertAlmostEqual(decision.generation_params["temperature"], 0.20, places=2)
        self.assertFalse(decision.is_fallback)

    def test_route_refactoring(self):
        """Tests classification of code cleanup & guard clauses."""
        prompt = "Refactor this function to reduce cyclomatic complexity and eliminate nested if-else statements with guard clauses."
        decision = self.router.route(prompt)
        self.assertEqual(decision.category, TaskCategory.REFACTORING)
        self.assertGreater(decision.confidence, 0.50)
        self.assertIn("git_diff", decision.tool_names)
        self.assertAlmostEqual(decision.generation_params["temperature"], 0.20, places=2)
        self.assertFalse(decision.is_fallback)

    def test_route_sql(self):
        """Tests classification of database query / schema requests."""
        prompt = "Write an SQL query to SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id HAVING SUM(amount) > 500 ORDER BY 2 DESC;"
        decision = self.router.route(prompt)
        self.assertEqual(decision.category, TaskCategory.SQL)
        self.assertGreater(decision.confidence, 0.50)
        self.assertAlmostEqual(decision.generation_params["temperature"], 0.10, places=2)
        self.assertFalse(decision.is_fallback)

    def test_route_architecture(self):
        """Tests classification of high-level system design."""
        prompt = "How should we design a high-level system architecture comparing microservices vs monolith with an event-driven message queue?"
        decision = self.router.route(prompt)
        self.assertEqual(decision.category, TaskCategory.ARCHITECTURE)
        self.assertGreater(decision.confidence, 0.50)
        self.assertAlmostEqual(decision.generation_params["temperature"], 0.35, places=2)
        self.assertFalse(decision.is_fallback)

    def test_route_git(self):
        """Tests classification of version control and git workflows."""
        prompt = "How do I resolve a merge conflict during an interactive git rebase on origin/main?"
        decision = self.router.route(prompt)
        self.assertEqual(decision.category, TaskCategory.GIT)
        self.assertGreater(decision.confidence, 0.50)
        self.assertIn("git_status", decision.tool_names)
        self.assertIn("git_diff", decision.tool_names)
        self.assertIn("git_log", decision.tool_names)
        self.assertAlmostEqual(decision.generation_params["temperature"], 0.10, places=2)
        self.assertFalse(decision.is_fallback)

    def test_route_tool_use(self):
        """Tests classification of workspace agent file/folder/command creation."""
        prompt = "In TEMP_TAEL folder, create a simple static website with index.html, css, js, and run the command to verify it."
        decision = self.router.route(prompt)
        self.assertEqual(decision.category, TaskCategory.TOOL_USE)
        self.assertGreater(decision.confidence, 0.50)
        # Should include all primary agentic tools
        self.assertIn("write_file", decision.tool_names)
        self.assertIn("read_file", decision.tool_names)
        self.assertIn("execute_terminal_command", decision.tool_names)
        self.assertFalse(decision.is_fallback)

    def test_route_math(self):
        """Tests classification of numerical / mathematical reasoning."""
        prompt = "Calculate the harmonic mean and percentage markup: what is 45 * 1.25 / 15 + 10?"
        decision = self.router.route(prompt)
        self.assertEqual(decision.category, TaskCategory.MATH)
        self.assertGreater(decision.confidence, 0.50)
        self.assertEqual(decision.generation_params["temperature"], 0.00)
        self.assertIn("execute_python", decision.tool_names)
        self.assertFalse(decision.is_fallback)

    def test_route_general_chat(self):
        """Tests classification of conversational greeting / chat."""
        prompt = "Hello! Who are you, and what are you capable of doing?"
        decision = self.router.route(prompt)
        self.assertEqual(decision.category, TaskCategory.GENERAL_CHAT)
        self.assertGreater(decision.confidence, 0.50)
        self.assertAlmostEqual(decision.generation_params["temperature"], 0.70, places=2)
        self.assertFalse(decision.is_fallback)

    def test_fallback_on_ambiguous_or_gibberish(self):
        """Tests graceful fallback to General Chat when confidence is low or input is gibberish."""
        gibberish = "purple umbrella clouds sidewalk zebra jumping"
        decision = self.router.route(gibberish)
        self.assertEqual(decision.category, TaskCategory.GENERAL_CHAT)
        self.assertTrue(decision.is_fallback)
        self.assertIn("Fallback", decision.reasoning)

    def test_fallback_on_empty_string(self):
        """Tests graceful fallback on empty or whitespace string."""
        decision = self.router.route("    ")
        self.assertEqual(decision.category, TaskCategory.GENERAL_CHAT)
        self.assertTrue(decision.is_fallback)

    def test_confidence_scores_structure(self):
        """Verifies that all 9 categories receive normalized confidence scores."""
        prompt = "Can you write an algorithm to sort numbers?"
        decision = self.router.route(prompt)
        self.assertEqual(len(decision.all_scores), 9)
        for cat in TaskCategory:
            self.assertIn(cat.value, decision.all_scores)
            self.assertGreaterEqual(decision.all_scores[cat.value], 0.0)
            self.assertLessEqual(decision.all_scores[cat.value], 1.0)

    def test_decision_formatting_and_dict(self):
        """Verifies format_summary and to_dict methods."""
        decision = route_task("git status check")
        summary = decision.format_summary()
        self.assertIn("=== TAEL ROUTER DECISION", summary)
        self.assertIn("Git", summary)

        d = decision.to_dict()
        self.assertEqual(d["category"], TaskCategory.GIT.value)
        self.assertIn("all_scores", d)
        self.assertIn("generation_params", d)
        self.assertIn("system_prompt", d)


if __name__ == "__main__":
    unittest.main()
