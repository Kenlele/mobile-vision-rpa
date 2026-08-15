"""
core/runner.py
Framework execution runner orchestrating driver initialization, LLM planning, agent execution, and reporting.
"""

import logging
from typing import Dict, Any, Optional
from drivers.driver_factory import DriverFactory
from ai.llm_planner import LLMPlanner
from core.agent import RPAAgent
from config.settings import settings

logger = logging.getLogger("FrameworkRunner")


class FrameworkRunner:
    """Orchestrates configuration, components initialization, and RPA task execution."""

    def __init__(
        self,
        driver_mode: Optional[str] = None,
        udid: Optional[str] = None,
        provider: Optional[str] = None
    ):
        self.driver_mode = driver_mode or settings.driver.driver_type or "ios"
        self.udid = udid or settings.driver.ios_udid or "booted"
        self.provider = provider or settings.llm.provider or "gemini"


        # 1. Initialize Driver Layer via DriverFactory
        self.driver = DriverFactory.create_driver(driver_type=self.driver_mode, udid=self.udid)

        # 2. Initialize LLM Planner
        self.planner = LLMPlanner(provider=self.provider)

        # 3. Instantiate Agent Orchestrator
        self.agent = RPAAgent(driver=self.driver, llm_planner=self.planner)

    def execute(self, prompt: str, max_steps: int = 5) -> Dict[str, Any]:
        """
        Execute automation task based on user prompt/goal.
        """
        logger.info("==========================================")
        logger.info("      MOBILE VISION RPA FRAMEWORK         ")
        logger.info("==========================================")
        logger.info(f"Target OS: iOS")
        logger.info(f"Driver Mode: {self.driver_mode}")
        logger.info(f"LLM Provider: {self.provider}")
        logger.info(f"Task Prompt: {prompt}")

        # Run RPA Agent
        result = self.agent.run(goal=prompt, max_steps=max_steps)

        # Print Execution Report
        self._print_summary_report(result)
        return result

    def _print_summary_report(self, result: Dict[str, Any]):
        """Print formatted execution summary report."""
        logger.info("\n==========================================")
        logger.info("          EXECUTION SUMMARY               ")
        logger.info("==========================================")
        logger.info(f"Task Status: {'SUCCESS' if result['success'] else 'FAILED'}")
        logger.info(f"Total Steps Taken: {result['total_steps']}")
        for step in result.get('history', []):
            plan = step.get('plan', {})
            res = step.get('result', {})
            logger.info(
                f"  Step {step.get('step')}: Action='{plan.get('action')}' "
                f"Target='{plan.get('target_text')}' -> Success={res.get('success')}"
            )
        logger.info("==========================================\n")
