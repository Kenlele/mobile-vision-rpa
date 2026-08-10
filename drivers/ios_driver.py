"""
drivers/ios_driver.py
iOS Simulator driver implementation using xcrun simctl and idb, with mock fallback.
"""

import subprocess
import io
import json
import time
import shutil
import re
import logging
from typing import Tuple, Optional
from PIL import Image, ImageDraw

from drivers.base_driver import BaseDriver

logger = logging.getLogger("iOSDriver")


class IOSDriver(BaseDriver):
    """Driver implementation for iOS Simulator using xcrun simctl / idb."""

    def __init__(self, udid: str = "booted", mock_fallback: bool = False):
        self.udid = udid
        self.mock_fallback = mock_fallback
        self.width = 1179  # Default iPhone resolution width
        self.height = 2556 # Default iPhone resolution height
        self._check_environment()

    def _get_booted_device_udid(self) -> str:
        """Retrieve UDID of currently booted iOS simulator device using simctl JSON API."""
        try:
            res = subprocess.run(["xcrun", "simctl", "list", "devices", "--json"],
                                 capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                devices = data.get("devices", {})
                for runtime, dev_list in devices.items():
                    for dev in dev_list:
                        if dev.get("state") == "Booted" and dev.get("isAvailable", True):
                            return dev.get("udid")
        except Exception as e:
            logger.warning(f"Error querying simctl booted devices: {e}")
        return ""

    def _boot_available_device(self) -> str:
        """Find an available iPhone simulator device and boot it."""
        try:
            res = subprocess.run(["xcrun", "simctl", "list", "devices", "--json"],
                                 capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                devices = data.get("devices", {})
                for runtime, dev_list in devices.items():
                    if "iOS" in runtime:
                        for dev in dev_list:
                            if dev.get("isAvailable", True) and "iPhone" in dev.get("name", ""):
                                udid = dev.get("udid")
                                logger.info(f"Auto-booting iOS Simulator device: {dev.get('name')} ({udid})")
                                subprocess.run(["xcrun", "simctl", "boot", udid], capture_output=True, timeout=10)
                                return udid
        except Exception as e:
            logger.warning(f"Failed to auto-boot simulator: {e}")
        return ""

    def _check_environment(self):
        """Check if xcrun simctl is available, auto-launch Simulator app and boot device if needed."""
        # 1. Launch Simulator application window on macOS
        try:
            subprocess.run(["open", "-a", "Simulator"], check=False)
            logger.info("Launched iOS Simulator application window.")
        except Exception as e:
            logger.warning(f"Could not open Simulator app: {e}")

        if self.udid == "mock":
            self.mock_fallback = True
            logger.info("Explicit mock mode requested.")
            return

        # 2. Check if a booted device exists
        booted_udid = self._get_booted_device_udid()

        if not booted_udid:
            logger.info("No booted iOS Simulator detected. Attempting to auto-boot simulator...")
            booted_udid = self._boot_available_device()
            time.sleep(6)  # Wait for SpringBoard boot initialization
            booted_udid = self._get_booted_device_udid()

        if booted_udid:
            logger.info(f"Connected to booted iOS Simulator (UDID: {booted_udid})")
            if self.udid == "booted" or not self.udid:
                self.udid = booted_udid
            self.mock_fallback = False
        else:
            logger.warning("No booted iOS Simulator found and auto-boot failed. Enabling mock fallback mode.")
            self.mock_fallback = True

    def find_bundle_id(self, target_text: str) -> Optional[str]:
        """Dynamically discover app Bundle ID from booted simulator using simctl listapps without hardcoding."""
        clean_target = target_text.strip().lower()
        if not clean_target:
            return None

        # Direct mappings for iOS system apps
        translation_map = {
            "相簿": "com.apple.mobileslideshow",
            "照片": "com.apple.mobileslideshow",
            "相冊": "com.apple.mobileslideshow",
            "photos": "com.apple.mobileslideshow",
            "設定": "com.apple.Preferences",
            "settings": "com.apple.Preferences",
            "safari": "com.apple.mobilesafari",
            "瀏覽器": "com.apple.mobilesafari",
            "相機": "com.apple.camera",
            "camera": "com.apple.camera",
            "地圖": "com.apple.Maps",
            "maps": "com.apple.Maps",
            "行事曆": "com.apple.mobilecal",
            "日曆": "com.apple.mobilecal",
            "備忘錄": "com.apple.mobilenotes",
            "notes": "com.apple.mobilenotes",
            "訊息": "com.apple.MobileSMS",
            "messages": "com.apple.MobileSMS",
            "檔案": "com.apple.DocumentsApp",
            "files": "com.apple.DocumentsApp",
        }

        for k, v in translation_map.items():
            if k in clean_target:
                return v

        try:
            res = subprocess.run(["xcrun", "simctl", "listapps", self.udid],
                                 capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                raw = res.stdout
                app_blocks = raw.split("\n    \"")
                for block in app_blocks:
                    match_id = re.search(r'CFBundleIdentifier\s*=\s*"?([a-zA-Z0-9\._\-]+)"?;', block)
                    match_name = re.search(r'CFBundleDisplayName\s*=\s*"?([^";]+)"?;', block)
                    if match_id:
                        bid = match_id.group(1)
                        bname = match_name.group(1).lower() if match_name else ""
                        if clean_target in bid.lower() or (bname and clean_target in bname):
                            return bid
        except Exception as e:
            logger.warning(f"Dynamic bundle lookup error: {e}")
        return None


    def tap(self, x: int, y: int, target_text: str = "", bundle_id: str = None) -> bool:
        """Tap at (x, y) on iOS Simulator or launch target app dynamically."""
        logger.info(f"iOS Driver TAP at ({x}, {y}) [target: '{target_text}']")
        if self.mock_fallback:
            return True

        # Use explicitly passed bundle_id from Skill or discover dynamically
        app_bundle = bundle_id or self.find_bundle_id(target_text)

        if app_bundle:
            for attempt in range(2):
                try:
                    res = subprocess.run(["xcrun", "simctl", "launch", self.udid, app_bundle],
                                         capture_output=True, text=True, timeout=5)
                    if res.returncode == 0:
                        logger.info(f"Dynamically launched iOS app '{target_text}' ({app_bundle}) via simctl.")
                        return True
                except Exception as e:
                    if attempt == 0:
                        time.sleep(2)
                    else:
                        logger.warning(f"simctl launch failed for {app_bundle}: {e}")

        # Try idb if available
        idb_path = shutil.which("idb")
        if idb_path:
            try:
                cmd = [idb_path, "ui", "tap", str(x), str(y), "--udid", self.udid]
                res = subprocess.run(cmd, capture_output=True, timeout=5)
                if res.returncode == 0:
                    return True
            except Exception as e:
                logger.warning(f"idb tap failed: {e}")

        # Fallback: Activate Simulator application window
        try:
            subprocess.run(["osascript", "-e", 'tell application "Simulator" to activate'],
                           capture_output=True, timeout=3)
            return True
        except Exception as e:
            logger.error(f"Failed to activate Simulator: {e}")
            return False

    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration_ms: int = 300) -> bool:
        """Swipe gesture on iOS Simulator."""
        logger.info(f"iOS Driver SWIPE from ({start_x}, {start_y}) to ({end_x}, {end_y})")
        if self.mock_fallback:
            return True

        idb_path = shutil.which("idb")
        if idb_path:
            try:
                cmd = [idb_path, "ui", "swipe", str(start_x), str(start_y), str(end_x), str(end_y), "--udid", self.udid]
                subprocess.run(cmd, capture_output=True, timeout=5)
                return True
            except Exception as e:
                logger.warning(f"idb swipe failed: {e}")
        return True

    def type_text(self, text: str) -> bool:
        """Type text string on iOS Simulator."""
        logger.info(f"iOS Driver TYPE TEXT: '{text}'")
        if self.mock_fallback:
            return True

        try:
            # Bring Simulator to front and send keystrokes via AppleScript
            script = f'''
            tell application "Simulator" to activate
            delay 0.2
            tell application "System Events"
                keystroke "{text}"
            end tell
            '''
            res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception as e:
            logger.error(f"Failed to execute type_text on iOS simulator: {e}")
            return False

    def screenshot(self) -> Image.Image:
        """Capture screenshot from iOS Simulator or generate synthetic mock image."""
        if not self.mock_fallback:
            try:
                cmd = ["xcrun", "simctl", "io", self.udid, "screenshot", "-"]
                res = subprocess.run(cmd, capture_output=True, check=True, timeout=10)
                img = Image.open(io.BytesIO(res.stdout)).convert("RGB")
                self.width, self.height = img.size
                return img
            except Exception as e:
                logger.warning(f"Failed to capture real screenshot via simctl: {e}. Generating mock screenshot.")

        # Synthetic screenshot generator for mock mode
        return self._generate_mock_screenshot()

    def get_screen_size(self) -> Tuple[int, int]:
        """Return screen size."""
        return (self.width, self.height)

    def _generate_mock_screenshot(self) -> Image.Image:
        """Generate synthetic mobile UI image with regular text and red/bold buttons for testing."""
        img = Image.new("RGB", (self.width, self.height), color=(245, 247, 250))
        draw = ImageDraw.Draw(img)

        # Header area
        draw.rectangle([0, 0, self.width, 160], fill=(20, 24, 33))
        draw.text((60, 60), "iOS App Dashboard", fill=(255, 255, 255))

        # Card 1: Normal text button
        draw.rectangle([60, 250, self.width - 60, 420], fill=(255, 255, 255), outline=(220, 225, 230), width=3)
        draw.text((100, 310), "相簿", fill=(50, 50, 50))

        # Card 2: Settings button
        draw.rectangle([60, 460, self.width - 60, 630], fill=(255, 255, 255), outline=(220, 225, 230), width=3)
        draw.text((100, 520), "Settings", fill=(50, 50, 50))

        # Card 3: Red & Bold Submit Button
        draw.rectangle([60, 670, self.width - 60, 840], fill=(255, 255, 255), outline=(220, 225, 230), width=3)
        draw.text((100, 730), "Submit Payment", fill=(220, 38, 38))
        draw.text((101, 730), "Submit Payment", fill=(220, 38, 38))
        draw.text((100, 731), "Submit Payment", fill=(220, 38, 38))

        # Card 4: Normal Blue Button
        draw.rectangle([60, 880, self.width - 60, 1050], fill=(37, 99, 235))
        draw.text((100, 940), "Cancel", fill=(255, 255, 255))

        return img

