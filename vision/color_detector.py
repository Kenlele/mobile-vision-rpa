"""
vision/color_detector.py
OpenCV color analysis to detect red text and elements in target screen ROIs.
"""

import cv2
import numpy as np
import logging
from typing import Tuple, Dict, Any, Union
from PIL import Image
from config.settings import settings

logger = logging.getLogger("ColorDetector")


class ColorDetector:
    """OpenCV color analyzer for ROI verification."""

    def __init__(self, red_ratio_threshold: float = None):
        self.red_ratio_threshold = red_ratio_threshold or settings.color.red_ratio_threshold
        self.red_lower1 = np.array(settings.color.red_lower1, dtype=np.uint8)
        self.red_upper1 = np.array(settings.color.red_upper1, dtype=np.uint8)
        self.red_lower2 = np.array(settings.color.red_lower2, dtype=np.uint8)
        self.red_upper2 = np.array(settings.color.red_upper2, dtype=np.uint8)

    def is_red(self, roi_image: Union[Image.Image, np.ndarray]) -> Dict[str, Any]:
        """
        Analyze whether the input ROI contains significant red text/element content.
        
        Returns:
            {
                "is_red": bool,
                "red_ratio": float,
                "threshold": float
            }
        """
        # Convert PIL to OpenCV BGR if necessary
        if isinstance(roi_image, Image.Image):
            np_img = np.array(roi_image.convert("RGB"))
            bgr = cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)
        else:
            bgr = roi_image

        if bgr.size == 0:
            return {"is_red": False, "red_ratio": 0.0, "threshold": self.red_ratio_threshold}

        # Convert to HSV color space
        hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

        # Red HSV ranges
        mask1 = cv2.inRange(hsv, self.red_lower1, self.red_upper1)
        mask2 = cv2.inRange(hsv, self.red_lower2, self.red_upper2)
        red_mask = cv2.bitwise_or(mask1, mask2)

        red_pixel_count = cv2.countNonZero(red_mask)
        total_pixels = bgr.shape[0] * bgr.shape[1]
        red_ratio = red_pixel_count / float(total_pixels) if total_pixels > 0 else 0.0

        is_red_detected = red_ratio >= self.red_ratio_threshold

        logger.debug(f"Color Analysis: red_ratio={red_ratio:.4f}, threshold={self.red_ratio_threshold}, is_red={is_red_detected}")

        return {
            "is_red": is_red_detected,
            "red_ratio": round(red_ratio, 4),
            "threshold": self.red_ratio_threshold
        }
