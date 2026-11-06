"""
Loads and parses semantic layer definitions for prompt context.
"""

import os
import yaml
from typing import Dict, Any, List

DEFAULT_SEMANTIC_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config",
    "semantic_layer.yaml"
)


class SemanticLayer:
    def __init__(self, config_path: str = DEFAULT_SEMANTIC_PATH):
        self.config_path = config_path
        self.data = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_path):
            return {"entities": {}, "relationships": [], "metrics": {}}
        with open(self.config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    @property
    def metrics(self) -> Dict[str, Any]:
        return self.data.get("metrics", {})

    @property
    def entities(self) -> Dict[str, Any]:
        return self.data.get("entities", {})

    @property
    def relationships(self) -> List[Dict[str, Any]]:
        return self.data.get("relationships", [])

    def get_prompt_context(self) -> str:
        """
        Formats semantic metrics, business rules, and synonyms into a clean Markdown block
        for the LLM prompt.
        """
        lines = [
            "### Enterprise Business Metrics & Semantic Rules:",
            "Use these verified business formulas and definitions to avoid semantic errors:",
            ""
        ]

        # Metrics
        for key, metric in self.metrics.items():
            label = metric.get("label", key)
            desc = metric.get("description", "")
            formula = metric.get("formula", "")
            rule = metric.get("business_rule", "")

            lines.append(f"- **{label}** (`{key}`):")
            lines.append(f"  * Description: {desc}")
            if formula:
                lines.append(f"  * Formula / Logic: `{formula}`")
            if rule:
                lines.append(f"  * Critical Business Rule: {rule}")

        lines.append("")
        lines.append("### Table Join Guide & Entity Synonyms:")
        for entity_name, details in self.entities.items():
            synonyms = ", ".join(f"'{s}'" for s in details.get("synonyms", []))
            lines.append(f"- Table `{details.get('table', entity_name)}`: {details.get('description', '')}")
            if synonyms:
                lines.append(f"  * Common Synonyms: {synonyms}")

        if self.relationships:
            lines.append("")
            lines.append("### Recommended Join Paths:")
            for rel in self.relationships:
                lines.append(f"- {rel.get('from')} -> {rel.get('to')}: `{rel.get('join_hint', '')}`")

        lines.append("")
        return "\n".join(lines)
