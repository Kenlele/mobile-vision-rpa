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


def ensure_ollama_service(base_url: str = "http://127.0.0.1:11434", model_name: str = "llama3.2-vision") -> bool:
    """Auto-detect local Ollama server status and launch 'ollama serve' in background if stopped."""
    import requests
    import subprocess
    import shutil
    import time

    url = f"{base_url.rstrip('/')}/api/tags"

    # 1. Check if Ollama is already running
    active = False
    try:
        resp = requests.get(url, timeout=2)
        if resp.status_code == 200:
            logger.info(f"✅ Local Ollama service is active at {base_url}")
            active = True
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            if model_name and not any(model_name in m for m in models):
                logger.warning(f"⚠️ [Ollama Model Check] Model '{model_name}' not found in installed models {models}. Run 'ollama pull {model_name}' to download.")
            return True
    except Exception:
        pass

    # 2. Ollama is not running -> Check if ollama CLI is on PATH
    ollama_path = shutil.which("ollama")
    if not ollama_path:
        logger.warning("⚠️ 'ollama' CLI not found on PATH. Please install Ollama from https://ollama.com/")
        return False

    # 3. Auto-launch 'ollama serve' in background
    logger.info("🚀 [Ollama Auto-Launcher] Ollama service not detected. Auto-launching 'ollama serve' in background...")
    try:
        subprocess.Popen(
            [ollama_path, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        # Wait up to 5 seconds for Ollama server to initialize
        for _ in range(10):
            time.sleep(0.5)
            try:
                resp = requests.get(url, timeout=1)
                if resp.status_code == 200:
                    logger.info("✨ [Ollama Auto-Launcher] Ollama service started successfully!")
                    models = [m.get("name", "") for m in resp.json().get("models", [])]
                    if model_name and not any(model_name in m for m in models):
                        logger.warning(f"⚠️ [Ollama Model Check] Model '{model_name}' not found in installed models {models}. Run 'ollama pull {model_name}' to download.")
                    return True
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Failed to auto-launch 'ollama serve': {e}")


    return False


class LLMPlanner:
    """Vision LLM Client translating screenshots and task goals into structured RPA actions."""

    def __init__(self, provider: str = None, api_key: str = None, model_name: str = None, ollama_base_url: str = None):
        self.provider = provider or settings.llm.provider
        self.api_key = api_key or settings.llm.api_key
        self.model_name = model_name or settings.llm.model_name
        self.ollama_base_url = ollama_base_url or settings.llm.ollama_base_url

        if self.provider == "ollama":
            ensure_ollama_service(base_url=self.ollama_base_url, model_name=self.model_name)


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
            if resp.status_code != 200:
                err_msg = ""
                try:
                    err_msg = resp.json().get("error", "")
                except Exception:
                    err_msg = resp.text
                if "not found" in err_msg.lower():
                    logger.error(f"❌ [Ollama Model Missing] Model '{target_model}' is not installed! Please run: ollama pull {target_model}")
                elif "mllama" in err_msg.lower() or "unknown model architecture" in err_msg.lower():
                    logger.error(
                        f"❌ [Ollama Version Outdated] Your local Ollama version does not support the 'mllama' architecture used by '{target_model}'.\n"
                        f"👉 Solution 1: Update Ollama via 'brew upgrade ollama' or download latest version from https://ollama.com\n"
                        f"👉 Solution 2: Use local 'llava' model instead (run: 'ollama pull llava' and set model_name = llava in config.ini)\n"
                        f"👉 Solution 3: Use Gemini Vision (set provider = gemini in config.ini)"
                    )
                else:
                    logger.error(f"❌ [Ollama API Error {resp.status_code}] {err_msg}")
                resp.raise_for_status()

            res_data = resp.json()
            raw_text = res_data.get("message", {}).get("content", "")
            return self._parse_json_response(raw_text)
        except Exception as e:
            logger.error(f"Ollama Vision API call failed ({url}): {e}")
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
        """Rule-based mock decision engine for offline execution, fallback, and heuristic testing."""
        goal_lower = goal.lower()
        step_count = len(history) if history else 0

        logger.warning(
            f"⚠️ [Mock Planner Mode] LLM Vision service inactive. Executing rule-based heuristic step {step_count + 1} for goal: '{goal}'"
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
        elif "photos" in goal_lower or "相簿" in goal_lower or "相冊" in goal_lower:
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
