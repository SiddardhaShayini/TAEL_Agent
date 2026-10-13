#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAEL Memory System: Conversation Memory
---------------------------------------
Manages persistent multi-turn dialogue, tool interactions, and session history.
Stored under `.tael/memory/conversations/<session_id>.json`.
"""

import os
import time
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

from .base import StorageHelper, TokenCounter


@dataclass
class ConversationTurn:
    """Represents a single message turn in the dialogue."""
    role: str                       # 'user', 'assistant', 'system', 'tool'
    content: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationTurn":
        return cls(**data)


class ConversationMemory:
    """
    Persistent conversation memory manager.
    Tracks sequential turns, token usage, and serializes sessions to disk.
    """

    def __init__(
        self,
        workspace: str,
        session_id: Optional[str] = None,
        storage_dir: Optional[str] = None,
    ):
        self.workspace = os.path.abspath(workspace)
        self.session_id = session_id or f"session_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        self.storage_dir = storage_dir or os.path.join(self.workspace, ".tael", "memory", "conversations")
        self.file_path = os.path.join(self.storage_dir, f"{self.session_id}.json")
        self.turns: List[ConversationTurn] = []
        self.created_at = time.time()
        self.updated_at = time.time()

        StorageHelper.ensure_dir(self.storage_dir)
        if os.path.exists(self.file_path):
            self.load()

    def add_user(self, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Appends a user turn."""
        turn = ConversationTurn(
            role="user",
            content=content,
            metadata=metadata or {},
        )
        self.turns.append(turn)
        self.updated_at = time.time()
        self.save()

    def add_assistant(
        self,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Appends an assistant turn with optional tool calls."""
        meta = metadata or {}
        if tool_calls:
            meta["tool_calls"] = tool_calls
        turn = ConversationTurn(
            role="assistant",
            content=content,
            metadata=meta,
        )
        self.turns.append(turn)
        self.updated_at = time.time()
        self.save()

    def add_tool_result(
        self,
        tool_name: str,
        output: str,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Appends a tool execution result as a system/tool turn."""
        meta = metadata or {}
        meta["tool"] = tool_name
        meta["success"] = success
        formatted_content = f"<tool_response tool=\"{tool_name}\" status=\"{'success' if success else 'error'}\">\n{output}\n</tool_response>"
        turn = ConversationTurn(
            role="user",
            content=formatted_content,
            metadata=meta,
        )
        self.turns.append(turn)
        self.updated_at = time.time()
        self.save()

    def get_messages(self, limit: Optional[int] = None) -> List[Dict[str, str]]:
        """Returns standard OpenAI-style message dicts for inference."""
        turns_to_use = self.turns[-limit:] if limit else self.turns
        return [{"role": t.role, "content": t.content} for t in turns_to_use]

    def total_tokens(self) -> int:
        """Estimates total token count of the active dialogue."""
        return TokenCounter.estimate_messages(self.get_messages())

    def turn_count(self) -> int:
        return len(self.turns)

    def prune_oldest(self, count: int) -> List[ConversationTurn]:
        """Removes and returns the oldest `count` turns."""
        if count <= 0:
            return []
        removed = self.turns[:count]
        self.turns = self.turns[count:]
        self.updated_at = time.time()
        self.save()
        return removed

    def save(self):
        """Serializes session to JSON file."""
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "turn_count": len(self.turns),
            "estimated_tokens": self.total_tokens(),
            "turns": [t.to_dict() for t in self.turns],
        }
        StorageHelper.save_json(self.file_path, data)

    def load(self):
        """Loads session from JSON file."""
        data = StorageHelper.load_json(self.file_path, {})
        if not data:
            return
        self.session_id = data.get("session_id", self.session_id)
        self.created_at = data.get("created_at", self.created_at)
        self.updated_at = data.get("updated_at", self.updated_at)
        raw_turns = data.get("turns", [])
        self.turns = [ConversationTurn.from_dict(t) for t in raw_turns]

    @classmethod
    def list_sessions(cls, workspace: str) -> List[Dict[str, Any]]:
        """Lists all existing saved sessions in the workspace."""
        conv_dir = os.path.join(os.path.abspath(workspace), ".tael", "memory", "conversations")
        if not os.path.exists(conv_dir):
            return []
        sessions = []
        for fname in os.listdir(conv_dir):
            if fname.endswith(".json"):
                fpath = os.path.join(conv_dir, fname)
                data = StorageHelper.load_json(fpath, {})
                if data:
                    sessions.append({
                        "session_id": data.get("session_id", fname[:-5]),
                        "turn_count": data.get("turn_count", 0),
                        "estimated_tokens": data.get("estimated_tokens", 0),
                        "updated_at": data.get("updated_at", 0),
                        "path": fpath,
                    })
        return sorted(sessions, key=lambda s: s["updated_at"], reverse=True)
