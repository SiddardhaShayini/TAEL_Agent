# -*- coding: utf-8 -*-
"""
TAEL Tool System - Base Definitions
-----------------------------------
Abstract Base Class and Result Types for all sandboxed tools.
Every tool must expose:
  - name
  - description
  - parameter_schema
  - execute()
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ToolResult:
    """Standardized result returned by every tool's execute() method."""
    tool_name: str
    success: bool
    output: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_terminal: bool = False  # Set to True for tools that conclude the agent task (e.g. finish)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool": self.tool_name,
            "success": self.success,
            "output": self.output,
            "metadata": self.metadata,
            "is_terminal": self.is_terminal,
        }

    def to_xml_response(self) -> str:
        """Serializes result into standard <tool_response> XML tag."""
        status = "success" if self.success else "error"
        return f'<tool_response tool="{self.tool_name}" status="{status}">\n{self.output}\n</tool_response>'


class BaseTool(ABC):
    """
    Abstract Base Class for all TAEL tools.
    Every tool must define name, description, parameter_schema, and execute().
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier name of the tool (e.g. 'read_file')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Detailed description of the tool and its intended use."""
        pass

    @property
    @abstractmethod
    def parameter_schema(self) -> Dict[str, Any]:
        """
        JSON-Schema compliant parameter definition.
        Format:
        {
            "type": "object",
            "properties": { ... },
            "required": [ ... ]
        }
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Executes the tool with provided arguments and returns a ToolResult.
        Must enforce sandboxing and validation internally.
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        """Returns full metadata dictionary for the tool."""
        return {
            "name": self.name,
            "description": self.description,
            "parameter_schema": self.parameter_schema,
        }
