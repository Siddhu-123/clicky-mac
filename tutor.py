"""
Tutor-layer helpers for macOS:
- Active window & application detection (via NSWorkspace and Quartz)
- Privacy masking
- Intent classification (locate, multistep, next, stop, repeat, agent mode)
"""

from __future__ import annotations

import re
from typing import Optional

try:
    import AppKit
    import Quartz
except ImportError:
    AppKit = None
    Quartz = None


def active_window_title() -> str:
    """
    Returns the title of the frontmost window and application on macOS.
    Falls back to localizedName of the active application.
    """
    app_name = ""
    window_title = ""

    if AppKit is not None:
        try:
            workspace = AppKit.NSWorkspace.sharedWorkspace()
            front_app = workspace.frontmostApplication()
            if front_app:
                app_name = front_app.localizedName() or ""
        except Exception:
            pass

    if Quartz is not None:
        try:
            # Look up on-screen windows in frontmost app
            options = Quartz.kCGWindowListOptionOnScreenOnly | Quartz.kCGWindowListExcludeDesktopElements
            window_list = Quartz.CGWindowListCopyWindowInfo(options, Quartz.kCGNullWindowID)
            if window_list:
                for w in window_list:
                    w_owner = w.get(Quartz.kCGWindowOwnerName, "")
                    w_name = w.get(Quartz.kCGWindowName, "")
                    w_layer = w.get(Quartz.kCGWindowLayer, 0)
                    # Layer 0 is normal application windows
                    if w_layer == 0 and w_name and (not app_name or w_owner == app_name):
                        window_title = w_name
                        break
        except Exception:
            pass

    if app_name and window_title:
        return f"{app_name} — {window_title}"
    return app_name or window_title or "macOS Desktop"


def app_key(title: str) -> str:
    """Reduces a noisy window title to a stable per-app key."""
    if not title:
        return "desktop"
    parts = re.split(r"\s[-—–|]\s", title)
    return (parts[0] if parts else title).strip()[:48] or "desktop"


# ── Query Intent Classifiers ──────────────────────────────────────────────────

LOCATE_RE = re.compile(
    r"\b(where\s+(is|do|can|should)|how\s+do\s+i\s+(click|find|open|access|use|get\s+to)|"
    r"point\s+(at|to)|show\s+me\s+(the|where)|click\s+(the|on)|find\s+the|"
    r"locate\s+the|highlight\s+the)\b",
    re.IGNORECASE,
)

MULTISTEP_RE = re.compile(
    r"\b(how\s+(do\s+i|to)\s+(export|install|configure|set\s*up|setup|publish|"
    r"deploy|enable|disable|build|launch|download|upload|record))\b",
    re.IGNORECASE,
)

NEXT_RE = re.compile(
    r"^\s*(next|continue|go\s*on|keep\s*going|what'?s?\s*next)[\s.!?]*$",
    re.IGNORECASE,
)

STOP_RE = re.compile(
    r"^\s*(stop|quit|cancel|never\s*mind|nevermind|pause)[\s.!?]*$",
    re.IGNORECASE,
)

REPEAT_RE = re.compile(
    r"^\s*(repeat|say\s+(it|that)\s*again|say\s+again|once\s+more|"
    r"what\s+(did\s+you|d['’]you)\s+say)[\s.!?]*$",
    re.IGNORECASE,
)

AGENT_RE = re.compile(
    r"\b(hey\s*clicky\s*agent|clicky\s*agent|agent\s*mode|agent\b|"
    r"can\s+you\s+(do|run|create|build|automate|fix|install|write|search\s+and\s+create)|"
    r"please\s+(create|write|automate|build|search\s+for\s+and\s+save))\b",
    re.IGNORECASE,
)


def is_locate(q: str) -> bool:
    return LOCATE_RE.search(q or "") is not None


def is_multistep(q: str) -> bool:
    return MULTISTEP_RE.search(q or "") is not None


def is_next(q: str) -> bool:
    return NEXT_RE.match((q or "").strip()) is not None


def is_stop(q: str) -> bool:
    return STOP_RE.match((q or "").strip()) is not None


def is_repeat(q: str) -> bool:
    return REPEAT_RE.match((q or "").strip()) is not None


def is_agent(q: str) -> bool:
    """Detects if user is invoking HeyClicky Max Agent Mode."""
    return AGENT_RE.search(q or "") is not None


def is_sensitive_window(title: str) -> bool:
    """Detects sensitive windows (e.g. password managers, bank sites) for privacy guard."""
    t = (title or "").lower()
    keywords = [
        "1password", "bitwarden", "keepass", "lastpass", "keychain access",
        "login", "sign in", "signin", "banking", "credit card", ".env", "secrets"
    ]
    return any(k in t for k in keywords)
