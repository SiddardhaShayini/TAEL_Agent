#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAEL Memory System: Project Memory
----------------------------------
Manages persistent project-level knowledge, architectural decisions,
technical constraints, conventions, and facts.
Stored at `.tael/memory/project_memory.json`.
"""

import os
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

from .base import StorageHelper, TokenCounter


@dataclass
class ArchitectureDecision:
    """An architectural decision record (ADR) in project memory."""
    id: str
    title: str
    description: str
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArchitectureDecision":
        return cls(**data)


class ProjectMemory:
    """
    Persistent project memory tracker.
    Stores overarching architectural choices, constraints, facts, and conventions.
    """

    def __init__(self, workspace: str, file_path: Optional[str] = None):
        self.workspace = os.path.abspath(workspace)
        self.file_path = file_path or os.path.join(self.workspace, ".tael", "memory", "project_memory.json")
        self.project_name: str = os.path.basename(self.workspace)
        self.facts: Dict[str, Any] = {}
        self.decisions: List[ArchitectureDecision] = []
        self.conventions: List[str] = []
        self.updated_at: float = time.time()

        if os.path.exists(self.file_path):
            self.load()
        else:
            # Seed with default TAEL V2 architecture facts if new
            self._seed_defaults()

    def _seed_defaults(self):
        """Seeds initial default project facts for TAEL V2."""
        self.facts = {
            "project_name": "TAEL V2",
            "model_backbone": "IBM Granite 3.1 2B Instruct GGUF (Q4_K_M)",
            "hardware_budget": "8GB RAM laptop, CPU inference",
            "license": "Apache 2.0 (commercial-friendly)",
            "runtime_tools": "10 sandboxed tools with PathSandbox & CommandSandbox",
            "router_categories": "9 dynamic task categories with calibrated sampling",
        }
        self.conventions = [
            "Confine all file operations strictly to the designated workspace root.",
            "Do not modify training code or rerun training loops during runtime tasks.",
            "Always update project_memory.md when architectural updates occur.",
            "Emit valid <tool_call> XML blocks with JSON arguments for autonomous execution.",
        ]
        self.save()

    def set_fact(self, key: str, value: Any):
        """Sets a project-level fact or technical configuration."""
        self.facts[key] = value
        self.updated_at = time.time()
        self.save()

    def get_fact(self, key: str, default: Any = None) -> Any:
        return self.facts.get(key, default)

    def add_decision(self, title: str, description: str, tags: Optional[List[str]] = None) -> str:
        """Records an architectural decision."""
        decision_id = f"ADR-{len(self.decisions) + 1:03d}"
        adr = ArchitectureDecision(
            id=decision_id,
            title=title,
            description=description,
            tags=tags or [],
        )
        self.decisions.append(adr)
        self.updated_at = time.time()
        self.save()
        return decision_id

    def list_decisions(self, tag: Optional[str] = None) -> List[ArchitectureDecision]:
        if not tag:
            return list(self.decisions)
        return [d for d in self.decisions if tag.lower() in [t.lower() for t in d.tags]]

    def add_convention(self, rule: str):
        """Adds a project styling or operational convention."""
        if rule not in self.conventions:
            self.conventions.append(rule)
            self.updated_at = time.time()
            self.save()

    def format_context_block(self, max_tokens: int = 350) -> str:
        """
        Formats project memory into a compact markdown block suitable
        for system prompt injection without overflowing token budget.
        """
        lines = ["[PROJECT MEMORY]"]
        if self.facts:
            lines.append("Key Facts:")
            for k, v in list(self.facts.items())[:12]:
                lines.append(f"  - {k}: {v}")

        if self.conventions:
            lines.append("Conventions:")
            for c in self.conventions[:4]:
                lines.append(f"  - {c}")

        if self.decisions:
            lines.append("Recent Decisions:")
            for d in self.decisions[-3:]:
                lines.append(f"  - [{d.id}] {d.title}: {d.description[:80]}...")

        block = "\n".join(lines)
        if TokenCounter.estimate_tokens(block) > max_tokens:
            # Truncate lines defensively
            while lines and TokenCounter.estimate_tokens("\n".join(lines)) > max_tokens:
                lines.pop()
            block = "\n".join(lines)

        return block

    def save(self):
        """Serializes project memory to JSON file."""
        data = {
            "project_name": self.project_name,
            "updated_at": self.updated_at,
            "facts": self.facts,
            "conventions": self.conventions,
            "decisions": [d.to_dict() for d in self.decisions],
        }
        StorageHelper.save_json(self.file_path, data)

    def load(self):
        """Loads project memory from disk."""
        data = StorageHelper.load_json(self.file_path, {})
        if not data:
            return
        self.project_name = data.get("project_name", self.project_name)
        self.updated_at = data.get("updated_at", self.updated_at)
        self.facts = data.get("facts", {})
        self.conventions = data.get("conventions", [])
        self.decisions = [ArchitectureDecision.from_dict(d) for d in data.get("decisions", [])]
