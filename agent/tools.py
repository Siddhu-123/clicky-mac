"""
Tools available to HeyClicky Max Agent Mode on macOS.
Includes shell commands, file manipulation, web browsing, AppleScript, and GUI computer use.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

try:
    import Quartz
except ImportError:
    Quartz = None

from ai.web_search import WebSearcher
from config import cfg


class AgentTools:
    """Tool execution suite for macOS autonomous agent."""

    @classmethod
    def get_workspace_dir(cls) -> Path:
        p = Path(cfg.agent_workspace_dir).expanduser()
        p.mkdir(parents=True, exist_ok=True)
        return p

    @classmethod
    def bash_run(cls, command: str, timeout: int = 45) -> str:
        """Runs a shell command on macOS and returns combined stdout and stderr."""
        cwd = cls.get_workspace_dir()
        try:
            with subprocess.Popen(
                ["/bin/zsh", "-c", command],
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            ) as proc:
                try:
                    out, err = proc.communicate(timeout=timeout)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except Exception:
                        pass
                    return f"Command timed out after {timeout} seconds."
                code = proc.returncode
                output = f"Exit code: {code}\n"
                if out:
                    output += f"Output:\n{out}\n"
                if err:
                    output += f"Error:\n{err}\n"
                return output.strip()
        except Exception as e:
            return f"Error executing command: {e}"

    @classmethod
    def file_read(cls, file_path: str) -> str:
        """Reads content of a file."""
        p = Path(file_path).expanduser()
        if not p.is_absolute():
            p = cls.get_workspace_dir() / p
        try:
            if not p.exists():
                return f"File does not exist: {p}"
            return p.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading file: {e}"

    @classmethod
    def file_write(cls, file_path: str, content: str) -> str:
        """Writes text content to a file."""
        p = Path(file_path).expanduser()
        if not p.is_absolute():
            p = cls.get_workspace_dir() / p
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"Successfully wrote {len(content)} bytes to {p}"
        except Exception as e:
            return f"Error writing file: {e}"

    @classmethod
    def file_list(cls, directory: Optional[str] = None) -> str:
        """Lists files and directories."""
        p = Path(directory).expanduser() if directory else cls.get_workspace_dir()
        if not p.is_absolute():
            p = cls.get_workspace_dir() / p
        try:
            if not p.exists():
                return f"Directory does not exist: {p}"
            items = []
            for item in sorted(p.iterdir()):
                kind = "DIR " if item.is_dir() else "FILE"
                size = item.stat().st_size if item.is_file() else "-"
                items.append(f"{kind:4} {item.name:30} {size}")
            return "\n".join(items) if items else "(Empty directory)"
        except Exception as e:
            return f"Error listing directory: {e}"

    @classmethod
    async def web_search(cls, query: str) -> str:
        """Searches DuckDuckGo and returns summaries with links."""
        return await WebSearcher.format_search_context(query)

    @classmethod
    async def fetch_page(cls, url: str) -> str:
        """Fetches and cleans readable text from a URL."""
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            try:
                async with client.stream("GET", url, headers=headers) as resp:
                    if resp.status_code != 200:
                        return f"HTTP error {resp.status_code}"
                    max_bytes = 2000000
                    body = bytearray()
                    truncated = False
                    async for chunk in resp.aiter_bytes():
                        remaining = max_bytes - len(body)
                        if len(chunk) >= remaining:
                            body.extend(chunk[:remaining])
                            truncated = True
                            break
                        body.extend(chunk)

                    encoding = resp.encoding or "utf-8"
                    try:
                        text = body.decode(encoding, errors="replace")
                    except (LookupError, TypeError):
                        text = body.decode("utf-8", errors="replace")

                    import re
                    # Simple strip tags
                    text = re.sub(r"<(script|style)[^>]*>[\s\S]*?</\1>", "", text, flags=re.I)
                    clean = re.sub(r"<[^>]+>", " ", text)
                    clean = re.sub(r"\s+", " ", clean).strip()

                    result = clean[:4000].rstrip()
                    if truncated:
                        return f"{result}\n[truncated]" if result else "[truncated]"
                    return clean[:4000]
            except Exception as e:
                return f"Error fetching {url}: {e}"

    @classmethod
    def run_applescript(cls, script: str) -> str:
        """Executes native macOS AppleScript to automate applications."""
        try:
            cmd = ["osascript", "-e", script]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if res.returncode == 0:
                return res.stdout.strip() or "AppleScript executed successfully."
            return f"AppleScript error: {res.stderr.strip()}"
        except Exception as e:
            return f"Error running AppleScript: {e}"

    @classmethod
    def mac_click(cls, x: int, y: int) -> str:
        """Simulates a mouse click at logical coordinate (x, y) using Quartz."""
        if Quartz is None:
            return "Quartz is not available for mouse events."
        try:
            point = Quartz.CGPointMake(x, y)
            # Mouse down
            event_down = Quartz.CGEventCreateMouseEvent(
                None, Quartz.kCGEventLeftMouseDown, point, Quartz.kCGMouseButtonLeft
            )
            # Mouse up
            event_up = Quartz.CGEventCreateMouseEvent(
                None, Quartz.kCGEventLeftMouseUp, point, Quartz.kCGMouseButtonLeft
            )
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)
            time.sleep(0.05)
            Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)
            return f"Clicked at ({x}, {y})"
        except Exception as e:
            return f"Error clicking at ({x}, {y}): {e}"

    @classmethod
    def mac_type(cls, text: str) -> str:
        """Types text using Quartz simulated keystrokes."""
        if Quartz is None:
            return "Quartz is not available for keyboard events."
        try:
            for char in text:
                event_down = Quartz.CGEventCreateKeyboardEvent(None, 0, True)
                Quartz.CGEventKeyboardSetUnicodeString(event_down, len(char.encode("utf-16-le")) // 2, char)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_down)

                event_up = Quartz.CGEventCreateKeyboardEvent(None, 0, False)
                Quartz.CGEventKeyboardSetUnicodeString(event_up, len(char.encode("utf-16-le")) // 2, char)
                Quartz.CGEventPost(Quartz.kCGHIDEventTap, event_up)
                time.sleep(0.01)
            return f"Typed: {text}"
        except Exception as e:
            return f"Error typing text: {e}"
