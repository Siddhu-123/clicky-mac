"""
HeyClicky Max Agent Runtime for macOS.
Executes autonomous multi-step tasks using tool execution and ReAct loop.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import AsyncGenerator, Callable, Dict, List, Optional

from agent.tools import AgentTools
from ai.base_provider import BaseAIProvider
from config import cfg

# Matches key="value" | key='value' | key=plain
_ARG_RE = re.compile(r'([a-zA-Z0-9_]+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,)]*))')

AGENT_SYSTEM_PROMPT = """You are HeyClicky Agent, an autonomous macOS assistant.
You can execute tasks by thinking step-by-step and invoking available tools.

Available tools:
1. bash_run(command="...") - Runs a shell command in macOS zsh.
2. file_read(file_path="...") - Reads contents of a file.
3. file_write(file_path="...", content="...") - Writes contents to a file.
4. file_list(directory="...") - Lists files in a directory.
5. web_search(query="...") - Searches the web via DuckDuckGo.
6. fetch_page(url="...") - Fetches readable text from a webpage.
7. run_applescript(script="...") - Executes macOS AppleScript (e.g. tell application "Finder" to ...).
8. mac_click(x=100, y=200) - Clicks at screen coordinates.
9. mac_type(text="...") - Types text into the active window.

To use a tool, respond strictly in this format:
Thought: Explain what you need to do next.
Action: tool_name(arg1="value", arg2="value")

When you have completed the task or have the final response, respond with:
Thought: I have finished the task.
Final Answer: [Your complete summary and answer to the user]

Do not make assumptions about files or facts without checking them first. Be concise and proactive.
"""


class AgentRuntime:
    def __init__(
        self,
        provider: BaseAIProvider,
        on_progress: Optional[Callable[[str], None]] = None,
    ):
        self.provider = provider
        self.on_progress = on_progress or (lambda msg: None)
        self.max_steps = 10

    def _parse_action(self, text: str) -> Optional[tuple[str, dict]]:
        """Parses `Action: tool_name(key="value", ...)` from LLM output.

        Uses a quote-aware, bracket-balanced scan so arguments containing
        parentheses or quotes are not truncated.
        """
        match = re.search(r"Action:\s*([a-zA-Z0-9_]+)\s*\(", text)
        if not match:
            return None

        tool_name = match.group(1)
        raw_args = []

        # Find the matching closing paren, respecting nested parens and quotes.
        i = match.end()  # position right after the opening '('
        depth = 1
        in_str: Optional[str] = None
        escape = False
        n = len(text)
        while i < n and depth > 0:
            ch = text[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == in_str:
                    in_str = None
            else:
                if ch in ("'", '"'):
                    in_str = ch
                elif ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
            if depth > 0:
                raw_args.append(ch)
            i += 1

        kwargs = {}
        for m in _ARG_RE.finditer("".join(raw_args)):
            k = m.group(1)
            v = m.group(2) if m.group(2) is not None else (m.group(3) if m.group(3) is not None else m.group(4))
            kwargs[k] = v.strip() if isinstance(v, str) else v

        return tool_name, kwargs

    async def _execute_tool(self, tool_name: str, kwargs: dict) -> str:
        """Dispatches tool call to AgentTools."""
        try:
            if tool_name == "bash_run":
                cmd = kwargs.get("command", "")
                return AgentTools.bash_run(cmd)
            elif tool_name == "file_read":
                path = kwargs.get("file_path", "")
                return AgentTools.file_read(path)
            elif tool_name == "file_write":
                path = kwargs.get("file_path", "")
                content = kwargs.get("content", "")
                return AgentTools.file_write(path, content)
            elif tool_name == "file_list":
                directory = kwargs.get("directory", None)
                return AgentTools.file_list(directory)
            elif tool_name == "web_search":
                q = kwargs.get("query", "")
                return await AgentTools.web_search(q)
            elif tool_name == "fetch_page":
                url = kwargs.get("url", "")
                return await AgentTools.fetch_page(url)
            elif tool_name == "run_applescript":
                script = kwargs.get("script", "")
                return AgentTools.run_applescript(script)
            elif tool_name == "mac_click":
                x = int(kwargs.get("x", 0))
                y = int(kwargs.get("y", 0))
                return AgentTools.mac_click(x, y)
            elif tool_name == "mac_type":
                text = kwargs.get("text", "")
                return AgentTools.mac_type(text)
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            return f"Tool execution failed: {e}"

    async def run(self, objective: str) -> str:
        """Runs autonomous agent loop to solve the user objective."""
        self.on_progress(f"Agent starting task: '{objective}'")

        history: List[Dict[str, str]] = []
        current_prompt = f"Objective: {objective}\nPlease start your reasoning and tool execution."

        for step in range(1, self.max_steps + 1):
            response = await self.provider.ask(
                prompt=current_prompt,
                system_prompt=AGENT_SYSTEM_PROMPT,
                history=history,
            )

            # Check for Final Answer
            if "Final Answer:" in response:
                final_part = response.split("Final Answer:", 1)[1].strip()
                self.on_progress(f"Agent completed task: {final_part[:80]}...")
                return final_part

            # Parse Action
            action_info = self._parse_action(response)
            if not action_info:
                # No action found, return the response as answer
                return response

            tool_name, kwargs = action_info
            self.on_progress(f"Step {step}/{self.max_steps}: {tool_name}({kwargs})")

            # Execute Tool
            obs = await self._execute_tool(tool_name, kwargs)

            # Record in history
            history.append({"role": "user", "content": current_prompt})
            history.append({"role": "assistant", "content": response})

            current_prompt = f"Observation:\n{obs}\n\nWhat is your next Thought and Action or Final Answer?"

        return "Agent reached maximum step limit before finishing."
