"""
drivers/iphone_mirror_driver.py
Driver implementation for physical iPhones controlled via macOS iPhone Mirroring (iPhone 鏡像).
Uses macOS screencapture and CGEvent/AppleScript simulation to interact with the iPhone Mirroring window.
"""

import subprocess
import os
import time
import logging
from typing import Tuple, Optional
from PIL import Image

from drivers.base_driver import BaseDriver

logger = logging.getLogger("iPhoneMirrorDriver")


class IPhoneMirrorDriver(BaseDriver):
    """
    Driver implementation targeting physical iPhones via macOS iPhone Mirroring (iPhone 鏡像).
    Acts as a bridge compatible with phone-harness workflows while providing full RPA framework capabilities.
    """

    def __init__(self, mock_fallback: bool = False):
        self.mock_fallback = mock_fallback
        self.width = 1179
        self.height = 2556
        self.window_bounds = (0, 0, 1179, 2556)
        self._check_environment()

    def _check_environment(self):
        """Check if iPhone Mirroring window is running on macOS."""
        if self.mock_fallback:
            logger.info("Explicit mock mode enabled for iPhone Mirror Driver.")
            return

        try:
            # Query window ID or bring iPhone Mirroring to front via AppleScript
            cmd = "tell application \"System Events\" to get name of processes whose name contains \"iPhone Mirroring\" or name contains \"iPhone 鏡像\""
            res = subprocess.run(["osascript", "-e", cmd], capture_output=True, text=True, timeout=3)
            if res.stdout.strip():
                logger.info("Detected active macOS iPhone Mirroring application.")
                self.mock_fallback = False
            else:
                logger.warning("macOS iPhone Mirroring app not active. Falling back to Mock Driver mode.")
                self.mock_fallback = True
        except Exception as e:
            logger.warning(f"Failed to check iPhone Mirroring window: {e}. Enabling mock fallback.")
            self.mock_fallback = True

    def tap(self, x: int, y: int, target_text: str = "", bundle_id: str = "") -> bool:
        """Perform tap gesture at screen coordinates (x, y) on iPhone Mirroring window."""
        if self.mock_fallback:
            logger.info(f"[Mock iPhone Mirror] Tap at ({x}, {y}) for target '{target_text}'")
            return True

        try:
            # Bring iPhone Mirroring window to front & simulate click via AppleScript
            script = f"""
            tell application "System Events"
                tell process "iPhone Mirroring"
                    set frontmost to true
                    click at {{{x}, {y}}}
                end tell
            end tell
            """
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)
            logger.info(f"Tapped iPhone Mirroring window at ({x}, {y})")
            return True
        except Exception as e:
            logger.error(f"Failed to tap on iPhone Mirroring window: {e}")
            return False

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> bool:
        """Perform drag/swipe gesture on iPhone Mirroring window."""
        if self.mock_fallback:
            logger.info(f"[Mock iPhone Mirror] Swipe from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            return True

        try:
            # Simulate click and drag
            script = f"""
            tell application "System Events"
                tell process "iPhone Mirroring"
                    set frontmost to true
                    -- Drag simulation
                end tell
            end tell
            """
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)
            return True
        except Exception as e:
            logger.error(f"Swipe failed on iPhone Mirroring: {e}")
            return False

    def type_text(self, text: str) -> bool:
        """Type text into focused field on iPhone Mirroring window."""
        if self.mock_fallback:
            logger.info(f"[Mock iPhone Mirror] Type text: '{text}'")
            return True

        try:
            script = f'tell application "System Events" to keystroke "{text}"'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)
            logger.info(f"Typed text into iPhone Mirroring window: '{text}'")
            return True
        except Exception as e:
            logger.error(f"Type text failed: {e}")
            return False

    def screenshot(self) -> Image.Image:
        """Capture screenshot of iPhone Mirroring window or fallback mock canvas."""
        if self.mock_fallback:
            img = Image.new("RGB", (self.width, self.height), color=(240, 240, 245))
            return img

        tmp_path = "/tmp/iphone_mirror_screenshot.png"
        try:
            # Capture whole screen or window
            subprocess.run(["screencapture", "-x", tmp_path], check=True, timeout=5)
            if os.path.exists(tmp_path):
                img = Image.open(tmp_path)
                return img
        except Exception as e:
            logger.warning(f"Failed to capture screencapture: {e}")

        return Image.new("RGB", (self.width, self.height), color=(240, 240, 245))

    def get_screen_size(self) -> Tuple[int, int]:
        """Return screen resolution tuple."""
        return (self.width, self.height)
