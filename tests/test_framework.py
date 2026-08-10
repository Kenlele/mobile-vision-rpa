"""
tests/test_framework.py
Automated unit tests for Mobile Vision RPA framework.
"""

import unittest
from PIL import Image

from drivers.driver_factory import DriverFactory
from drivers.base_driver import BaseDriver
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

    def test_llm_planner_mock(self):
        """Test rule-based mock planner output."""
        planner = LLMPlanner(provider="mock")
        img = Image.new("RGB", (100, 100))
        plan = planner.plan_next_action(img, "測試相簿")
        self.assertEqual(plan.get("action"), "tap")
        self.assertEqual(plan.get("target_text"), "相簿")

    def test_skill_manager_matching(self):
        """Test skill manager discovery and matching."""
        sm = SkillManager()
        matched = sm.find_matching_skill("non_existent_skill_xyz")
        self.assertIsNone(matched)

    def test_screen_verifier_strict_assertion(self):
        """Test strict assertion mode in ScreenVerifier (2.0% threshold)."""
        img1 = Image.new("RGB", (100, 100), color=(255, 255, 255))
        img2 = Image.new("RGB", (100, 100), color=(0, 0, 0))
        res_pass = ScreenVerifier.verify_action_success(img1, img2, "tap")
        self.assertTrue(res_pass["success"])
        self.assertGreater(res_pass["delta"], 0.02)

        # Fail case when screen delta is 0
        res_fail = ScreenVerifier.verify_action_success(img1, img1, "tap")
        self.assertFalse(res_fail["success"])
        self.assertLess(res_fail["delta"], 0.02)

    def test_skill_manager_self_healing_save(self):
        """Test saving self-healed skill in SkillManager."""
        sm = SkillManager()
        history = [
            {"plan": {"action": "tap", "target_text": "測試標籤", "coordinates": [100, 200]}},
            {"plan": {"action": "finish"}}
        ]
        res = sm.create_skill_from_execution("SelfHealingTestSkill", history, self_healed=True)
        self.assertIsNotNone(res)
        self.assertTrue(res.get("self_healed"))

    def test_rpa_agent_mock_run(self):
        """Test complete RPA agent mock execution loop."""
        driver = DriverFactory.create_driver("mock")
        planner = LLMPlanner(provider="mock")
        agent = RPAAgent(driver=driver, llm_planner=planner)
        result = agent.run(goal="測試相簿", max_steps=3)
        self.assertIn("success", result)


if __name__ == "__main__":
    unittest.main()
