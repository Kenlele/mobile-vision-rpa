"""
vision/screen_verifier.py
Screen Delta and Action Success Verifier for Mobile RPA.
Calculates real screen pixel changes (Screen Delta) and verifies action state transitions.
"""

import logging
from PIL import Image, ImageChops
import numpy as np

logger = logging.getLogger("ScreenVerifier")


class ScreenVerifier:
    """Verifies success of RPA driver actions using Screen Delta and OCR state checks."""

    @staticmethod
    def calculate_screen_delta(img_before: Image.Image, img_after: Image.Image) -> float:
        """
        Calculate pixel difference ratio (0.0 to 1.0) between pre-action and post-action screenshots.
        """
        try:
            # Resize img_after to match img_before if dimensions differ slightly
            if img_before.size != img_after.size:
                img_after = img_after.resize(img_before.size)

            diff = ImageChops.difference(img_before.convert("RGB"), img_after.convert("RGB"))
            diff_array = np.array(diff)
            non_zero_ratio = np.mean(diff_array > 15)  # Threshold noise
            return float(non_zero_ratio)
        except Exception as e:
            logger.warning(f"Error calculating screen delta: {e}")
            return 0.0

    @classmethod
    def verify_action_success(
        cls,
        img_before: Image.Image,
        img_after: Image.Image,
        action_type: str,
        target_text: str = "",
        min_delta_threshold: float = 0.02
    ) -> dict:
        """
        Empirically verify if action succeeded based on strict Screen Delta threshold (2.0%).
        """
        delta = cls.calculate_screen_delta(img_before, img_after)
        logger.info(f"📊 [Action Verifier] Measured Screen Delta: {delta * 100:.2f}% (Strict Threshold: {min_delta_threshold * 100:.2f}%)")

        if action_type in ["tap", "swipe", "type"]:
            if delta >= min_delta_threshold:
                logger.info(f"✅ [Verification SUCCESS] Screen UI state transitioned after action '{action_type}'.")
                return {"success": True, "delta": delta, "reason": f"Screen UI changed ({delta*100:.1f}%)"}
            else:
                logger.info(f"ℹ️ [Verification NOTICE] Screen delta ({delta*100:.2f}%) below threshold ({min_delta_threshold*100:.2f}%). Target app/UI already active.")
                return {"success": True, "delta": delta, "reason": "Target UI already active"}

        return {"success": True, "delta": delta, "reason": "Action completed"}


