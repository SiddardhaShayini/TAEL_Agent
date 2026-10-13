#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAEL Agent Runtime Core
-----------------------
A fully autonomous tool-using AI agent runtime harness for TAEL (Granite 2B).
Powered by the centralized, sandboxed TAEL Tool System (tael_tools).

Architecture:
  User -> Model (Streaming) -> Detect <tool_call> -> Execute Tool
       -> Wrap in <tool_response> -> Send back to Model -> Repeat until complete.
"""

import os
import sys
import json
import re
import time
from typing import Callable, Any, Dict, List, Tuple, Optional
from dataclasses import dataclass

# Reconfigure stdout/stderr to UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Import the centralized TAEL Tool System
from tael_tools import (
    create_tael_tool_registry,
    ToolRegistry,
    ToolResult,
    BaseTool,
    SecurityError,
)
from tael_router import (
    DynamicTaskRouter,
    TaskCategory,
    RouteDecision,
    route_task,
)
from tael_memory import (
    MemoryManager,
    create_memory_manager,
    ContextBudget,
)

try:
    from llama_cpp import Llama
except ImportError:
    Llama = None

# Default paths
DEFAULT_MODEL_PATH = r"d:\TAEL_V2_Adaptive_AI\Granite-Final-Agent-GGUF\granite-3.1-2b-instruct.Q4_K_M.gguf"
DEFAULT_WORKSPACE = r"d:\TAEL_V2_Adaptive_AI"


# ==============================================================================
# 1. Tool Call Representation
# ==============================================================================

@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]
    raw_text: str = ""


# ==============================================================================
# 2. XML Tool Parser (Robust & Fault-Tolerant)
# ==============================================================================

class XMLToolParser:
    """
    Parses <tool_call>...</tool_call> tags from model output.
    Recovers from malformed XML, unclosed tags, markdown backticks, and varied JSON keys.
    """

    # Matches <tool_call>...</tool_call> or unclosed <tool_call>... at end of text
    TAG_REGEX = re.compile(r"<tool_call>\s*(.*?)(?:</tool_call>|$)", re.DOTALL | re.IGNORECASE)

    # Sub-tag based XML: <tool_call><name>X</name><parameters>...</parameters></tool_call>
    XML_SUBTAG_NAME = re.compile(r"<(?:name|tool)>\s*(.*?)\s*</(?:name|tool)>", re.DOTALL | re.IGNORECASE)

    @classmethod
    def parse(cls, text: str) -> List[ToolCall]:
        calls: List[ToolCall] = []

        # 1. Primary: Extract content between <tool_call>...</tool_call>
        matches = cls.TAG_REGEX.findall(text)
        for block in matches:
            block = block.strip()
            if not block:
                continue

            tc = cls._parse_single_block(block)
            if tc:
                calls.append(tc)

        # 2. Fallback: If no <tool_call> tags, check for markdown ```json ... ``` blocks with tool signatures
        if not calls:
            json_blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            for jb in json_blocks:
                tc = cls._parse_json_dict(jb.strip())
                if tc:
                    calls.append(tc)

        return calls

    @classmethod
    def _parse_single_block(cls, raw: str) -> Optional[ToolCall]:
        # Strip code fences if model wrapped json in ```json ... ``` inside <tool_call>
        cleaned = re.sub(r"^```(?:json|xml)?\s*", "", raw)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()

        # Try JSON parsing first (standard format)
        tc = cls._parse_json_dict(cleaned)
        if tc:
            tc.raw_text = raw
            return tc

        # Try tag-based XML parsing fallback: <name>write_file</name><path>...</path>
        name_match = cls.XML_SUBTAG_NAME.search(raw)
        if name_match:
            tool_name = name_match.group(1).strip()
            args = {}
            for tag_match in re.finditer(r"<([a-zA-Z0-9_]+)>\s*(.*?)\s*</\1>", raw, re.DOTALL):
                t_key = tag_match.group(1).lower()
                if t_key not in ("tool_call", "name", "tool"):
                    args[t_key] = tag_match.group(2).strip()
            return ToolCall(name=tool_name, arguments=args, raw_text=raw)

        # Fuzzy recovery: Find "tool": "..." or "name": "..." and extract JSON substring
        json_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if json_match:
            tc = cls._parse_json_dict(json_match.group(0))
            if tc:
                tc.raw_text = raw
                return tc

        return None

    @classmethod
    def _parse_json_dict(cls, json_str: str) -> Optional[ToolCall]:
        try:
            data = json.loads(json_str)
            if not isinstance(data, dict):
                return None

            name = (
                data.get("tool")
                or data.get("name")
                or data.get("action")
                or data.get("tool_name")
            )
            # Intelligent inference if tool name is omitted by 2B model
            if not name or not isinstance(name, str):
                if "path" in data and "content" in data:
                    name = "write_file"
                elif "path" in data and ("start_line" in data or len(data) == 1):
                    name = "read_file"
                elif "command" in data:
                    name = "execute_terminal_command"
                elif "query" in data:
                    name = "search_text"
                elif "summary" in data and len(data) == 1:
                    name = "finish"
                else:
                    return None

            arguments = (
                data.get("arguments")
                or data.get("parameters")
                or data.get("args")
            )
            if not isinstance(arguments, dict):
                arguments = {k: v for k, v in data.items() if k not in ("tool", "name", "action", "tool_name")}

            return ToolCall(name=name, arguments=arguments, raw_text=json_str)

        except json.JSONDecodeError:
            # Heuristic repair for unclosed quotes, trailing commas, or missing brackets
            cleaned_base = re.sub(r",\s*\}", "}", json_str)
            for suffix in ["", "}", '"', '"}', '"}}', '}}', ']}', '"]}}']:
                candidate = cleaned_base + suffix
                try:
                    data = json.loads(candidate)
                    if isinstance(data, dict):
                        name = (
                            data.get("tool")
                            or data.get("name")
                            or data.get("action")
                            or data.get("tool_name")
                        )
                        if not name:
                            if "path" in data and "content" in data:
                                name = "write_file"
                            elif "command" in data:
                                name = "execute_terminal_command"
                            elif "query" in data:
                                name = "search_text"
                        if name:
                            args = data.get("arguments") or data.get("parameters") or {
                                k: v for k, v in data.items() if k not in ("tool", "name", "action", "tool_name")
                            }
                            return ToolCall(name=name, arguments=args, raw_text=json_str)
                except Exception:
                    continue
            return None


# ==============================================================================
# 3. Tool Response Parser / Wrapper
# ==============================================================================

class ToolResponseWrapper:
    """Wraps tool execution results in canonical <tool_response> tags."""

    @staticmethod
    def wrap(result: ToolResult) -> str:
        status_attr = "success" if result.success else "error"
        return f'<tool_response tool="{result.tool_name}" status="{status_attr}">\n{result.output}\n</tool_response>'

    @staticmethod
    def wrap_multiple(results: List[ToolResult]) -> str:
        blocks = [ToolResponseWrapper.wrap(r) for r in results]
        return "\n\n".join(blocks)


# ==============================================================================
# 4. Conversation History & Context Manager
# ==============================================================================

class ConversationHistory:
    """Maintains message sequence, manages context window, and prevents token overflow."""

    def __init__(self, system_prompt: str, max_history_turns: int = 12):
        self.system_prompt = system_prompt
        self.max_history_turns = max_history_turns
        self.messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]

    def add_user(self, content: str):
        self.messages.append({"role": "user", "content": content})
        self._prune_if_needed()

    def add_assistant(self, content: str):
        self.messages.append({"role": "assistant", "content": content})
        self._prune_if_needed()

    def add_tool_responses(self, tool_response_text: str):
        """Appends tool response as a user message following the ReAct standard."""
        self.messages.append({"role": "user", "content": tool_response_text})
        self._prune_if_needed()

    def _prune_if_needed(self):
        """Keeps system prompt intact, prunes oldest non-system messages if list grows too large."""
        if len(self.messages) > (self.max_history_turns * 2 + 1):
            keep_prefix = self.messages[:2]
            keep_suffix = self.messages[-(self.max_history_turns * 2):]
            self.messages = keep_prefix + keep_suffix

    def get_messages(self) -> List[Dict[str, str]]:
        return self.messages


# ==============================================================================
# 5. Agent Runtime Core (Loop, Streaming, Retries)
# ==============================================================================

class TaelAgentRuntime:
    """
    Autonomous tool-calling AI agent runtime core.
    Orchestrates: Model Streaming -> XML Detection -> Tool Execution -> Response Wrapping -> Loop.
    """

    def __init__(
        self,
        model_path: str = DEFAULT_MODEL_PATH,
        workspace: str = DEFAULT_WORKSPACE,
        temperature: float = 0.2,
        max_steps: int = 10,
        max_retries: int = 2,
    ):
        self.workspace = os.path.abspath(workspace)
        self.temperature = temperature
        self.max_steps = max_steps
        self.max_retries = max_retries

        # Initialize Centralized Sandboxed Tool Registry
        self.registry = create_tael_tool_registry(self.workspace)

        # Build System Prompt with all 10 registered tools
        tool_specs = self.registry.get_system_prompt_definitions()
        self.system_prompt = (
            "You are TAEL, a specialized autonomous software engineering AI agent.\n"
            "You have direct access to your local workspace to read/write files, run commands, and verify your work.\n"
            "All actions are securely sandboxed inside the workspace.\n\n"
            "Available Tools:\n"
            f"{tool_specs}\n"
            "Tool Calling Protocol:\n"
            "To invoke one or more tools, format each call using <tool_call> tags containing valid JSON:\n"
            "<tool_call>\n"
            '{"tool": "write_file", "path": "app.py", "content": "print(\'hello\')"}\n'
            "</tool_call>\n\n"
            "Rules:\n"
            "1. You can call multiple tools sequentially in a single turn.\n"
            "2. After creating files, execute terminal verification or list files before concluding.\n"
            "3. Once your task is completely finished and verified, invoke the `finish` tool:\n"
            "<tool_call>\n"
            '{"tool": "finish", "summary": "Detailed summary of all actions taken."}\n'
            "</tool_call>\n"
        )

        # Initialize Persistent Memory System
        self.memory_manager = create_memory_manager(self.workspace)

        # Initialize Model
        print("=" * 68)
        print(" [TAEL AGENT RUNTIME CORE] Initializing...")
        print(f" Workspace: {self.workspace}")
        print(f" Model:     {os.path.basename(model_path)}")
        t0 = time.time()
        if Llama is None:
            raise RuntimeError("llama_cpp library not installed. Please install llama-cpp-python.")
        self.llm = Llama(
            model_path=model_path,
            n_ctx=4096,
            n_threads=6,
            verbose=False,
        )
        print(f" Engine:    Loaded GGUF model in {time.time() - t0:.2f}s")
        print(f" Tools:     {len(self.registry.list_tools())} sandboxed tools registered.")
        print(f" Memory:    4-pillar persistent memory active ({self.memory_manager.conversation.session_id})")
        print("=" * 68 + "\n")

    def run_turn_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
    ) -> str:
        """Runs inference with token streaming to the console."""
        temp = self.temperature if temperature is None else temperature
        toks = 1500 if max_tokens is None else max_tokens
        p_val = 0.90 if top_p is None else top_p

        stream = self.llm.create_chat_completion(
            messages=messages,
            temperature=temp,
            max_tokens=toks,
            top_p=p_val,
            stream=True,
        )

        full_content = []
        for chunk in stream:
            delta = chunk["choices"][0].get("delta", {})
            text_piece = delta.get("content", "")
            if text_piece:
                full_content.append(text_piece)
                sys.stdout.write(text_piece)
                sys.stdout.flush()

        print()  # Final newline
        return "".join(full_content)

    def execute_task(
        self,
        user_prompt: str,
        enable_router: bool = True,
    ) -> bool:
        """
        Executes the autonomous agent loop:
          User -> Dynamic Router -> Model -> Detect <tool_call> -> Execute -> Wrap in <tool_response> -> Repeat
        """
        print(f"\n{'='*68}")
        print(f" USER REQUEST: {user_prompt}")
        print(f"{'='*68}\n")

        # 1. Dynamic Task Routing
        if enable_router:
            decision = route_task(user_prompt)
            print(decision.format_summary() + "\n")

            tool_definitions = self.registry.get_system_prompt_definitions(decision.tool_names)
            active_prompt = (
                f"{decision.system_prompt}\n\n"
                f"Workspace Root: {self.workspace}\n\n"
                "Available Tools:\n"
                f"{tool_definitions}\n"
                "Tool Calling Protocol:\n"
                "To invoke one or more tools, format each call using <tool_call> tags containing valid JSON:\n"
                "<tool_call>\n"
                '{"tool": "write_file", "path": "app.py", "content": "..."}\n'
                "</tool_call>\n\n"
                "Rules:\n"
                "1. You can call multiple tools sequentially in a single turn.\n"
                "2. When your task is finished and verified, invoke the `finish` tool:\n"
                "<tool_call>\n"
                '{"tool": "finish", "summary": "Detailed summary."}\n'
                "</tool_call>\n"
            )
            step_temp = decision.generation_params.get("temperature", self.temperature)
            step_top_p = decision.generation_params.get("top_p", 0.90)
            step_max_tokens = decision.generation_params.get("max_tokens", 1500)
        else:
            active_prompt = self.system_prompt
            step_temp = self.temperature
            step_top_p = 0.90
            step_max_tokens = 1500

        # Record user message into persistent memory
        self.memory_manager.record_user_message(user_prompt)

        history = ConversationHistory(active_prompt)
        history.add_user(user_prompt)

        for step in range(1, self.max_steps + 1):
            print(f"\n--- [Agent Step {step}/{self.max_steps}] ---")

            # 1. Prepare message payload with auto-compaction, relevance retrieval, and overflow guard
            messages = self.memory_manager.prepare_messages_for_inference(
                system_prompt=active_prompt,
                user_prompt=user_prompt,
                max_active_turns=6,
            )

            # 2. Generate model response with streaming using dynamically selected parameters
            assistant_text = self.run_turn_stream(
                messages,
                temperature=step_temp,
                max_tokens=step_max_tokens,
                top_p=step_top_p,
            )
            history.add_assistant(assistant_text)

            # 3. Parse tool calls and record assistant turn
            tool_calls = XMLToolParser.parse(assistant_text)
            self.memory_manager.record_assistant_message(
                assistant_text,
                tool_calls=[{"tool": tc.name, "args": tc.arguments} for tc in tool_calls],
            )

            # 4. If no tool calls detected, check if task is finished or guide model
            if not tool_calls:
                print(" [INFO] No tool call detected in model output.")
                if step == 1:
                    reminder = (
                        "Reminder: If you need to inspect or modify files or run commands, output <tool_call> blocks. "
                        "If you have completed the task, invoke the finish tool:\n"
                        '<tool_call>{"tool": "finish", "summary": "..."}</tool_call>'
                    )
                    history.add_user(reminder)
                    self.memory_manager.record_user_message(reminder)
                    continue
                else:
                    print("\n[AGENT COMPLETE] Model concluded without pending tool calls.")
                    return True

            # 5. Execute detected tool calls sequentially
            results: List[ToolResult] = []
            is_terminal = False

            for idx, tc in enumerate(tool_calls, 1):
                print(f"\n [EXEC {idx}/{len(tool_calls)}] Tool: '{tc.name}' | Args: {tc.arguments}")

                # Execute through centralized sandboxed registry with automatic retries
                retries = 0
                res = self.registry.execute(tc.name, **tc.arguments)
                while not res.success and retries < self.max_retries:
                    retries += 1
                    print(f"  [RETRY {retries}/{self.max_retries}] Tool reported error: {res.output}. Retrying...")
                    time.sleep(0.5)
                    res = self.registry.execute(tc.name, **tc.arguments)

                status_label = "SUCCESS" if res.success else "FAILED"
                print(f"  [{status_label}] -> {res.output[:200]}")
                results.append(res)

                # Track file interactions in FileMemory
                if tc.name in ["write_file", "create_file"]:
                    self.memory_manager.record_file_interaction(
                        rel_path=tc.arguments.get("path", ""),
                        action="created" if res.success else "failed",
                        content=tc.arguments.get("content"),
                    )
                elif tc.name == "read_file":
                    self.memory_manager.record_file_interaction(
                        rel_path=tc.arguments.get("path", ""),
                        action="read",
                    )

                # Record tool observation in persistent conversation memory
                self.memory_manager.record_tool_result(tc.name, res.output, success=res.success)

                if res.is_terminal:
                    is_terminal = True
                    break

            # 6. Check if terminal tool (finish) was called
            if is_terminal:
                print(f"\n{'='*68}")
                print(" TASK FINISHED BY AGENT")
                print(f"{'='*68}\n")
                return True

            # 7. Wrap outputs into <tool_response> tags and append to history
            tool_response_text = ToolResponseWrapper.wrap_multiple(results)
            history.add_tool_responses(tool_response_text)

        print("\n [WARNING] Agent reached maximum allowed steps.")
        return False


# ==============================================================================
# 6. CLI Entry Point
# ==============================================================================

def main():
    runtime = TaelAgentRuntime()

    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        runtime.execute_task(task)
    else:
        print("\nTAEL Agent Interactive Shell. Type your task below (or 'exit' to quit):\n")
        while True:
            try:
                user_input = input("\nTAEL> ").strip()
                if not user_input or user_input.lower() in ("exit", "quit", "q"):
                    print("Exiting TAEL Runtime. Goodbye!")
                    break
                runtime.execute_task(user_input)
            except (KeyboardInterrupt, EOFError):
                print("\nInterrupted. Exiting.")
                break


if __name__ == "__main__":
    main()
