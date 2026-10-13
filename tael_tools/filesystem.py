# -*- coding: utf-8 -*-
"""
TAEL Tool System - Sandboxed Filesystem Tools
--------------------------------------------
Implements:
  1. Read File (read_file)
  2. Write File (write_file)
  3. List Directory (list_dir)
  4. Search Text (search_text)
"""

import os
import re
import fnmatch
from typing import Dict, Any, List, Optional
from tael_tools.base import BaseTool, ToolResult
from tael_tools.security import PathSandbox, SecurityError


class ReadFileTool(BaseTool):
    """Safely reads the content of a file within the workspace."""

    def __init__(self, sandbox: PathSandbox):
        self.sandbox = sandbox

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return (
            "Reads file content from the workspace. Supports optional line slice pagination "
            "with start_line and line_count."
        )

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path of the file to read."
                },
                "start_line": {
                    "type": "integer",
                    "description": "Optional 1-based start line index.",
                    "default": 1
                },
                "line_count": {
                    "type": "integer",
                    "description": "Optional maximum number of lines to return.",
                    "default": 500
                }
            },
            "required": ["path"]
        }

    def execute(self, path: str = "", start_line: int = 1, line_count: int = 500, **kwargs) -> ToolResult:
        try:
            full_path = self.sandbox.resolve_safe_path(path)
            if not os.path.exists(full_path):
                return ToolResult(self.name, False, f"File not found: '{path}'")
            if os.path.isdir(full_path):
                return ToolResult(self.name, False, f"Path is a directory, not a file: '{path}'. Use list_dir.")

            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            total_lines = len(lines)
            start_idx = max(0, start_line - 1)
            end_idx = min(total_lines, start_idx + max(1, line_count))
            selected_lines = lines[start_idx:end_idx]

            formatted = "".join(selected_lines)
            header = f"[File: '{path}' | Lines {start_idx + 1}-{end_idx} of {total_lines}]\n"
            return ToolResult(
                tool_name=self.name,
                success=True,
                output=header + formatted,
                metadata={"total_lines": total_lines, "returned_lines": len(selected_lines)}
            )
        except SecurityError as se:
            return ToolResult(self.name, False, f"Security Violation: {se}")
        except Exception as e:
            return ToolResult(self.name, False, f"Error reading file '{path}': {e}")


class WriteFileTool(BaseTool):
    """Safely creates or modifies files within the workspace."""

    def __init__(self, sandbox: PathSandbox):
        self.sandbox = sandbox

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return "Writes content to a file in the workspace. Automatically creates parent directories."

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path of the file to create or overwrite."
                },
                "content": {
                    "type": "string",
                    "description": "The complete text content to write."
                },
                "append": {
                    "type": "boolean",
                    "description": "If true, appends content to the existing file instead of overwriting.",
                    "default": False
                }
            },
            "required": ["path", "content"]
        }

    def execute(self, path: str = "", content: str = "", append: bool = False, **kwargs) -> ToolResult:
        try:
            full_path = self.sandbox.resolve_safe_path(path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            mode = "a" if append else "w"
            with open(full_path, mode, encoding="utf-8") as f:
                f.write(content)

            size_bytes = os.path.getsize(full_path)
            action_desc = "Appended to" if append else "Successfully created"
            return ToolResult(
                tool_name=self.name,
                success=True,
                output=f"{action_desc} '{path}' ({size_bytes} bytes).",
                metadata={"path": path, "size_bytes": size_bytes, "append": append}
            )
        except SecurityError as se:
            return ToolResult(self.name, False, f"Security Violation: {se}")
        except Exception as e:
            return ToolResult(self.name, False, f"Error writing to '{path}': {e}")


class ListDirectoryTool(BaseTool):
    """Safely inspects directory structures within the workspace."""

    def __init__(self, sandbox: PathSandbox):
        self.sandbox = sandbox

    @property
    def name(self) -> str:
        return "list_dir"

    @property
    def description(self) -> str:
        return "Lists files and subdirectories within a specified workspace directory."

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative directory path (default: '.').",
                    "default": "."
                },
                "recursive": {
                    "type": "boolean",
                    "description": "If true, traverses subdirectories recursively.",
                    "default": False
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth when recursive traversal is enabled.",
                    "default": 2
                }
            },
            "required": []
        }

    def execute(self, path: str = ".", recursive: bool = False, max_depth: int = 2, **kwargs) -> ToolResult:
        try:
            full_path = self.sandbox.resolve_safe_path(path)
            if not os.path.exists(full_path):
                return ToolResult(self.name, False, f"Directory does not exist: '{path}'")
            if not os.path.isdir(full_path):
                return ToolResult(self.name, False, f"Path is a file, not a directory: '{path}'. Use read_file.")

            ignored_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode"}
            items = []

            if not recursive:
                for entry in sorted(os.listdir(full_path)):
                    epath = os.path.join(full_path, entry)
                    is_d = os.path.isdir(epath)
                    size = os.path.getsize(epath) if not is_d else "-"
                    tag = "[DIR]" if is_d else "[FILE]"
                    items.append(f"{tag:<6} {entry} ({size} bytes)" if not is_d else f"{tag:<6} {entry}/")
            else:
                base_depth = full_path.rstrip(os.sep).count(os.sep)
                for root, dirs, files in os.walk(full_path):
                    # Filter ignored directories in-place
                    dirs[:] = [d for d in dirs if d not in ignored_dirs]
                    current_depth = root.count(os.sep) - base_depth
                    if current_depth > max_depth:
                        continue
                    rel_dir = os.path.relpath(root, full_path)
                    for f in sorted(files):
                        p = os.path.join(rel_dir, f) if rel_dir != "." else f
                        sz = os.path.getsize(os.path.join(root, f))
                        items.append(f"[FILE] {p} ({sz} bytes)")
                    for d in sorted(dirs):
                        p = os.path.join(rel_dir, d) if rel_dir != "." else d
                        items.append(f"[DIR]  {p}/")

            res_text = f"Directory listing for '{path}':\n" + ("\n".join(items) if items else "(empty directory)")
            return ToolResult(
                tool_name=self.name,
                success=True,
                output=res_text,
                metadata={"item_count": len(items)}
            )
        except SecurityError as se:
            return ToolResult(self.name, False, f"Security Violation: {se}")
        except Exception as e:
            return ToolResult(self.name, False, f"Error listing directory '{path}': {e}")


class SearchTextTool(BaseTool):
    """Safely searches text and patterns across files in the workspace."""

    def __init__(self, sandbox: PathSandbox):
        self.sandbox = sandbox

    @property
    def name(self) -> str:
        return "search_text"

    @property
    def description(self) -> str:
        return "Searches for a text pattern or regex query across files in the workspace."

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text substring or regex pattern to search for."
                },
                "path": {
                    "type": "string",
                    "description": "Relative directory or file to search within (default: '.').",
                    "default": "."
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Optional file glob pattern to match (e.g. '*.py', '*.json').",
                    "default": "*"
                },
                "is_regex": {
                    "type": "boolean",
                    "description": "Whether query should be treated as a regular expression.",
                    "default": False
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of matching lines to return.",
                    "default": 30
                }
            },
            "required": ["query"]
        }

    def execute(
        self,
        query: str = "",
        path: str = ".",
        file_pattern: str = "*",
        is_regex: bool = False,
        max_results: int = 30,
        **kwargs
    ) -> ToolResult:
        if not query:
            return ToolResult(self.name, False, "Parameter 'query' cannot be empty.")

        try:
            warning_note = ""
            if not path or path.strip() in (".", ""):
                full_path = self.sandbox.workspace
            else:
                try:
                    candidate = self.sandbox.resolve_safe_path(path)
                    if os.path.exists(candidate):
                        full_path = candidate
                    else:
                        full_path = self.sandbox.workspace
                        warning_note = f"[Note: Specified path '{path}' does not exist; searching workspace root '.' instead]\n"
                except SecurityError as se:
                    return ToolResult(self.name, False, f"Security Violation: {se}")

            flags = re.IGNORECASE
            pattern = re.compile(query if is_regex else re.escape(query), flags)

            matches = []
            ignored_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", "bin"}

            files_to_search = []
            if os.path.isfile(full_path):
                files_to_search.append(full_path)
            else:
                for root, dirs, files in os.walk(full_path):
                    dirs[:] = [d for d in dirs if d not in ignored_dirs]
                    for f in files:
                        if fnmatch.fnmatch(f, file_pattern):
                            files_to_search.append(os.path.join(root, f))

            for fpath in files_to_search:
                if len(matches) >= max_results:
                    break
                rel_f = os.path.relpath(fpath, self.sandbox.workspace)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, 1):
                            if pattern.search(line):
                                matches.append(f"{rel_f}:{line_no}: {line.strip()}")
                                if len(matches) >= max_results:
                                    break
                except Exception:
                    continue

            output = (
                f"Found {len(matches)} match(es) for '{query}':\n" + "\n".join(matches)
                if matches else f"No matches found for '{query}' in '{path}'."
            )
            return ToolResult(
                tool_name=self.name,
                success=True,
                output=output,
                metadata={"matches_found": len(matches)}
            )
        except SecurityError as se:
            return ToolResult(self.name, False, f"Security Violation: {se}")
        except Exception as e:
            return ToolResult(self.name, False, f"Error searching text: {e}")
