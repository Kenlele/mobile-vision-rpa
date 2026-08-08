"""
drivers/base_driver.py
Abstract base class (ABC) defining the device driver interface for screen actions and screenshots.
"""

from abc import ABC, abstractmethod
from typing import Tuple
from PIL import Image


class BaseDriver(ABC):
    """Abstract interface for mobile device driver interactions."""

    @abstractmethod
    def tap(self, x: int, y: int) -> bool:
        """Tap at screen coordinates (x, y)."""
        pass

    @abstractmethod
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> bool:
        """Perform swipe gesture from start coordinates to end coordinates."""
        pass

    @abstractmethod
    def type_text(self, text: str) -> bool:
        """Input text string into the currently focused input field."""
        pass

    @abstractmethod
    def screenshot(self) -> Image.Image:
        """Capture device screenshot and return as PIL Image."""
        pass

    @abstractmethod
    def get_screen_size(self) -> Tuple[int, int]:
        """Return device screen resolution as (width, height)."""
        pass
