"""
Apple MLX Native Vision Engine for Clicky macOS.
Executes Qwen2-VL / Qwen2.5-VL models directly on Apple Silicon GPU via Metal.
100% Offline, Zero Cloud Dependencies, Ultra-Low Latency.
"""

from __future__ import annotations

import asyncio
import io
import threading
from typing import AsyncGenerator, Dict, List, Optional

import mlx.core as mx
from PIL import Image

try:
    import mlx_vlm
    from mlx_vlm import apply_chat_template, generate, load, stream_generate
    from mlx_vlm.prompt_utils import get_message_json
except ImportError:
    mlx_vlm = None

from ai.base_provider import BaseAIProvider
from config import cfg
from screen.capture import ScreenShot


class MLXEngine(BaseAIProvider):
    """
    Direct in-process Apple Silicon MLX inference engine for Vision-Language models.
    """

    def __init__(self, model_id: Optional[str] = None):
        self.model_id = model_id or cfg.mlx_model
        self.model = None
        self.processor = None
        self.config = None
        self._load_lock = threading.Lock()
        self._is_loading = False

    @property
    def provider_name(self) -> str:
        return "mlx"

    def is_loaded(self) -> bool:
        return self.model is not None and self.processor is not None

    def ensure_model_loaded(self, on_progress=None):
        """Loads model into Apple Silicon Unified Memory if not already resident."""
        if self.is_loaded() and self.model_id == cfg.mlx_model:
            return

        with self._load_lock:
            if self.is_loaded() and self.model_id == cfg.mlx_model:
                return

            self.model_id = cfg.mlx_model
            if on_progress:
                on_progress(f"Loading MLX model: {self.model_id}...")

            print(f"\n⏳ [MLXEngine] Loading model into Apple Unified Memory: {self.model_id}")
            print("   (If this is your first run, Hugging Face will download ~1.5 GB of 4-bit weights)")
            self.model, self.processor = load(self.model_id)
            self.config = self.model.config
            print(f"✓ [MLXEngine] Model {self.model_id} is loaded onto Apple Metal GPU and ready!\n")

    def _build_prompt_and_image(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> tuple[str, Optional[Image.Image]]:
        messages = []

        # System instructions
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Multi-turn history
        if history:
            for turn in history:
                messages.append({"role": turn["role"], "content": turn["content"]})

        # Image input
        pil_img = None
        has_image = False
        if screenshots and len(screenshots) > 0:
            sc = screenshots[0]
            if sc.pil_image is not None:
                pil_img = sc.pil_image
            elif sc.base64_jpeg:
                import base64
                data = base64.b64decode(sc.base64_jpeg)
                pil_img = Image.open(io.BytesIO(data)).convert("RGB")
            has_image = pil_img is not None

        # User message
        model_type = getattr(self.config, "model_type", "qwen2_vl")
        if has_image:
            user_msg = get_message_json(model_type, prompt, role="user", num_images=1)
        else:
            user_msg = {"role": "user", "content": prompt}

        messages.append(user_msg)

        # Apply model's official chat template (Qwen-VL format)
        formatted_prompt = apply_chat_template(
            self.processor,
            self.config,
            messages,
            num_images=1 if has_image else 0,
            add_generation_prompt=True,
        )

        return formatted_prompt, pil_img

    async def ask(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        if mlx_vlm is None:
            return "MLX is not installed. Run `pip install mlx mlx-vlm`."

        def _run_inference():
            self.ensure_model_loaded()
            formatted_prompt, pil_img = self._build_prompt_and_image(
                prompt, system_prompt, screenshots, history
            )

            # Generate via MLX on Apple Metal GPU
            res = generate(
                self.model,
                self.processor,
                prompt=formatted_prompt,
                image=pil_img,
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature,
                verbose=False,
            )

            # Keep Unified Memory cache tidy
            mx.metal.clear_cache()
            return res.text.strip()

        return await asyncio.to_thread(_run_inference)

    async def ask_stream(
        self,
        prompt: str,
        system_prompt: str,
        screenshots: Optional[List[ScreenShot]] = None,
        history: Optional[List[Dict[str, str]]] = None,
    ) -> AsyncGenerator[str, None]:
        if mlx_vlm is None:
            yield "MLX is not installed. Run `pip install mlx mlx-vlm`."
            return

        # Prepare in thread
        def _prep():
            self.ensure_model_loaded()
            return self._build_prompt_and_image(
                prompt, system_prompt, screenshots, history
            )

        formatted_prompt, pil_img = await asyncio.to_thread(_prep)

        # Run stream generator
        def _get_stream():
            return stream_generate(
                self.model,
                self.processor,
                prompt=formatted_prompt,
                image=pil_img,
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature,
            )

        # Iterate tokens asynchronously
        stream_iter = await asyncio.to_thread(_get_stream)

        loop = asyncio.get_event_loop()
        while True:
            def _next_token():
                try:
                    chunk = next(stream_iter)
                    return chunk.text, False
                except StopIteration:
                    return "", True

            text_piece, is_done = await loop.run_in_executor(None, _next_token)
            if is_done:
                break
            if text_piece:
                yield text_piece

        mx.metal.clear_cache()
