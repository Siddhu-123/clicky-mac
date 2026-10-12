# Clicky for macOS (Apple MLX Edition) 🔵

> **An ultra-fast, local AI cursor companion & autonomous agent for Apple Silicon Macs.**  
> Powered by **Apple MLX** and **Qwen-VL 2B/3B** (4-bit). Runs 100% on-device on your Mac's GPU via Metal.  
> Combines the smooth visual pointing and tutor experience of [Clicky](https://clicky.foo) with the full capabilities of **HeyClicky Max** (Talk Mode + Autonomous Agent Mode) **100% free with zero cloud dependencies**.

---

## Why Apple MLX + Qwen-VL?

- **Zero Memory Copy Overhead**: MLX leverages Apple Silicon's **Unified Memory Architecture**. The CPU and GPU share the exact same memory buffers.
- **Native Metal GPU Acceleration**: Model inference runs directly on Apple Metal GPU kernels (`Device(gpu, 0)`).
- **Featherweight Footprint**: The 4-bit 2B model consumes only **~1.8 GB of RAM**, running at **80–120+ tokens/sec** with sub-second response times.
- **100% Private & Offline**: No cloud APIs, no network latency, no subscriptions, and zero external servers needed.

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
│  │ Clicky  [MLX: Qwen2-VL 2B]   Talk │ ← HUD Panel      │
│  │ ● Speaking…                       │                  │
│  │ "The Save button is right here ↗" │                  │
│  │ [Points with pulsing blue ring]   │                  │
│  └───────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────┘
```

1. **Talk Mode (Tutor & Pointing)**:
   - Hold **`Control + Option`** and speak, or type into the HUD panel and hit `Enter`.
   - Clicky's blue triangle buddy flies along a smooth cubic-bezier arc to target buttons or menus, dwells with a pulsing highlight ring, and returns to your cursor.
   - Whiteboard annotations: draws arrows (`[ARROW]`), pulsing circles (`[CIRCLE]`), and labels (`[LABEL]`) directly over your apps.
   - Press **`Esc`** at any time to instantly cancel speech or dismiss annotations.

2. **Agent Mode (HeyClicky Max Feature)**:
   - Click the **Talk / Agent** button in the HUD panel or say *"HeyClicky agent [task]"*.
   - Executes autonomous multi-step tasks across macOS:
     - Safe terminal commands in macOS `zsh`.
     - Project file reading, editing, and creation.
     - Real-time web research via DuckDuckGo.
     - Mac application automation via AppleScript and simulated clicks/keystrokes.

3. **100% Free & Local Speech Stack**:
   - **STT**: On-device `faster-whisper` running with Apple Silicon NEON acceleration.
   - **TTS**: High-fidelity Microsoft Edge Neural TTS (400+ voices, 0 keys needed) with macOS native `say` fallback.

---

## Quick Start

### 1. Launch Clicky

Requires an Apple Silicon Mac running macOS with Python 3.11+. Clone the repository and run:

```bash
git clone https://github.com/Siddhu-123/clicky-mac.git
cd clicky-mac
./run.sh
```

The first run creates `.venv`, installs `requirements.txt` and builds `dist/Clicky.app` so macOS permissions are scoped to the app. Optional settings live in `.env` (copy `.env.example`).

*(On the very first launch, MLX will download the lightweight 4-bit weights from Hugging Face and cache them locally in `~/.cache/huggingface/hub/`.)*

### 2. Permissions (First time only)

When prompted by macOS (or in **System Settings → Privacy & Security**):
- **Accessibility**: Required for the `Control + Option` global shortcut and automated clicks.
- **Screen Recording**: Required for Clicky to capture your screen when you ask questions.
- **Microphone**: Required for push-to-talk voice capture.

---

## Controls

| Action | What It Does |
| :--- | :--- |
| **Hold `Control + Option`** | Push-to-talk voice query (releases to process). |
| **Type in HUD Panel + `Enter`** | Instant text input without speaking. |
| **Press `Esc`** | Instantly stop speech and clear screen annotations. |
| **Click Menu Bar Icon (🔵)** | Toggle HUD, switch modes, or open Settings. |
| **"Talk / Agent" Button** | Switch between tutor conversation and autonomous agent. |

---

## Model Selection

You can choose your MLX model in **Settings (⚙)**:
- **`mlx-community/Qwen2-VL-2B-Instruct-4bit`** *(Default — Fastest, ~1.8 GB RAM)*
- **`mlx-community/Qwen2.5-VL-3B-Instruct-4bit`** *(Higher detail, ~2.5 GB RAM)*
- **`mlx-community/Qwen2.5-VL-7B-Instruct-4bit`** *(Maximum reasoning, ~5.5 GB RAM)*
- **Custom Model**: Any MLX-compatible VLM from HuggingFace or a local folder.

---

## Verification

Run the automated test suite:

```bash
source .venv/bin/activate
python3 -m unittest tests/test_clicky.py
```

---

## Known limitations

- Apple Silicon only: inference runs on MLX / Metal.
- Pointing accuracy depends on the small 2B/3B vision model; the 7B option is more reliable but needs ~5.5 GB of RAM.
- Agent Mode runs shell commands and simulated clicks on your Mac. Review what you ask it to do.
- Screenshots are processed on-device by the local model. In talk mode no screenshot is taken when the frontmost window title looks sensitive (password managers, sign-in or banking pages). This is a keyword match on the title, so it can miss some windows.

## Licence

MIT. See [LICENSE](LICENSE).
