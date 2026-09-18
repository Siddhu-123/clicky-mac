"""
Quick Benchmark & Inference Test for Qwen2-VL-2B on Apple MLX.
Takes a real screenshot of your Mac display, runs MLX inference on your Metal GPU,
and reports speed (tokens/sec), latency, and response.
"""

import time
from screen.capture import capture_all_screens
from ai.mlx_engine import MLXEngine

print("=" * 60)
print("🔵 Testing Qwen2-VL-2B Inference on Apple Metal GPU (MLX)")
print("=" * 60)

# 1. Capture current display
print("\n[1/3] Capturing Mac screen...")
t0 = time.time()
screens = capture_all_screens(max_width=1280)
capture_time = time.time() - t0
print(f"✓ Screen captured in {capture_time*1000:.1f}ms ({screens[0].width}x{screens[0].height})")

# 2. Load MLX Model
print("\n[2/3] Loading Qwen2-VL-2B-Instruct-4bit into Apple Unified Memory...")
engine = MLXEngine()
t_load = time.time()
engine.ensure_model_loaded()
load_time = time.time() - t_load
print(f"✓ Model loaded into Metal GPU memory in {load_time:.2f}s")

# 3. Run Test Query
prompt = "What applications or windows are visible on this screen? Point out one key button using [POINT:x,y:label]."
sys_prompt = "You are Clicky, an AI tutor on macOS. Look at the screenshot and answer concisely."

print(f"\n[3/3] Running inference on Metal GPU...")
print(f"Prompt: '{prompt}'")
print("-" * 60)

t_start = time.time()
response = ""
token_count = 0

# Run query
import asyncio
response = asyncio.run(engine.ask(prompt, sys_prompt, screenshots=screens))
total_time = time.time() - t_start

print(f"\nResponse:\n{response}")
print("-" * 60)
approx_tokens = len(response.split()) * 1.3
tps = approx_tokens / total_time if total_time > 0 else 0
print(f"✓ Inference completed in {total_time:.2f}s (~{tps:.1f} tokens/sec)")
print("=" * 60)
print("Everything is working! You can now launch the full app with: ./run.sh")
