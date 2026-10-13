# -*- coding: utf-8 -*-
"""
TAEL Tool System - Centralized Tool Registry
--------------------------------------------
Manages tool discovery, schema generation, alias resolution, and dispatching.
"""

import json
from typing import Dict, List, Optional, Any
from tael_tools.base import BaseTool, ToolResult
from tael_tools.security import PathSandbox
from tael_tools.filesystem import ReadFileTool, WriteFileTool, ListDirectoryTool, SearchTextTool
from tael_tools.git import GitStatusTool, GitDiffTool, GitLogTool, GitBranchTool
from tael_tools.execution import ExecutePythonTool, ExecuteTerminalCommandTool, FinishTool


class ToolRegistry:
    """Centralized registry for managing, documenting, and executing sandboxed tools."""

    def __init__(self, workspace: str):
        self.workspace = workspace
        self.sandbox = PathSandbox(workspace)
        self._tools: Dict[str, BaseTool] = {}
        self._aliases: Dict[str, str] = {}

    def register(self, tool: BaseTool, aliases: Optional[List[str]] = None):
        """Registers a BaseTool instance with optional aliases."""
        canonical = tool.name.lower().strip()
        self._tools[canonical] = tool
        if aliases:
            for alias in aliases:
                self._aliases[alias.lower().strip()] = canonical

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Resolves tool instance by name or alias."""
        clean = name.lower().strip()
        if clean in self._tools:
            return self._tools[clean]
        if clean in self._aliases:
            return self._tools[self._aliases[clean]]
        return None

    def list_tools(self) -> List[BaseTool]:
        """Returns all registered tool instances."""
        return list(self._tools.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Returns JSON schema definitions for all registered tools."""
        return [tool.get_info() for tool in self._tools.values()]

    def get_system_prompt_definitions(self, tool_names: Optional[List[str]] = None) -> str:
        """Formats tool schemas into a readable system prompt block. If tool_names is provided, only formats those tools."""
        lines = []
        if tool_names is not None:
            tools_to_show = []
            for t_name in tool_names:
                t = self.get_tool(t_name)
                if t and t not in tools_to_show:
                    tools_to_show.append(t)
        else:
            tools_to_show = list(self._tools.values())

        for tool in tools_to_show:
            schema = tool.parameter_schema
            param_props = schema.get("properties", {})
            required_keys = schema.get("required", [])

            lines.append(f"### Tool: `{tool.name}`")
            lines.append(f"Description: {tool.description}")
            if param_props:
                lines.append("Parameters:")
                for param_name, param_meta in param_props.items():
                    req_mark = "(required)" if param_name in required_keys else "(optional)"
                    p_type = param_meta.get("type", "any")
                    p_desc = param_meta.get("description", "")
                    lines.append(f"  - `{param_name}` ({p_type}, {req_mark}): {p_desc}")
            else:
                lines.append("Parameters: None")
            lines.append("")
        return "\n".join(lines)

    def execute(self, name: str, **kwargs) -> ToolResult:
        """Resolves tool by name/alias, validates arguments, and executes securely."""
        tool = self.get_tool(name)
        if not tool:
            available = list(self._tools.keys())
            return ToolResult(
                tool_name=name,
                success=False,
                output=f"Error: Unknown tool '{name}'. Available tools: {available}"
            )

        try:
            return tool.execute(**kwargs)
        except TypeError as te:
            return ToolResult(
                tool_name=tool.name,
                success=False,
                output=f"Invalid arguments for '{tool.name}': {te}. Required schema: {tool.parameter_schema}"
            )
        except Exception as e:
            return ToolResult(
                tool_name=tool.name,
                success=False,
                output=f"Execution error in '{tool.name}': {e}"
            )


def create_tael_tool_registry(workspace: str) -> ToolRegistry:
    """
    Factory creating a fully initialized Centralized Tool Registry
    containing all 10 standard tools + Finish tool.
    """
    registry = ToolRegistry(workspace)
    sandbox = registry.sandbox

    # 1. Filesystem Tools
    registry.register(ReadFileTool(sandbox), aliases=["read", "cat", "view_file"])
    registry.register(WriteFileTool(sandbox), aliases=["write", "create_file", "save_file"])
    registry.register(ListDirectoryTool(sandbox), aliases=["list_files", "dir", "ls"])
    registry.register(SearchTextTool(sandbox), aliases=["grep", "search", "find_in_files"])

    # 2. Git Tools
    registry.register(GitStatusTool(sandbox), aliases=["status"])
    registry.register(GitDiffTool(sandbox), aliases=["diff"])
    registry.register(GitLogTool(sandbox), aliases=["log"])
    registry.register(GitBranchTool(sandbox), aliases=["branch", "branches"])

    # 3. Execution Tools
    registry.register(ExecutePythonTool(sandbox), aliases=["python", "eval_python", "run_python"])
    registry.register(ExecuteTerminalCommandTool(sandbox), aliases=["run_command", "bash", "terminal", "shell"])
    registry.register(FinishTool(sandbox), aliases=["task_complete", "complete"])

    return registry
