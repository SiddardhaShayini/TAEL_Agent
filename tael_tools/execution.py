# -*- coding: utf-8 -*-
"""
TAEL Tool System - Sandboxed Execution Tools
--------------------------------------------
Implements:
  1. Execute Python (execute_python)
  2. Execute Terminal Command (execute_terminal_command)
  3. Finish Task (finish)
"""

import sys
import subprocess
import os
import tempfile
from typing import Dict, Any, Optional
from tael_tools.base import BaseTool, ToolResult
from tael_tools.security import PathSandbox, CommandSandbox, SecurityError


class ExecutePythonTool(BaseTool):
    """Safely executes Python scripts in an isolated subprocess within the workspace."""

    def __init__(self, sandbox: PathSandbox):
        self.sandbox = sandbox

    @property
    def name(self) -> str:
        return "execute_python"

    @property
    def description(self) -> str:
        return (
            "Executes a Python code snippet in an isolated subprocess within the workspace "
            "and captures stdout, stderr, and execution status."
        )

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python source code string to execute."
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds (default: 15, max: 30).",
                    "default": 15
                }
            },
            "required": ["code"]
        }

    def execute(self, code: str = "", timeout: int = 15, **kwargs) -> ToolResult:
        if not code or not code.strip():
            return ToolResult(self.name, False, "Code parameter cannot be empty.")

        timeout_sec = max(1, min(CommandSandbox.MAX_COMMAND_TIMEOUT, timeout))

        # Write code to a temporary file inside the workspace
        tmp_file = None
        try:
            tmp_fd, tmp_file = tempfile.mkstemp(suffix=".py", prefix="_tael_eval_", dir=self.sandbox.workspace)
            os.close(tmp_fd)
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(code)

            res = subprocess.run(
                [sys.executable, tmp_file],
                cwd=self.sandbox.workspace,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )

            stdout = res.stdout[:CommandSandbox.MAX_OUTPUT_CHARS]
            stderr = res.stderr[:CommandSandbox.MAX_OUTPUT_CHARS]

            output_lines = [f"Exit Code: {res.returncode}"]
            if stdout:
                output_lines.append(f"Stdout:\n{stdout}")
            if stderr:
                output_lines.append(f"Stderr:\n{stderr}")
            if not stdout and not stderr:
                output_lines.append("(No output produced)")

            return ToolResult(
                tool_name=self.name,
                success=(res.returncode == 0),
                output="\n".join(output_lines),
                metadata={"exit_code": res.returncode}
            )

        except subprocess.TimeoutExpired:
            return ToolResult(self.name, False, f"Execution timed out after {timeout_sec} seconds.")
        except Exception as e:
            return ToolResult(self.name, False, f"Failed to execute Python code: {e}")
        finally:
            if tmp_file and os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception:
                    pass


class ExecuteTerminalCommandTool(BaseTool):
    """
    Safely executes non-destructive terminal / shell commands within the workspace.
    Guarded by CommandSandbox safety policies.
    """

    def __init__(self, sandbox: PathSandbox):
        self.sandbox = sandbox

    @property
    def name(self) -> str:
        return "execute_terminal_command"

    @property
    def description(self) -> str:
        return (
            "Executes a sandboxed terminal command strictly inside the workspace. "
            "Dangerous operations (disk formatting, recursive system deletion, privilege escalation) "
            "are blocked by safety policy."
        )

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command line to execute."
                },
                "timeout": {
                    "type": "integer",
                    "description": "Execution timeout in seconds (default: 20, max: 30).",
                    "default": 20
                }
            },
            "required": ["command"]
        }

    def execute(self, command: str = "", timeout: int = 20, **kwargs) -> ToolResult:
        try:
            # 1. Enforce safety validation
            CommandSandbox.validate_command(command)

            timeout_sec = max(1, min(CommandSandbox.MAX_COMMAND_TIMEOUT, timeout))

            # 2. Execute command confined to workspace
            res = subprocess.run(
                command,
                shell=True,
                cwd=self.sandbox.workspace,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
            )

            stdout = res.stdout[:CommandSandbox.MAX_OUTPUT_CHARS]
            stderr = res.stderr[:CommandSandbox.MAX_OUTPUT_CHARS]

            output_lines = [f"Exit Code: {res.returncode}"]
            if stdout:
                output_lines.append(f"Stdout:\n{stdout}")
            if stderr:
                output_lines.append(f"Stderr:\n{stderr}")
            if not stdout and not stderr:
                output_lines.append("(Command produced no output)")

            return ToolResult(
                tool_name=self.name,
                success=(res.returncode == 0),
                output="\n".join(output_lines),
                metadata={"exit_code": res.returncode, "command": command}
            )

        except SecurityError as se:
            return ToolResult(self.name, False, f"Security Violation: {se}")
        except subprocess.TimeoutExpired:
            return ToolResult(self.name, False, f"Command timed out after {timeout} seconds.")
        except Exception as e:
            return ToolResult(self.name, False, f"Execution error: {e}")


class FinishTool(BaseTool):
    """Signals final completion of the agent task."""

    def __init__(self, sandbox: PathSandbox):
        self.sandbox = sandbox

    @property
    def name(self) -> str:
        return "finish"

    @property
    def description(self) -> str:
        return "Concludes the agent task. Call this after verifying that all required files and commands succeeded."

    @property
    def parameter_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Comprehensive summary of the accomplished task and verification."
                }
            },
            "required": ["summary"]
        }

    def execute(self, summary: str = "Task successfully completed.", **kwargs) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            success=True,
            output=summary,
            is_terminal=True
        )
