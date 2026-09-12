# Clicky for macOS 🔵

> **An AI cursor companion, teacher, and autonomous agent for macOS.**  
> Inspired by [HeyClicky](https://www.heyclicky.com) and the Windows port of [Clicky](https://clicky.foo).  
> Delivers the full **HeyClicky Max** experience ($100/month commercial tier: Talk Mode + Autonomous Agent Mode) **100% free** using local and open-tier models.

---

## What It Does

```
┌─────────────────────────────────────────────────────────┐
│  macOS Desktop (VS Code, Safari, Xcode, Premiere, etc.) │
│                                                         │
│          🔵◂ ← Clicky, your blue cursor buddy           │
│          (floats next to your real pointer)             │
│                                                         │
│  ┌───────────────────────────────────┐                  │
│  │ Clicky  [Gemini 2.5 Flash]   Talk │ ← HUD Panel      │
│  │ ● Speaking…                       │                  │
│  │ "The Save button is right here ↗" │                  │
│  │ [Points with pulsing blue ring]   │                  │
│  └───────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

1. **Talk Mode (Free & Unlimited)**:
   - Hold **Control + Option** and talk. Clicky observes your screen, listens to your voice, and answers with natural voice.
   - **Smooth Visual Pointing**: The blue triangle flies along a smooth cubic-bezier arc to target buttons or menus, dwells with a pulsing highlight ring, and returns to your cursor.
   - **Whiteboard Annotations**: Draws animated arrows (`[ARROW]`), pulsing circles (`[CIRCLE]`), and labels (`[LABEL]`) directly on your display.
   - **Two-Stage Grid Locator**: Pinpoints exact pixels on any screen resolution without needing specialized vision weights.
   - Press **Escape** at any time to instantly stop speech or dismiss annotations.

2. **Agent Mode (HeyClicky Max Feature - Free)**:
   - Activate by saying **"HeyClicky agent [task]"** or clicking the **Talk / Agent** button in the HUD panel or menu bar.
   - Executes autonomous multi-step tasks across macOS:
     - Runs safe terminal commands in macOS zsh.
     - Reads, edits, and writes project files.
     - Performs real-time web research via DuckDuckGo.
     - Automates Mac apps via AppleScript and simulated clicks/keystrokes.

3. **100% Free Default Stack**:
   - **Speech-to-Text**: Local `faster-whisper` running on Apple Silicon (0 cost, offline).
   - **Text-to-Speech**: Microsoft Edge Neural TTS with 400+ natural voices (0 cost, zero API keys needed).
   - **Vision & Intelligence**: Ready for Google Gemini (generous free tier), Ollama (100% local offline), OpenAI, or Claude.
   - **Web Search**: Built-in DuckDuckGo scraping (no search API keys required).

---

## Quick Start

### 1. Launch Clicky

Open your terminal in this directory and run:

```bash
./run.sh
```

The script will automatically activate the Python virtual environment and start Clicky.

### 2. macOS System Permissions

On first run, macOS will prompt for permissions (or you can enable them in **System Settings → Privacy & Security**):
- **Accessibility**: Required for the global `Control + Option` shortcut and computer-use automation.
- **Screen Recording**: Required for Clicky to capture your screen when you ask questions.
- **Microphone**: Required for push-to-talk audio capture.

---

## Hotkeys & Controls

| Shortcut / Action | What It Does |
| :--- | :--- |
| **Hold `Control + Option`** | Push-to-talk voice query (releases to process). |
| **Press `Esc`** | Instantly stop speech and clear screen annotations. |
| **Click Menu Bar Icon 🔵** | Open Clicky menu bar controls & provider switcher. |
| **"Talk" / "Agent" Button** | Toggle between conversational tutor and autonomous agent. |

---

## Switching AI Models & Providers

You can switch models and providers on the fly from the **Menu Bar Icon → AI Provider** or via **Settings**:

### 1. Google Gemini (Free Cloud Tier)
- High-speed multimodal screen analysis and reasoning with generous free quota.
- Set your key in Settings or add to `.env`:
  ```bash
  GEMINI_API_KEY=AIzaSy...
  ```

### 2. Ollama (100% Offline & Private)
- Run local vision models on Apple Silicon GPU via Metal:
  ```bash
  ollama run llama3.2-vision
  ```
- No internet connection or API keys required.

### 3. OpenAI / Claude (BYOK)
- OpenAI GPT-4o (`OPENAI_API_KEY=...`)
- Anthropic Claude 3.5 Sonnet (`ANTHROPIC_API_KEY=...`)

---

## Architecture

```
clicky-mac/
├── config.py                 # Configuration & settings management (~/.config/clicky/)
├── hotkey.py                 # macOS global shortcuts via pynput & Quartz
├── tutor.py                  # Active window detection (NSWorkspace) & intent classification
├── companion_manager.py      # Core orchestrator connecting audio, screen, AI, and UI
├── main.py                   # Application entrypoint & macOS permissions preflight
├── run.sh                    # Launcher script
├── screen/
│   └── capture.py            # Multi-monitor Retina-aware screenshot capture
├── ai/
│   ├── base_provider.py      # Abstract multimodal AI provider interface
│   ├── gemini_provider.py    # Google Gemini Flash provider
│   ├── ollama_provider.py    # Local Ollama provider
│   ├── openai_provider.py    # OpenAI provider
│   ├── claude_provider.py    # Anthropic Claude provider
│   ├── universal_locator.py  # Two-stage visual grid locator (12x8 coarse + 6x6 fine)
│   └── web_search.py         # Free DuckDuckGo real-time web search
├── audio/
│   ├── capture.py            # Sounddevice microphone input stream
│   ├── playback.py           # Native macOS afplay audio player with instant cancellation
│   ├── tts/                  # Microsoft Edge Neural TTS + macOS native `say` fallback
│   └── stt/                  # Local faster-whisper on Apple Silicon
├── agent/
│   ├── runtime.py            # HeyClicky Max autonomous execution loop
│   └── tools.py              # Shell execution, file I/O, AppleScript, computer use
└── ui/
    ├── overlay.py            # Transparent canvas: blue buddy triangle, bezier arc, annotations
    ├── panel.py              # Floating HUD window with live transcript & answers
    ├── tray.py               # macOS top menu bar item & controls
    └── settings_dialog.py    # Interactive settings dialog
```

---

## Testing

Run the automated test suite:

```bash
source .venv/bin/activate
python3 -m unittest tests/test_clicky.py
```
