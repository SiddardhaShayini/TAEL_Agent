#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAEL Memory System: Summary Memory & Auto-Summarization
-------------------------------------------------------
Maintains rolling executive summaries of past conversation turns.
Automatically compresses long agent trajectories to prevent context overflow.
Stored at `.tael/memory/summary_memory.json`.
"""

import os
import re
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field, asdict

from .base import StorageHelper, TokenCounter
from .conversation import ConversationTurn


@dataclass
class SummaryState:
    """Represents the ongoing executive summary state."""
    executive_summary: str = ""
    compacted_turn_count: int = 0
    key_findings: List[str] = field(default_factory=list)
    files_touched: List[str] = field(default_factory=list)
    tools_invoked: List[str] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SummaryState":
        return cls(**data)


class SummaryMemory:
    """
    Rolling summary memory manager.
    Compacts older dialogue turns into a persistent executive summary block.
    """

    def __init__(
        self,
        workspace: str,
        file_path: Optional[str] = None,
        custom_summarizer: Optional[Callable[[List[ConversationTurn], str], str]] = None,
    ):
        self.workspace = os.path.abspath(workspace)
        self.file_path = file_path or os.path.join(self.workspace, ".tael", "memory", "summary_memory.json")
        self.state = SummaryState()
        self.custom_summarizer = custom_summarizer

        if os.path.exists(self.file_path):
            self.load()

    def has_summary(self) -> bool:
        return bool(self.state.executive_summary.strip())

    def compact_turns(self, turns: List[ConversationTurn]) -> str:
        """
        Compresses a sequence of ConversationTurn objects into the ongoing summary.
        Updates key findings, files touched, tools used, and synthesis.
        """
        if not turns:
            return self.state.executive_summary

        if self.custom_summarizer:
            try:
                new_summary = self.custom_summarizer(turns, self.state.executive_summary)
                self.state.executive_summary = new_summary
                self.state.compacted_turn_count += len(turns)
                self.state.updated_at = time.time()
                self.save()
                return self.state.executive_summary
            except Exception as e:
                print(f"[WARN] Custom summarizer failed: {e}. Falling back to deterministic compaction.")

        # Deterministic Rule-Based Extractive Compaction (Zero latency, 0 GPU memory)
        extracted_goals = []
        extracted_tools = []
        extracted_files = []
        extracted_findings = []

        for turn in turns:
            content = turn.content.strip()

            # Analyze user turn
            if turn.role == "user":
                if content.startswith("<tool_response") or "tool" in turn.metadata:
                    t_name = turn.metadata.get("tool")
                    status = "success" if turn.metadata.get("success", True) else "error"
                    if not t_name:
                        m = re.search(r'tool="([^"]+)"\s+status="([^"]+)"', content)
                        if m:
                            t_name, status = m.group(1), m.group(2)
                    if t_name:
                        extracted_tools.append(t_name)
                        if status == "error":
                            extracted_findings.append(f"Encountered error in {t_name}")
                else:
                    # User request or guidance
                    cleaned = content[:120].replace("\n", " ")
                    extracted_goals.append(cleaned)

            # Analyze assistant turn
            elif turn.role == "assistant":
                # 1. Detect tool calls in metadata
                meta_tc = turn.metadata.get("tool_calls", [])
                if isinstance(meta_tc, list):
                    for item in meta_tc:
                        if isinstance(item, dict):
                            t = item.get("tool") or item.get("name")
                            if t:
                                extracted_tools.append(t)

                # 2. Detect tool calls in text content
                tc_matches = re.findall(r'<tool_call>\s*\{.*?"tool":\s*"([^"]+)".*?\}\s*</tool_call>', content, re.DOTALL)
                for tc in tc_matches:
                    extracted_tools.append(tc)

                # Detect mentioned file paths
                file_matches = re.findall(r'["\']([a-zA-Z0-9_\-\./\\]+\.[a-zA-Z0-9]{1,5})["\']', content)
                for fm in file_matches:
                    if "/" in fm or "\\" in fm or "." in fm:
                        extracted_files.append(fm)

        # Merge extracted data into ongoing state
        self.state.compacted_turn_count += len(turns)
        for t in extracted_tools:
            if t not in self.state.tools_invoked:
                self.state.tools_invoked.append(t)
        for f in extracted_files:
            if f not in self.state.files_touched:
                self.state.files_touched.append(f)
        for g in extracted_goals:
            if g not in self.state.key_findings:
                self.state.key_findings.append(f"User Goal: {g}")
        for find in extracted_findings:
            if find not in self.state.key_findings:
                self.state.key_findings.append(find)

        # Build clean synthesized executive summary
        summary_lines = []
        if extracted_goals:
            summary_lines.append(f"Goals Addressed: {'; '.join(extracted_goals[-3:])}")
        if self.state.tools_invoked:
            summary_lines.append(f"Tools Executed: {', '.join(self.state.tools_invoked[-6:])}")
        if self.state.files_touched:
            summary_lines.append(f"Files Modified/Read: {', '.join(self.state.files_touched[-5:])}")
        if extracted_findings:
            summary_lines.append(f"Key Observations: {'; '.join(extracted_findings[-3:])}")

        new_chunk = " | ".join(summary_lines)
        if self.state.executive_summary:
            self.state.executive_summary = (
                f"{self.state.executive_summary}\n"
                f"- [Step {self.state.compacted_turn_count - len(turns) + 1}-{self.state.compacted_turn_count}]: {new_chunk}"
            )
        else:
            self.state.executive_summary = f"- [Initial Steps 1-{self.state.compacted_turn_count}]: {new_chunk}"

        self.state.updated_at = time.time()
        self.save()
        return self.state.executive_summary

    def format_context_block(self, max_tokens: int = 400) -> str:
        """
        Formats summary memory into a compact markdown block
        to inject into conversation history without overflowing budget.
        """
        if not self.has_summary():
            return ""

        lines = [
            f"[SUMMARY OF PRIOR CONVERSATION] ({self.state.compacted_turn_count} turns compacted):",
            self.state.executive_summary,
        ]
        block = "\n".join(lines)

        if TokenCounter.estimate_tokens(block) > max_tokens:
            # Keep header and most recent summary lines
            summary_lines = self.state.executive_summary.splitlines()
            while summary_lines and TokenCounter.estimate_tokens("\n".join(summary_lines)) > (max_tokens - 40):
                summary_lines.pop(0)  # Drop oldest summary lines
            block = f"{lines[0]}\n...\n" + "\n".join(summary_lines)

        return block

    def clear(self):
        """Resets summary state."""
        self.state = SummaryState()
        self.save()

    def save(self):
        """Serializes summary to JSON."""
        StorageHelper.save_json(self.file_path, self.state.to_dict())

    def load(self):
        """Loads summary from disk."""
        data = StorageHelper.load_json(self.file_path, {})
        if data:
            self.state = SummaryState.from_dict(data)
