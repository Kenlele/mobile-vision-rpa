"""
vision/style_detector.py
OpenCV image processing to evaluate text style attributes (e.g. bold font detection).
"""

import cv2
import numpy as np
import logging
from typing import Dict, Any, Union
from PIL import Image
from config.settings import settings

logger = logging.getLogger("StyleDetector")


class StyleDetector:
    """OpenCV text style analyzer to evaluate font weight (bold vs normal)."""

    def __init__(self, edge_density_threshold: float = None, stroke_width_threshold: float = None):
        self.edge_density_threshold = edge_density_threshold or settings.style.bold_edge_density_threshold
        self.stroke_width_threshold = stroke_width_threshold or settings.style.bold_stroke_width_threshold

    def is_bold(self, roi_image: Union[Image.Image, np.ndarray]) -> Dict[str, Any]:
        """
        Analyze whether text within cropped ROI is bold formatted.
        
        Returns:
            {
                "is_bold": bool,
                "edge_density": float,
                "stroke_width": float,
                "ink_ratio": float
            }
        """
        if isinstance(roi_image, Image.Image):
            np_img = np.array(roi_image.convert("RGB"))
            bgr = cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)
        else:
            bgr = roi_image

        if bgr.size == 0 or bgr.shape[0] < 5 or bgr.shape[1] < 5:
            return {"is_bold": False, "edge_density": 0.0, "stroke_width": 0.0, "ink_ratio": 0.0}

        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        # 1. Edge Detection via Canny
        edges = cv2.Canny(gray, 50, 150)
        edge_pixels = cv2.countNonZero(edges)
        total_pixels = gray.shape[0] * gray.shape[1]
        edge_density = edge_pixels / float(total_pixels)

        # 2. Binary Thresholding for Ink Analysis
        # Otsu thresholding to separate text ink from background
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        ink_pixels = cv2.countNonZero(binary)
        ink_ratio = ink_pixels / float(total_pixels)

        # 3. Distance Transform for Stroke Thickness Estimation
        dist_transform = cv2.distanceTransform(binary, cv2.DIST_L2, 3)
        max_stroke_radius = np.max(dist_transform) if np.any(dist_transform) else 0.0
        stroke_width = max_stroke_radius * 2.0

        # Bold heuristic score
        is_bold_detected = (edge_density >= self.edge_density_threshold) or (stroke_width >= self.stroke_width_threshold) or (ink_ratio > 0.35)

        logger.debug(f"Style Analysis: edge_density={edge_density:.4f}, stroke_width={stroke_width:.2f}, ink_ratio={ink_ratio:.4f}, is_bold={is_bold_detected}")

        return {
            "is_bold": is_bold_detected,
            "edge_density": round(edge_density, 4),
            "stroke_width": round(stroke_width, 2),
            "ink_ratio": round(ink_ratio, 4)
        }
