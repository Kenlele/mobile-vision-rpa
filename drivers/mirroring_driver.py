"""
drivers/mirroring_driver.py
macOS iPhone Mirroring driver implementation using CGEvents / osascript and screencapture.
Enables AI agent control of physical iPhone mirrored on macOS Sequoia without jailbreak or Xcode.
"""

import os
import subprocess
import tempfile
import time
import logging
from typing import Tuple, Optional
from PIL import Image
from drivers.base_driver import BaseDriver

logger = logging.getLogger("MirroringDriver")


class MirroringDriver(BaseDriver):
    """Driver implementation controlling physical iPhone via macOS iPhone Mirroring window."""

    def __init__(self, window_name: str = "iPhone Mirroring"):
        self.window_name = window_name
        self.width = 1179
        self.height = 2556
        self._ensure_mirroring_app()

    def _ensure_mirroring_app(self):
        """Bring macOS iPhone Mirroring window to front."""
        try:
            script = f'tell application "{self.window_name}" to activate'
            subprocess.run(["osascript", "-e", script], capture_output=True, timeout=3)
            logger.info(f"Activated macOS '{self.window_name}' application window.")
        except Exception as e:
            logger.warning(f"Could not activate '{self.window_name}': {e}")

    def tap(self, x: int, y: int, target_text: str = "", bundle_id: str = None) -> bool:
        """Simulate HID tap/click at (x, y) coordinates on iPhone Mirroring window."""
        logger.info(f"iPhone Mirroring Driver TAP at ({x}, {y}) [target: '{target_text}']")
        self._ensure_mirroring_app()

        # Send click event using AppleScript system events
        try:
            script = f'''
            tell application "System Events"
                tell process "{self.window_name}"
                    set frontmost to true
                    click at {{{x}, {y}}}
                end tell
            end tell
            '''
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                return True
        except Exception as e:
            logger.warning(f"AppleScript click failed: {e}")

        # Fallback: Osascript basic click event
        try:
            script = f'''
            tell application "{self.window_name}" to activate
            delay 0.1
            tell application "System Events" to click at {{{x}, {y}}}
            '''
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Failed to execute tap on Mirroring window: {e}")
            return False

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> bool:
        """Simulate drag/swipe gesture on iPhone Mirroring window."""
        logger.info(f"iPhone Mirroring Driver SWIPE from ({start_x}, {start_y}) to ({end_x}, {end_y})")
        self._ensure_mirroring_app()

        try:
            script = f'''
            tell application "System Events"
                tell process "{self.window_name}"
                    set frontmost to true
                    action "drag" at {{{start_x}, {start_y}}} to {{{end_x}, {end_y}}}
                end tell
            end tell
            '''
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception as e:
            logger.warning(f"Swipe on Mirroring window failed: {e}")
            return True

    def type_text(self, text: str) -> bool:
        """Send keystrokes to active iPhone Mirroring window."""
        logger.info(f"iPhone Mirroring Driver TYPE TEXT: '{text}'")
        self._ensure_mirroring_app()

        try:
            script = f'''
            tell application "{self.window_name}" to activate
            delay 0.2
            tell application "System Events"
                keystroke "{text}"
            end tell
            '''
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Failed to send keystrokes to Mirroring window: {e}")
            return False

    def screenshot(self) -> Image.Image:
        """Capture screenshot of iPhone Mirroring window via macOS screencapture."""
        self._ensure_mirroring_app()
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name

            # Capture active window screenshot on macOS
            res = subprocess.run(["screencapture", "-l", self._get_window_id(), "-x", tmp_path],
                                 capture_output=True, timeout=5)

            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                img = Image.open(tmp_path).convert("RGB")
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                self.width, self.height = img.size
                return img
        except Exception as e:
            logger.warning(f"Failed to capture Mirroring window screenshot: {e}")

        # Fallback full screen capture if window id query fails
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            subprocess.run(["screencapture", "-x", tmp_path], capture_output=True, timeout=5)
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                img = Image.open(tmp_path).convert("RGB")
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
                self.width, self.height = img.size
                return img
        except Exception as e:
            logger.error(f"Full screencapture error: {e}")

        return Image.new("RGB", (self.width, self.height), color=(245, 247, 250))

    def _get_window_id(self) -> str:
        """Query macOS window ID for iPhone Mirroring app."""
        try:
            script = f'''
            tell application "System Events"
                tell process "{self.window_name}"
                    return id of window 1
                end tell
            end tell
            '''
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=3)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
        return "0"

    def get_screen_size(self) -> Tuple[int, int]:
        """Return screen size tuple."""
        return (self.width, self.height)
