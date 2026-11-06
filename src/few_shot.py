"""
Few-Shot Example Manager for NL2SQL Agent.
Loads validated SQL gold examples and injects them into the prompt to dramatically
improve exact-match SQL accuracy and domain alignment.
"""

import os
import yaml
from typing import Dict, Any, List

DEFAULT_FEW_SHOT_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "few_shot_examples.yaml"
)


class FewShotManager:
    def __init__(self, config_path: str = DEFAULT_FEW_SHOT_PATH):
        self.config_path = config_path
        self.examples = self._load_examples()

    def _load_examples(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.config_path):
            return []
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data.get("examples", [])

    def get_prompt_context(self, limit: int = 4) -> str:
        """
        Formats gold SQL examples into an exemplary few-shot prompt section.
        """
        selected = self.examples[:limit]
        if not selected:
            return ""

        lines = [
            "### Validated Gold-Standard SQL Examples:",
            "Follow these verified query patterns for SQLite formatting, joins, and aggregations:",
            ""
        ]

        for idx, ex in enumerate(selected, 1):
            lines.append(f"#### Example {idx}:")
            lines.append(f"User Question: \"{ex.get('question')}\"")
            if ex.get("intent"):
                lines.append(f"Business Intent: {ex.get('intent')}")
            if ex.get("thought"):
                lines.append(f"Reasoning / Logic: {ex.get('thought')}")
            lines.append("Verified SQLite Query:")
            lines.append("```sql")
            lines.append(ex.get("sql", "").strip())
            lines.append("```")
            lines.append("")

        return "\n".join(lines)
