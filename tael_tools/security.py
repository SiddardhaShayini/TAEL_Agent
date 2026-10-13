# -*- coding: utf-8 -*-
"""
TAEL Tool System - Sandboxing & Security Engine
-----------------------------------------------
Enforces strict filesystem and command execution sandboxing:
  - Path traversal protection (workspace confinement)
  - Dangerous command filtering & blacklisting
  - Non-interactive execution timeouts
  - Output buffer caps
"""

import os
import re
from typing import Tuple, List, Optional


class SecurityError(Exception):
    """Raised when an operation violates sandbox boundaries or safety policies."""
    pass


class PathSandbox:
    """Confines all filesystem operations strictly within the designated workspace."""

    def __init__(self, workspace: str):
        self.workspace = os.path.abspath(workspace)
        if not os.path.isdir(self.workspace):
            os.makedirs(self.workspace, exist_ok=True)

    def resolve_safe_path(self, rel_path: str) -> str:
        """
        Resolves a user-supplied relative path to an absolute path.
        Raises SecurityError if the path attempts to escape the workspace.
        """
        if not rel_path or not str(rel_path).strip():
            raise SecurityError("Path cannot be empty.")

        clean_path = str(rel_path).strip().lstrip("/\\")
        full_path = os.path.abspath(os.path.join(self.workspace, clean_path))

        # Commonpath check guarantees full_path is inside self.workspace
        try:
            common = os.path.commonpath([self.workspace, full_path])
        except ValueError:
            # Different drive letters on Windows (e.g. C: vs D:)
            raise SecurityError(f"Access denied: Path '{rel_path}' is on a different drive than workspace.")

        if common != self.workspace:
            raise SecurityError(
                f"Sandbox Violation: Path '{rel_path}' escapes workspace boundary '{self.workspace}'."
            )

        return full_path


class CommandSandbox:
    """
    Guards command execution against dangerous, destructive, or unrestricted operations.
    Blocks privilege escalation, disk format, recursive system deletions, and obfuscated shells.
    """

    # Blacklisted dangerous regex patterns
    DANGEROUS_PATTERNS = [
        # Recursive system wipe / root deletion
        re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?\s+([/\\]|\.\./|[a-zA-Z]:[/\\])", re.IGNORECASE),
        re.compile(r"\brmdir\s+/[sS]\s+([/\\]|[a-zA-Z]:[/\\])", re.IGNORECASE),
        re.compile(r"\bdel\s+(/[fF]?[sS]?[qQ]?\s+)*([a-zA-Z]:[/\\]|[/\\])", re.IGNORECASE),
        # Disk formatting / partitioning
        re.compile(r"\b(format|mkfs|diskpart|fdisk)\b", re.IGNORECASE),
        # System shutdown & reboot
        re.compile(r"\b(shutdown|reboot|halt|poweroff|init\s+0)\b", re.IGNORECASE),
        # Unrestricted piped remote execution (curl | sh, wget | bash)
        re.compile(r"\b(curl|wget)\b.*\|\s*(sh|bash|zsh|powershell|cmd)\b", re.IGNORECASE),
        # Obfuscated PowerShell / encoded scripts
        re.compile(r"\b(powershell|pwsh)\b.*-(enc|encodedcommand)\b", re.IGNORECASE),
        re.compile(r"\b(iex|Invoke-Expression)\b", re.IGNORECASE),
        # Windows Registry modification / tampering
        re.compile(r"\breg\s+(delete|add)\b", re.IGNORECASE),
        # Privilege escalation / user accounts
        re.compile(r"\b(net\s+user|takeown|icacls\s+.*grant)\b", re.IGNORECASE),
        re.compile(r"\b(sudo|su)\s+", re.IGNORECASE),
        # Fork bomb
        re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:", re.IGNORECASE),
    ]

    MAX_COMMAND_TIMEOUT = 30  # Max runtime seconds
    MAX_OUTPUT_CHARS = 25000  # Cap output buffer to prevent output-bomb crashes

    @classmethod
    def validate_command(cls, command: str) -> None:
        """
        Inspects command string against dangerous patterns.
        Raises SecurityError if dangerous patterns are detected.
        """
        cmd_strip = command.strip()
        if not cmd_strip:
            raise SecurityError("Command string cannot be empty.")

        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(cmd_strip):
                raise SecurityError(
                    f"Sandbox Violation: Command '{cmd_strip}' was blocked by safety policy "
                    f"(matches forbidden pattern '{pattern.pattern}')."
                )
