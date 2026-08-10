"""
core/skill_manager.py
Markdown-based Skill Store and Execution Engine (SKILL.md).
Persists reusable skills as human-readable and machine-parseable SKILL.md markdown files in skills/.
"""

import os
import json
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger("SkillManager")


class SkillManager:
    """Manages skill discovery, loading, execution, and automatic Markdown SKILL.md generation."""

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = os.path.abspath(skills_dir)
        os.makedirs(self.skills_dir, exist_ok=True)
        self.skills: List[Dict[str, Any]] = []
        self._load_skills()

    def _load_skills(self):
        """Load all SKILL.md markdown files from skills_dir subdirectories."""
        self.skills = []
        if not os.path.exists(self.skills_dir):
            return

        for item in os.listdir(self.skills_dir):
            item_path = os.path.join(self.skills_dir, item)
            skill_md_path = os.path.join(item_path, "SKILL.md") if os.path.isdir(item_path) else None

            if skill_md_path and os.path.exists(skill_md_path):
                try:
                    skill_data = self._parse_skill_md(skill_md_path)
                    if skill_data:
                        self.skills.append(skill_data)
                        logger.debug(f"Loaded Markdown Skill: {skill_data.get('name')} from {skill_md_path}")
                except Exception as e:
                    logger.warning(f"Failed to parse skill file {skill_md_path}: {e}")

    def _parse_skill_md(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Parse frontmatter and execution steps from a SKILL.md file."""
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        yaml_raw = parts[1].strip()
        body = parts[2].strip()

        meta = {}
        current_list_key = None
        for line in yaml_raw.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            if line_str.startswith("- ") and current_list_key:
                val = line_str[2:].strip(" '\"")
                if current_list_key not in meta or not isinstance(meta[current_list_key], list):
                    meta[current_list_key] = []
                meta[current_list_key].append(val)
            elif ":" in line_str:
                k, v = line_str.split(":", 1)
                k = k.strip()
                v = v.strip()
                current_list_key = k
                if v.startswith("[") and v.endswith("]"):
                    items = [i.strip(" '\"") for i in v[1:-1].split(",") if i.strip()]
                    meta[k] = items
                elif not v:
                    meta[k] = []
                else:
                    meta[k] = v.strip(" '\"")

        # Parse markdown steps
        steps = []
        current_step = {}
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("### Step"):
                if current_step:
                    steps.append(current_step)
                    current_step = {}
            elif line.startswith("- **Action**:") or line.startswith("- Action:"):
                current_step["action"] = line.split(":", 1)[1].strip()
            elif line.startswith("- **Target Text**:") or line.startswith("- Target Text:"):
                current_step["target_text"] = line.split(":", 1)[1].strip()
            elif line.startswith("- **Target App Bundle**:") or line.startswith("- Target App Bundle:"):
                val = line.split(":", 1)[1].strip()
                current_step["bundle_id"] = None if val in ["None", "null", ""] else val
            elif line.startswith("- **Coordinates**:") or line.startswith("- Coordinates:"):
                coords_str = line.split(":", 1)[1].strip()
                try:
                    current_step["coordinates"] = json.loads(coords_str)
                except Exception:
                    pass

        if current_step:
            steps.append(current_step)

        return {
            "name": meta.get("name", os.path.basename(os.path.dirname(filepath))),
            "description": meta.get("description", ""),
            "intent_keywords": meta.get("intent_keywords", []),
            "steps": steps,
            "filepath": filepath
        }

    def find_matching_skill(self, goal: str) -> Optional[Dict[str, Any]]:
        """
        Check if any registered Markdown SKILL.md matches the task prompt/goal.
        """
        self._load_skills()
        clean_goal = goal.strip().lower()

        for skill in self.skills:
            keywords = skill.get("intent_keywords", [])
            for kw in keywords:
                if isinstance(kw, str) and kw.lower() in clean_goal:
                    logger.info(f"🎯 [Skill Engine] Found matching learned SKILL.md: '{skill.get('name')}' (Keyword: '{kw}')")
                    return skill

            skill_name = skill.get("name", "").lower()
            if skill_name and (skill_name in clean_goal or clean_goal in skill_name):
                logger.info(f"🎯 [Skill Engine] Found matching learned SKILL.md: '{skill.get('name')}'")
                return skill

        return None

    def create_skill_from_execution(self, goal: str, history: List[Dict[str, Any]], self_healed: bool = False) -> Optional[Dict[str, Any]]:
        """
        Synthesize or update a formatted SKILL.md markdown file from a successful execution trajectory.
        """
        if not history:
            return None

        steps = []
        intent_keywords = set()

        words = re.findall(r"[\u4e00-\u9fa5]+|[a-zA-Z0-9]+", goal)
        for w in words:
            if len(w) > 1 and w.lower() not in ["幫我", "請", "打開", "執行", "open", "the"]:
                intent_keywords.add(w.lower())
        intent_keywords.add(goal.strip().lower())

        for idx, step_info in enumerate(history, 1):
            plan = step_info.get("plan", {})
            action = plan.get("action")
            if action in ["finish"]:
                continue

            target_text = plan.get("target_text", "")
            coords = plan.get("coordinates")
            bundle_id = plan.get("bundle_id")

            if target_text:
                intent_keywords.add(target_text.lower())

            steps.append({
                "step": idx,
                "action": action,
                "target_text": target_text,
                "coordinates": coords,
                "bundle_id": bundle_id,
                "thought": plan.get("thought", "")
            })

        if not steps:
            return None

        slug = re.sub(r"[^\w\u4e00-\u9fa5]+", "_", goal.strip().lower()).strip("_")
        if not slug:
            slug = f"skill_{int(datetime.now().timestamp())}"

        skill_dir = os.path.join(self.skills_dir, slug)
        os.makedirs(skill_dir, exist_ok=True)
        filepath = os.path.join(skill_dir, "SKILL.md")

        # Format SKILL.md content
        kw_str = "\n".join([f"  - {kw}" for kw in intent_keywords])
        steps_md = ""
        for s in steps:
            steps_md += f"### Step {s['step']}\n"
            steps_md += f"- **Action**: {s['action']}\n"
            steps_md += f"- **Target Text**: {s['target_text']}\n"
            steps_md += f"- **Target App Bundle**: {s['bundle_id'] or 'None'}\n"
            steps_md += f"- **Coordinates**: {json.dumps(s['coordinates']) if s['coordinates'] else 'None'}\n"
            steps_md += f"- **Thought**: {s['thought']}\n\n"

        status_str = " (Self-Healed)" if self_healed else ""
        md_content = f"""---
name: {slug}
description: Auto-generated Skill for task goal '{goal}'{status_str}
intent_keywords:
{kw_str}
self_healed: {str(self_healed).lower()}
updated_at: {datetime.now().isoformat()}
---

# Skill: {goal}

## Execution Steps

{steps_md}
"""

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(md_content)
            if self_healed:
                logger.info(f"🔄 [Self-Healing RPA] Automatically repaired & updated Markdown Skill: skills/{slug}/SKILL.md")
            else:
                logger.info(f"✨ [Skill Engine] Automatically generated & saved Markdown Skill: skills/{slug}/SKILL.md")
            return {"name": slug, "filepath": filepath, "steps": steps, "self_healed": self_healed}
        except Exception as e:
            logger.error(f"Failed to save SKILL.md file: {e}")
            return None

