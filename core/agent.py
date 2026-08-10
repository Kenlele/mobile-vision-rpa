"""
core/agent.py
Central RPA Agent orchestrating Pure AI Vision planning and device execution.
"""

import os
import time
import logging
from typing import Dict, Any, List, Optional
from PIL import Image

from drivers.base_driver import BaseDriver
from vision.ocr_engine import OCREngine
from vision.screen_verifier import ScreenVerifier
from ai.llm_planner import LLMPlanner
from core.skill_manager import SkillManager
from config.settings import settings

logger = logging.getLogger("RPAAgent")


class RPAAgent:
    """Core RPA Agent coordinating AI vision decisions, Skill engine, and driver execution."""

    def __init__(
        self,
        driver: BaseDriver,
        ocr_engine: Optional[OCREngine] = None,
        llm_planner: Optional[LLMPlanner] = None,
        skill_manager: Optional[SkillManager] = None
    ):
        self.driver = driver
        self.ocr = ocr_engine or OCREngine()
        self.planner = llm_planner or LLMPlanner()
        self.skill_manager = skill_manager or SkillManager()
        self.history: List[Dict[str, Any]] = []

        # Ensure output debug directory exists
        os.makedirs(settings.output_dir, exist_ok=True)


    def run(self, goal: str, max_steps: int = 5) -> Dict[str, Any]:
        """Execute RPA task goal loop with Skill Engine matching and dynamic AI Vision fallback."""
        logger.info("=== Starting Pure AI Vision RPA Loop ===")
        logger.info(f"Task Goal: '{goal}'")
        self.history = []

        # Step 1: Check if an existing SKILL.md matches the task goal
        matched_skill = self.skill_manager.find_matching_skill(goal)
        if matched_skill:
            return self._execute_skill(matched_skill, goal)

        # Step 2: Dynamic AI Discovery & Execution if no Skill matched
        logger.info("⚡ [Skill Engine] No matching SKILL.md found. Executing dynamic AI Vision discovery...")
        step = 0
        success = False

        while step < max_steps:
            step += 1
            logger.info(f"\n--- Step {step}/{max_steps} ---")

            # Capture screenshot
            screenshot = self.driver.screenshot()
            self._save_debug_screenshot(screenshot, f"step_{step}_screenshot.png")

            # Get action plan directly from LLM / AI Vision
            action_plan = self.planner.plan_next_action(screenshot, goal, self.history)
            logger.info(f"AI Thought: {action_plan.get('thought')}")
            logger.info(f"AI Decision: {action_plan.get('action')} on '{action_plan.get('target_text')}'")

            action_type = action_plan.get("action", "finish").lower()

            if action_type == "finish":
                logger.info("Task completed successfully!")
                success = True
                break

            step_result = self._execute_action(screenshot, action_plan)
            self.history.append({
                "step": step,
                "plan": action_plan,
                "result": step_result
            })

            if not step_result.get("success", False):
                logger.warning(f"Step {step} failed: {step_result.get('error')}")

            time.sleep(1)

        # Step 3: Automatically generate & persist a new SKILL.md if task succeeded
        if success:
            self.skill_manager.create_skill_from_execution(goal, self.history)

        return {
            "goal": goal,
            "success": success,
            "total_steps": step,
            "history": self.history
        }

    def _execute_skill(self, skill: Dict[str, Any], goal: str) -> Dict[str, Any]:
        """Execute pre-learned SKILL.md steps directly."""
        logger.info(f"🚀 [Skill Engine] Reusing learned SKILL.md: '{skill.get('name')}'")
        steps = skill.get("steps", [])
        executed_steps = 0

        for s in steps:
            executed_steps += 1
            action = s.get("action")
            target_text = s.get("target_text", "")
            bundle_id = s.get("bundle_id")

            logger.info(f"Executing SKILL.md Step {executed_steps}: {action} on '{target_text}'")
            screenshot = self.driver.screenshot()
            plan = {"action": action, "target_text": target_text, "bundle_id": bundle_id, "coordinates": s.get("coordinates")}
            res = self._execute_action(screenshot, plan)

            self.history.append({
                "step": executed_steps,
                "plan": plan,
                "result": res
            })

        logger.info(f"✅ [Skill Engine] Successfully completed task using SKILL.md '{skill.get('name')}'!")
        return {
            "goal": goal,
            "success": True,
            "total_steps": executed_steps,
            "history": self.history,
            "used_skill": skill.get("name")
        }

    def _execute_action(self, screenshot: Image.Image, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Execute driver action based on AI Vision decisions."""
        action_type = plan.get("action")
        target_text = plan.get("target_text", "")
        target_coords = plan.get("coordinates")

        # Priority 1: Real-time Local Apple Vision OCR scanning on live screenshot
        if target_text:
            match = self.ocr.find_target(screenshot, target_text)
            if match:
                target_coords = match["center"]
                plan["coordinates"] = target_coords
                logger.info(f"🔍 [Local Vision OCR] Located target '{target_text}' (detected: '{match.get('text')}') at exact screen coordinates {target_coords}")

        if not target_coords and action_type in ["tap", "type"]:
            return {"success": False, "error": f"No target coordinates found on screen for action '{action_type}'"}

        status = False
        if action_type == "tap":
            cx, cy = target_coords
            bundle_id = plan.get("bundle_id")
            if hasattr(self.driver, "find_bundle_id") and not bundle_id:
                bundle_id = self.driver.find_bundle_id(target_text)
                plan["bundle_id"] = bundle_id

            status = self.driver.tap(cx, cy, target_text=target_text, bundle_id=bundle_id)
        elif action_type == "swipe":
            swipe_coords = plan.get("swipe_coords", [500, 1500, 500, 500])
            status = self.driver.swipe(swipe_coords[0], swipe_coords[1], swipe_coords[2], swipe_coords[3])
        elif action_type == "type":
            cx, cy = target_coords
            text_to_type = plan.get("input_text", "")
            self.driver.tap(cx, cy)
            status = self.driver.type_text(text_to_type)
        elif action_type == "assert":
            logger.info(f"AI Self-Assertion PASSED for target: '{target_text}'")
            return {"success": True, "asserted": target_text}
        else:
            return {"success": False, "error": f"Unknown action type '{action_type}'"}

        # Verify action success via post-action screenshot & Screen Delta
        time.sleep(0.5)
        img_after = self.driver.screenshot()
        verification = ScreenVerifier.verify_action_success(screenshot, img_after, action_type, target_text)

        return {
            "success": status and verification.get("success", True),
            "tapped_coords": target_coords,
            "bundle_id": plan.get("bundle_id"),
            "screen_delta": verification.get("delta", 0.0),
            "verification_reason": verification.get("reason", "")
        }

    def _save_debug_screenshot(self, image: Image.Image, filename: str):
        """Save debug screenshot image to output directory."""
        try:
            filepath = os.path.join(settings.output_dir, filename)
            image.save(filepath)
        except Exception as e:
            logger.debug(f"Failed to save debug screenshot: {e}")
