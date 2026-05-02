"""
mistral_client.py
-----------------
Pipeline: Screenshot → EasyOCR (local) → Mistral text model → clean answer

Optimizations:
  - call preload_ocr_model() at startup so OCR is ready before first capture
  - screenshot is downscaled to 1024px wide before OCR (faster processing)
  - only the answer is returned, no raw OCR dump
"""

import numpy as np
from PIL import Image
from mistralai.client import Mistral

# ── OCR reader (lazy, cached after first load) ────────────────────────────────
_ocr_reader = None

OCR_MAX_WIDTH = 1024        # px – smaller = faster OCR, still readable
TEXT_MODEL    = "mistral-small-latest"


def preload_ocr_model():
    """
    Call this once at app startup (in a background thread) so the EasyOCR
    model is warm and ready before the user presses Capture.
    """
    _get_ocr_reader()


def _get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        import easyocr
        _ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _ocr_reader


def _resize_for_ocr(image: Image.Image) -> Image.Image:
    """Downscale width to OCR_MAX_WIDTH, preserve aspect ratio."""
    w, h = image.size
    if w > OCR_MAX_WIDTH:
        scale = OCR_MAX_WIDTH / w
        image = image.resize((OCR_MAX_WIDTH, int(h * scale)), Image.LANCZOS)
    return image


def analyze_screen(image: Image.Image, api_key: str, prompt: str = None) -> str:
    """
    1. OCR the screenshot locally (fast after model is warm)
    2. Send extracted text to Mistral text model
    3. Return only the answer (no raw OCR dump)
    """
    # Step 1 — OCR
    image = _resize_for_ocr(image)
    img_array = np.array(image.convert("RGB"))
    reader = _get_ocr_reader()
    results = reader.readtext(img_array, detail=0, paragraph=True)
    extracted_text = "\n".join(results).strip()

    if not extracted_text:
        return "No readable text found on screen. Make sure there is clear, legible text visible."

    # Step 2 — Ask Mistral (text only, no image)
    client = Mistral(api_key=api_key)

    user_msg = (
        f"Here is text extracted from a screenshot via OCR:\n\n"
        f"---\n{extracted_text}\n---\n\n"
        f"If there is a question in this text, answer it directly and concisely. "
        f"Do NOT repeat the question or explain what you are doing — just give the answer."
    )

    if prompt:
        user_msg += f"\n\nAdditional instruction: {prompt}"

    response = client.chat.complete(
        model=TEXT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a concise assistant. When given OCR text from a screenshot, "
                    "find any question and answer it directly. "
                    "Never repeat the question. Never add filler phrases like 'Sure!' or 'Of course!'. "
                    "Just the answer."
                ),
            },
            {"role": "user", "content": user_msg},
        ],
    )

    return response.choices[0].message.content.strip()
