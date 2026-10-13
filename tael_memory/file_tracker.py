#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAEL Memory System: File Memory
-------------------------------
Tracks files inspected, created, modified, or executed during agent sessions.
Prevents repetitive file reads, maintains summaries and key symbols.
Stored at `.tael/memory/file_memory.json`.
"""

import os
import re
import time
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict

from .base import StorageHelper, TokenCounter


@dataclass
class TrackedFile:
    """Record of an accessed, modified, or created file."""
    path: str
    action: str                        # 'read', 'created', 'modified', 'inspected'
    summary: str = ""
    symbols: List[str] = field(default_factory=list)
    line_count: int = 0
    content_hash: str = ""
    last_updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrackedFile":
        return cls(**data)


class FileMemory:
    """
    Persistent file tracker memory.
    Maintains awareness of active workspace files, their purposes, and key symbols.
    """

    def __init__(self, workspace: str, file_path: Optional[str] = None):
        self.workspace = os.path.abspath(workspace)
        self.file_path = file_path or os.path.join(self.workspace, ".tael", "memory", "file_memory.json")
        self.files: Dict[str, TrackedFile] = {}
        self.updated_at: float = time.time()

        if os.path.exists(self.file_path):
            self.load()

    def record_action(
        self,
        rel_path: str,
        action: str,
        summary: Optional[str] = None,
        symbols: Optional[List[str]] = None,
        content: Optional[str] = None,
    ) -> TrackedFile:
        """
        Records an interaction with a file.
        Automatically computes hash, line count, and extracts symbols if content is provided.
        """
        norm_path = os.path.normpath(rel_path).replace("\\", "/")

        # Compute hash and line count if content is passed
        content_hash = ""
        line_count = 0
        extracted_symbols = symbols or []

        if content is not None:
            content_hash = hashlib.md5(content.encode("utf-8")).hexdigest()[:10]
            line_count = len(content.splitlines())
            if not extracted_symbols:
                extracted_symbols = self._extract_symbols(content, norm_path)

        # Generate a concise fallback summary if none provided
        auto_summary = summary
        if not auto_summary:
            if action == "created":
                auto_summary = f"Created new file with {line_count} lines."
            elif action == "read":
                auto_summary = f"Read and analyzed file ({line_count} lines)."
            elif action == "modified":
                auto_summary = f"Updated content ({line_count} lines)."
            else:
                auto_summary = f"Inspected file."

        tracked = TrackedFile(
            path=norm_path,
            action=action,
            summary=auto_summary,
            symbols=extracted_symbols,
            line_count=line_count,
            content_hash=content_hash,
            last_updated=time.time(),
        )

        self.files[norm_path] = tracked
        self.updated_at = time.time()
        self.save()
        return tracked

    def get_file(self, rel_path: str) -> Optional[TrackedFile]:
        norm_path = os.path.normpath(rel_path).replace("\\", "/")
        return self.files.get(norm_path)

    def list_files(self) -> List[TrackedFile]:
        return sorted(self.files.values(), key=lambda f: f.last_updated, reverse=True)

    def format_context_block(
        self,
        relevant_paths: Optional[List[str]] = None,
        max_tokens: int = 350,
    ) -> str:
        """
        Formats tracked file memories into a compact markdown block.
        If relevant_paths is supplied, filters down to only those files.
        """
        if not self.files:
            return ""

        target_files = []
        if relevant_paths:
            for p in relevant_paths:
                norm = os.path.normpath(p).replace("\\", "/")
                if norm in self.files:
                    target_files.append(self.files[norm])
        else:
            # Take the 5 most recently updated files
            target_files = self.list_files()[:5]

        if not target_files:
            return ""

        lines = ["[FILE MEMORY] (Recently Touched Files):"]
        for tf in target_files:
            sym_str = f" | Symbols: {', '.join(tf.symbols[:4])}" if tf.symbols else ""
            lines.append(f"  - `{tf.path}` ({tf.action}, {tf.line_count} lines): {tf.summary[:70]}{sym_str}")

        block = "\n".join(lines)
        if TokenCounter.estimate_tokens(block) > max_tokens:
            while lines and TokenCounter.estimate_tokens("\n".join(lines)) > max_tokens:
                lines.pop()
            block = "\n".join(lines)

        return block

    def _extract_symbols(self, content: str, file_path: str) -> List[str]:
        """Heuristic symbol extractor for Python, JS, and HTML."""
        symbols = []
        ext = os.path.splitext(file_path)[1].lower()

        if ext in [".py"]:
            # Classes and functions (supporting indented methods and functions)
            matches = re.findall(r"^\s*(?:def|class)\s+([a-zA-Z0-9_]+)", content, re.MULTILINE)
            symbols.extend(matches[:12])
        elif ext in [".js", ".ts"]:
            matches = re.findall(r"(?:function|class|const|let|var)\s+([a-zA-Z0-9_]+)\s*=?\s*(?:function|\()?", content)
            symbols.extend(matches[:8])
        elif ext in [".html"]:
            tags = re.findall(r"<([a-zA-Z0-9_\-]+)\s+id=[\"']([^\"']+)[\"']", content)
            symbols.extend([f"#{t[1]}" for t in tags[:6]])

        return list(dict.fromkeys(symbols))  # Remove duplicates preserving order

    def save(self):
        """Serializes file memory to disk."""
        data = {
            "updated_at": self.updated_at,
            "files": {path: tf.to_dict() for path, tf in self.files.items()},
        }
        StorageHelper.save_json(self.file_path, data)

    def load(self):
        """Loads file memory from disk."""
        data = StorageHelper.load_json(self.file_path, {})
        if not data:
            return
        self.updated_at = data.get("updated_at", self.updated_at)
        raw_files = data.get("files", {})
        self.files = {p: TrackedFile.from_dict(v) for p, v in raw_files.items()}
