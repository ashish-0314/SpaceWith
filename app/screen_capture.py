"""
screen_capture.py
-----------------
Handles screen capture using mss (fast cross-platform screenshot library).

Learning: How to capture the full screen or a specific region using mss + PIL.
"""

import mss
import mss.tools
from PIL import Image





def capture_region(x: int, y: int, width: int, height: int) -> Image.Image:
    """
    Captures a specific region of the screen.

    Args:
        x, y:          Top-left corner of the region (pixels)
        width, height: Dimensions of the region

    Returns:
        PIL Image of the captured region
    """
    with mss.mss() as sct:
        region = {"top": y, "left": x, "width": width, "height": height}
        screenshot = sct.grab(region)
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
