"""
ai/llm_planner.py
Streamlined Gemini Vision LLM planner and action decision module.
"""

import json
import logging
import io
import re
from typing import Dict, Any, List, Optional
from PIL import Image
from config.settings import settings
from ai.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger("LLMPlanner")


class LLMPlanner:
    """Streamlined Gemini Vision LLM Client translating screenshots into RPA actions."""

    def __init__(self, api_key: str = None, model_name: str = None, provider: str = None):
        self.api_key = api_key or settings.llm.api_key
        self.model_name = model_name or settings.llm.model_name
        self.provider = provider or settings.llm.provider

    def plan_next_action(
        self,
        image: Image.Image,
        goal: str,
        history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze screenshot and goal to produce structured action dict."""
        if self.provider == "mock" or not self.api_key:
            logger.info("Using rule-based mock LLM Planner (offline mode or API Key missing).")
            return self._mock_plan(image, goal, history)

        try:
            return self._call_gemini(image, goal, history)
        except Exception as e:
            logger.error(f"Gemini Vision API call failed: {e}. Falling back to mock planner.")
            return self._mock_plan(image, goal, history)

    def _call_gemini(self, image: Image.Image, goal: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call Google Gemini Vision API using google-genai package or direct REST fallback."""
        if not self.api_key:
            logger.error("❌ [Gemini API Key Missing] Please set 'gemini_api_key' in config.ini or export GEMINI_API_KEY environment variable.")
            raise ValueError("Missing Gemini API Key")

        target_model = self.model_name if "gemini" in self.model_name else "gemini-2.5-flash"
        prompt = SYSTEM_PROMPT + "\n\n" + build_user_prompt(goal, history)

        # 1. Try official google-genai SDK
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=target_model,
                contents=[image, prompt]
            )
            return self._parse_json_response(response.text)
        except ImportError:
            logger.info("google-genai SDK not installed. Using direct HTTP REST API for Gemini Vision.")
        except Exception as e:
            logger.warning(f"google-genai SDK call failed: {e}. Retrying via direct HTTP REST API...")

        # 2. Fallback to direct HTTP REST API (zero extra SDK dependency)
        import base64
        import requests

        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": base64_image
                            }
                        }
                    ]
                }
            ]
        }
        resp = requests.post(url, json=payload, timeout=30)
        if resp.status_code != 200:
            logger.error(f"Gemini REST API error ({resp.status_code}): {resp.text}")
            resp.raise_for_status()

        res_data = resp.json()
        raw_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
        return self._parse_json_response(raw_text)

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Clean markdown wrapping and parse JSON dict."""
        cleaned = re.sub(r"```json\s*", "", text)
        cleaned = re.sub(r"```\s*", "", cleaned).strip()
        try:
            return json.loads(cleaned)
        except Exception as e:
            logger.warning(f"Failed to parse JSON response: {e}. Raw response: {text}")
            return {
                "thought": "Failed to parse LLM response JSON",
                "action": "finish",
                "target_text": ""
            }

    def _mock_plan(self, image: Image.Image, goal: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Rule-based mock decision engine for offline execution, fallback, and heuristic testing."""
        goal_lower = goal.lower()
        step_count = len(history) if history else 0

        logger.warning(
            f"⚠️ [Mock Planner Mode] Executing rule-based heuristic step {step_count + 1} for goal: '{goal}'"
        )

        # Photo-related goals ("相簿", "相冊", "照片", "第一張", "紅色花", "photos", etc.)
        if any(k in goal_lower for k in ["相簿", "相冊", "照片", "photo", "image", "picture", "第一張", "紅色花"]):
            if step_count == 0:
                return {
                    "thought": "Mock Heuristic: Goal involves viewing/opening photo. Step 1: Open/Focus Photos app.",
                    "action": "tap",
                    "target_text": "相簿",
                    "coordinates": [200, 410]
                }
            elif step_count == 1:
                return {
                    "thought": "Mock Heuristic: Photos app active. Step 2: Tap target photo item in grid at (250, 480).",
                    "action": "tap",
                    "target_text": "相片/圖片",
                    "coordinates": [250, 480]
                }
            else:
                return {
                    "thought": "Mock Heuristic: Photo opened successfully. Finish task goal.",
                    "action": "finish",
                    "target_text": "",
                    "coordinates": None
                }

        # General multi-step finish check
        if step_count >= 2:
            return {
                "thought": "Target UI interaction completed. Finish task goal.",
                "action": "finish",
                "target_text": "",
                "coordinates": None
            }

        if "submit" in goal_lower or "login" in goal_lower:
            return {
                "thought": "User goal requests clicking submit button. Identified 'Submit Payment' on screen at (275, 710).",
                "action": "tap",
                "target_text": "Submit Payment",
                "coordinates": [275, 710]
            }
        elif "confirm" in goal_lower:
            return {
                "thought": "User goal requests confirmation. Identified 'Confirm Action' button at (270, 730).",
                "action": "tap",
                "target_text": "Confirm Action",
                "coordinates": [270, 730]
            }
        elif "search" in goal_lower:
            return {
                "thought": "User goal requests searching product. Identified search bar at (270, 430).",
                "action": "type",
                "target_text": "Search Products",
                "input_text": "iPhone 15",
                "coordinates": [270, 430]
            }
        else:
            if step_count == 0:
                return {
                    "thought": "Identified target element on screen based on user goal request.",
                    "action": "tap",
                    "target_text": "Settings",
                    "coordinates": [200, 410]
                }
            else:
                return {
                    "thought": "Target interaction completed.",
                    "action": "finish",
                    "target_text": "",
                    "coordinates": None
                }
