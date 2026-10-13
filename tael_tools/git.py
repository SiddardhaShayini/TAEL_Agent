# -*- coding: utf-8 -*-
"""
TAEL Tool System - Sandboxed Git Tools
--------------------------------------
Implements:
  1. Git Status (git_status)
  2. Git Diff   (git_diff)
  3. Git Log    (git_log)
  4. Git Branch (git_branch)
"""

import subprocess
import os
from typing import Dict, Any, Optional
from tael_tools.base import BaseTool, ToolResult
from tael_tools.security import PathSandbox, SecurityError


def _run_git_command(workspace: str, args: list, timeout: int = 15) -> ToolResult:
    """Safely executes a git command within the workspace."""
    cmd = ["git"] + args
    try:
        res = subprocess.run(
            cmd,
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        out = (res.stdout + ("\n" + res.stderr if res.stderr else "")).strip()
        success = (res.returncode == 0)
        return ToolResult(
            tool_name="git",
            success=success,
            output=out if out else "(No output / clean working tree)",
            metadata={"exit_code": res.returncode, "args": args}
        )
    except subprocess.TimeoutExpired:
        return ToolResult("git", False, f"Git command timed out after {timeout} seconds.")
    except FileNotFoundError:
        return ToolResult("git", False, "Git executable not found in system PATH.")
    except Exception as e:
        return ToolResult("git", False, f"Git execution error: {e}")


class GitStatusTool(BaseTool):
    """Retrieves git repository status."""

    def __init__(self, sandbox: PathSandbox):
        self.sandbox = sandbox

    @property
    def name(self) -> str:
        return "git_status"

    @property
    def description(self) -> str:
        return "Shows the current working tree and index status of the git repository."

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "short": {
                    "type": "boolean",
                    "description": "If true, displays output in concise short format (default: False).",
                    "default": False
                }
            },
            "required": []
        }

    def execute(self, short: bool = False, **kwargs) -> ToolResult:
        args = ["status", "-s"] if short else ["status"]
        res = _run_git_command(self.sandbox.workspace, args)
        res.tool_name = self.name
        return res


class GitDiffTool(BaseTool):
    """Shows changes between commits, commit and working tree, or staged changes."""

    def __init__(self, sandbox: PathSandbox):
        self.sandbox = sandbox

    @property
    def name(self) -> str:
        return "git_diff"

    @property
    def description(self) -> str:
        return "Shows unstaged or staged git diff changes for review."

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "staged": {
                    "type": "boolean",
                    "description": "If true, shows changes staged for commit (--cached/--staged).",
                    "default": False
                },
                "path": {
                    "type": "string",
                    "description": "Optional specific file or folder path to inspect."
                }
            },
            "required": []
        }

    def execute(self, staged: bool = False, path: Optional[str] = None, **kwargs) -> ToolResult:
        args = ["diff"]
        if staged:
            args.append("--staged")
        if path:
            try:
                safe_path = self.sandbox.resolve_safe_path(path)
                rel_path = os.path.relpath(safe_path, self.sandbox.workspace)
                args.extend(["--", rel_path])
            except SecurityError as se:
                return ToolResult(self.name, False, f"Security Violation: {se}")

        res = _run_git_command(self.sandbox.workspace, args)
        res.tool_name = self.name
        return res


class GitLogTool(BaseTool):
    """Retrieves commit history logs."""

    def __init__(self, sandbox: PathSandbox):
        self.sandbox = sandbox

    @property
    def name(self) -> str:
        return "git_log"

    @property
    def description(self) -> str:
        return "Shows the recent commit history in oneline format."

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "max_count": {
                    "type": "integer",
                    "description": "Maximum number of recent commits to display (default: 5).",
                    "default": 5
                }
            },
            "required": []
        }

    def execute(self, max_count: int = 5, **kwargs) -> ToolResult:
        count = max(1, min(50, max_count))
        args = ["log", "--oneline", f"-n{count}"]
        res = _run_git_command(self.sandbox.workspace, args)
        res.tool_name = self.name
        return res


class GitBranchTool(BaseTool):
    """Lists repository branches."""

    def __init__(self, sandbox: PathSandbox):
        self.sandbox = sandbox

    @property
    def name(self) -> str:
        return "git_branch"

    @property
    def description(self) -> str:
        return "Lists local and remote git branches."

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "all_branches": {
                    "type": "boolean",
                    "description": "If true, lists both local and remote-tracking branches (-a).",
                    "default": False
                }
            },
            "required": []
        }

    def execute(self, all_branches: bool = False, **kwargs) -> ToolResult:
        args = ["branch", "-a"] if all_branches else ["branch"]
        res = _run_git_command(self.sandbox.workspace, args)
        res.tool_name = self.name
        return res
