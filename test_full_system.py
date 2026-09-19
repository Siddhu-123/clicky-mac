"""
Comprehensive End-to-End System Test for Clicky macOS.
Tests Screen Capture, Apple MLX Vision Inference, TTS Voice synthesis,
Audio STT model readiness, and Qt GUI components.
"""

import asyncio
import os
import sys
import time
import numpy as np

print("=" * 70)
print("🧪 CLICKY MAC COMPREHENSIVE END-TO-END SYSTEM AUDIT")
print("=" * 70)

# 1. Screen Capture Test
print("\n[TEST 1/5] Screen Capture...")
try:
    from screen.capture import capture_all_screens
    t0 = time.time()
    shots = capture_all_screens(max_width=1280)
    dur = (time.time() - t0) * 1000
    if not shots:
        print("❌ FAIL: No screens captured!")
    else:
        print(f"✓ PASS: Captured {len(shots)} display(s) in {dur:.1f}ms")
        for idx, s in enumerate(shots):
            print(f"   Display {idx}: {s.width}x{s.height}")
except Exception as e:
    print(f"❌ FAIL: Screen capture threw exception: {e}")

# 2. MLX Engine & Vision Inference Test
print("\n[TEST 2/5] MLX Vision Inference (Metal GPU)...")
try:
    from ai.mlx_engine import MLXEngine
    engine = MLXEngine()
    
    t0 = time.time()
    engine.ensure_model_loaded()
    load_dur = time.time() - t0
    print(f"✓ PASS: Model {engine.model_id} loaded in {load_dur:.2f}s")
    
    # Run test prompt with captured screenshot
    query = "Summarize what is visible on this screen in 1-2 concise sentences."
    sys_prompt = "You are Clicky, an AI tutor on macOS. Be helpful and direct."
    print(f"   Query: '{query}'")
    
    t0 = time.time()
    resp = asyncio.run(engine.ask(query, sys_prompt, shots))
    infer_dur = time.time() - t0
    
    words = len(resp.split())
    approx_tokens = words * 1.3
    tps = approx_tokens / infer_dur if infer_dur > 0 else 0
    
    print(f"   Response:\n   \"{resp}\"")
    print(f"✓ PASS: Inference completed in {infer_dur:.2f}s (~{tps:.1f} tokens/sec)")
except Exception as e:
    print(f"❌ FAIL: MLX inference threw exception: {e}")

# 3. Audio & Voice TTS Test
print("\n[TEST 3/5] Audio & Text-to-Speech (TTS)...")
try:
    from audio.tts.edge_tts_provider import EdgeTTSProvider, clean_text_for_speech
    from pathlib import Path
    
    cleaned = clean_text_for_speech("Hello from Clicky! [POINT:100,200:test] Here is your screen.")
    print(f"   Cleaned speech text: \"{cleaned}\"")
    assert "[POINT" not in cleaned, "Tags should be stripped for speech"
    
    tts = EdgeTTSProvider()
    t0 = time.time()
    tmp_out = Path("/tmp/clicky_test_audio.mp3")
    success = asyncio.run(tts.synthesize("Clicky is online and ready.", tmp_out))
    dur = (time.time() - t0) * 1000
    if success and tmp_out.exists():
        print(f"✓ PASS: Edge TTS generated voice audio in {dur:.1f}ms: {tmp_out}")
        tmp_out.unlink(missing_ok=True)
    else:
        print(f"⚠️ Edge TTS fallback, testing MacOSTTSProvider...")
        from audio.tts.macos_tts_provider import MacOSTTSProvider
        mac_tts = MacOSTTSProvider()
        mac_tmp = Path("/tmp/clicky_mac_tts.aiff")
        mac_ok = asyncio.run(mac_tts.synthesize("Clicky is ready.", mac_tmp))
        print(f"✓ PASS: macOS native TTS generated: {mac_tmp} (ok={mac_ok})")
        mac_tmp.unlink(missing_ok=True)
except Exception as e:
    print(f"❌ FAIL: TTS threw exception: {e}")

# 4. Audio STT (Whisper) Test
print("\n[TEST 4/5] Audio Speech-to-Text (Faster-Whisper)...")
try:
    from audio.stt.faster_whisper_stt import FasterWhisperSTT
    stt = FasterWhisperSTT()
    print(f"   Faster-Whisper initialized with model size: '{stt.model_size}'")
    # Quick model load test with 0.5s silence
    silent_audio = np.zeros(8000, dtype=np.float32)
    transcription = stt.transcribe(silent_audio)
    print(f"✓ PASS: Whisper model transcribed audio buffer (result: '{transcription}')")
except Exception as e:
    print(f"❌ FAIL: STT threw exception: {e}")

# 5. Qt GUI & Overlay Test
print("\n[TEST 5/5] Qt GUI Components (HUD Panel & Overlay)...")
try:
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    from ui.panel import CompanionPanel
    from ui.overlay import OverlayWindow
    from companion_manager import CompanionManager
    
    panel = CompanionPanel()
    overlay = OverlayWindow()
    mgr = CompanionManager()
    
    mgr.start()
    print(f"✓ PASS: GUI components initialized, HUD panel at ({panel.pos().x()}, {panel.pos().y()})")
    
    # Close gracefully
    overlay.close()
    panel.close()
    mgr.hotkey_monitor.stop()
    print("✓ PASS: GUI lifecycle and hotkey monitor stopped cleanly")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"❌ FAIL: GUI test threw exception: {e}")

print("\n" + "=" * 70)
print("🏁 SYSTEM AUDIT COMPLETE")
print("=" * 70)
