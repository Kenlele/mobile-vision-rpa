"""
tests/test_framework.py
Automated unit tests for Mobile Vision RPA framework.
"""

import unittest
from PIL import Image

from drivers.driver_factory import DriverFactory
from drivers.base_driver import BaseDriver
from drivers.mirroring_driver import MirroringDriver
from ai.llm_planner import LLMPlanner
from core.skill_manager import SkillManager
from core.agent import RPAAgent
from vision.screen_verifier import ScreenVerifier


class TestFrameworkComponents(unittest.TestCase):

    def test_driver_factory_mock(self):
        """Test creating mock driver via factory."""
        driver = DriverFactory.create_driver("mock")
        self.assertIsInstance(driver, BaseDriver)
        self.assertTrue(driver.mock_fallback)
        self.assertEqual(driver.get_screen_size(), (1179, 2556))

    def test_driver_factory_mirroring(self):
        """Test creating macOS iPhone Mirroring driver via factory."""
        driver = DriverFactory.create_driver("mirroring")
        self.assertIsInstance(driver, MirroringDriver)

    def test_llm_planner_mock(self):
        """Test rule-based mock planner output."""
        planner = LLMPlanner(provider="mock")
        img = Image.new("RGB", (100, 100))
        plan = planner.plan_next_action(img, "測試相簿")
        self.assertEqual(plan.get("action"), "tap")
        self.assertEqual(plan.get("target_text"), "相簿")

    def test_llm_planner_ollama(self):
        """Test Ollama planner initialization and fallback when service unavailable."""
        planner = LLMPlanner(provider="ollama", model_name="llama3.2-vision")
        self.assertEqual(planner.provider, "ollama")
        self.assertEqual(planner.model_name, "llama3.2-vision")
        img = Image.new("RGB", (100, 100))
        plan = planner.plan_next_action(img, "測試相簿")
        self.assertIn("action", plan)

    def test_screen_verifier_strict_assertion(self):
        """Test assertion mode in ScreenVerifier (2.0% threshold)."""
        img1 = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img2 = Image.new("RGB", (100, 100), color=(0, 0, 0))
        res_pass = ScreenVerifier.verify_action_success(img1, img2, "tap")
        self.assertTrue(res_pass["success"])
        self.assertGreater(res_pass["delta"], 0.02)

        # Zero delta case (app already active)
        res_zero = ScreenVerifier.verify_action_success(img1, img1, "tap")
        self.assertTrue(res_zero["success"])
        self.assertLess(res_zero["delta"], 0.02)


    def test_rpa_agent_pure_execution(self):
        """Test complete RPA agent dynamic execution loop without skill creation."""
        driver = DriverFactory.create_driver("mock")
        planner = LLMPlanner(provider="mock")
        agent = RPAAgent(driver=driver, llm_planner=planner)
        result = agent.run(goal="測試相簿", max_steps=3)
        self.assertIn("success", result)


if __name__ == "__main__":
    unittest.main()
