"""
ai/llm_planner.py
Vision LLM caller and action planner module.
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
    """Vision LLM Client translating screenshots and task goals into structured RPA actions."""

    def __init__(self, provider: str = None, api_key: str = None, model_name: str = None, ollama_base_url: str = None):
        self.provider = provider or settings.llm.provider
        self.api_key = api_key or settings.llm.api_key
        self.model_name = model_name or settings.llm.model_name
        self.ollama_base_url = ollama_base_url or settings.llm.ollama_base_url

    def plan_next_action(
        self,
        image: Image.Image,
        goal: str,
        history: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze screenshot and goal to produce structured action dict.
        """
        if self.provider == "ollama":
            try:
                return self._call_ollama(image, goal, history)
            except Exception as e:
                logger.error(f"Ollama Vision API call failed: {e}. Falling back to mock planner.")
                return self._mock_plan(image, goal, history)

        if not self.api_key or self.provider == "mock":
            logger.info("Using heuristic rule-based mock LLM Planner.")
            return self._mock_plan(image, goal, history)

        try:
            if self.provider == "gemini":
                return self._call_gemini(image, goal, history)
            elif self.provider == "openai":
                return self._call_openai(image, goal, history)
            else:
                return self._mock_plan(image, goal, history)
        except Exception as e:
            logger.error(f"Vision LLM call failed: {e}. Falling back to mock planner.")
            return self._mock_plan(image, goal, history)


    def _call_gemini(self, image: Image.Image, goal: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call Google Gemini Vision API using google-genai package."""
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            prompt = SYSTEM_PROMPT + "\n\n" + build_user_prompt(goal, history)
            
            response = client.models.generate_content(
                model=self.model_name,
                contents=[image, prompt]
            )
            return self._parse_json_response(response.text)
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    def _call_openai(self, image: Image.Image, goal: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call OpenAI Vision API."""
        import base64
        import requests

        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        user_content = build_user_prompt(goal, history)
        payload = {
            "model": self.model_name if "gpt" in self.model_name else "gpt-4o",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_content},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            "temperature": 0.1
        }

        resp = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        res_data = resp.json()
        raw_text = res_data["choices"][0]["message"]["content"]
        return self._parse_json_response(raw_text)

    def _call_ollama(self, image: Image.Image, goal: str, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Call local Ollama Vision API endpoint."""
        import base64
        import requests

        buffered = io.BytesIO()
        image.save(buffered, format="JPEG")
        base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

        prompt = SYSTEM_PROMPT + "\n\n" + build_user_prompt(goal, history)
        url = f"{self.ollama_base_url.rstrip('/')}/api/chat"
        target_model = self.model_name if self.model_name and self.model_name not in ["gemini-2.5-flash", "gpt-4o"] else "llama3.2-vision"

        payload = {
            "model": target_model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [base64_image]
                }
            ],
            "stream": False
        }

        try:
            logger.info(f"Calling Local Ollama Vision model '{target_model}' at {url}...")
            resp = requests.post(url, json=payload, timeout=60)
            resp.raise_for_status()
            res_data = resp.json()
            raw_text = res_data.get("message", {}).get("content", "")
            return self._parse_json_response(raw_text)
        except Exception as e:
            logger.error(f"Ollama Vision API error ({url}): {e}. Ensure Ollama is running ('ollama serve') and model is pulled ('ollama pull {target_model}').")
            raise


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
        """Rule-based mock decision engine for offline execution and testing."""
        goal_lower = goal.lower()
        step_count = len(history) if history else 0

        if step_count >= 1:
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
        elif "photos" in goal_lower or "相簿" in goal_lower or "相冊" in goal_lower or "照片" in goal_lower:
            return {
                "thought": "User requested opening Photos app. Identified target: '相簿'.",
                "action": "tap",
                "target_text": "相簿",
                "coordinates": [200, 410]
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
            return {
                "thought": "Identified target element on screen based on user goal request.",
                "action": "tap",
                "target_text": "Settings",
                "coordinates": [200, 410]
            }
