"""
vision/ocr_engine.py
Real-time Local macOS Vision OCR Engine.
Scans exact screen pixels for text bounding boxes and pixel center coordinates.
"""

import os
import sys
import json
import logging
import subprocess
import tempfile
from typing import List, Dict, Any, Optional
from PIL import Image

logger = logging.getLogger("OCREngine")


class OCREngine:
    """Real-time Local macOS Vision OCR locator."""

    def __init__(self):
        self.swift_bin = os.path.join(os.path.dirname(__file__), "apple_vision_ocr")
        self._ensure_binary()

    def _ensure_binary(self):
        """Ensure Apple Vision Swift OCR binary is compiled."""
        swift_src = os.path.join(os.path.dirname(__file__), "apple_vision_ocr.swift")
        if not os.path.exists(self.swift_bin) and os.path.exists(swift_src):
            try:
                subprocess.run(["swiftc", swift_src, "-o", self.swift_bin], check=True, capture_output=True)
                logger.info("Compiled local macOS Vision OCR engine.")
            except Exception as e:
                logger.warning(f"Could not compile Swift Vision OCR: {e}")

    def detect(self, image: Image.Image) -> List[Dict[str, Any]]:
        """
        Run real-time local OCR on PIL Image and return detected text bounding boxes and centers.
        """
        if not os.path.exists(self.swift_bin):
            self._ensure_binary()

        if os.path.exists(self.swift_bin):
            try:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    tmp_path = tmp.name
                    image.save(tmp_path)

                res = subprocess.run([self.swift_bin, tmp_path], capture_output=True, text=True, timeout=5)
                if os.path.exists(tmp_path):
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass

                if res.returncode == 0 and res.stdout.strip():
                    detections = json.loads(res.stdout.strip())
                    logger.debug(f"Local macOS Vision OCR detected {len(detections)} text elements.")
                    return detections
            except Exception as e:
                logger.warning(f"Local Vision OCR detection error: {e}")

        return []

    def find_target(self, image: Image.Image, target_text: str) -> Optional[Dict[str, Any]]:
        """
        Search for text matching target_text or synonyms on live screen image.
        """
        clean_target = target_text.strip().lower()
        if not clean_target:
            return None

        detections = self.detect(image)
        if not detections:
            return None

        # Synonyms / Aliases mapping
        aliases = {
            "相簿": ["照片", "相簿", "相冊", "photos", "album"],
            "照片": ["照片", "相簿", "相冊", "photos"],
            "設定": ["設定", "settings", "setting"],
            "相機": ["相機", "camera"],
            "地圖": ["地圖", "maps"],
            "瀏覽器": ["safari", "瀏覽器"],
            "訊息": ["訊息", "messages"],
            "備忘錄": ["備忘錄", "notes"],
            "檔案": ["檔案", "files"],
        }

        search_candidates = [clean_target]
        for k, v_list in aliases.items():
            if k in clean_target:
                search_candidates.extend(v_list)

        # 1. Exact match search
        for candidate in search_candidates:
            for item in detections:
                item_text = item["text"].strip().lower()
                if item_text == candidate:
                    logger.info(f"🎯 Local OCR exact matched '{item['text']}' at center {item['center']}")
                    return item

        # 2. Substring match search (avoid single-letter false positives)
        for candidate in search_candidates:
            if len(candidate) < 2:
                continue
            for item in detections:
                item_text = item["text"].strip().lower()
                if len(item_text) < 2:
                    continue
                if candidate in item_text or item_text in candidate:
                    logger.info(f"🎯 Local OCR fuzzy matched '{item['text']}' at center {item['center']}")
                    return item

        return None
