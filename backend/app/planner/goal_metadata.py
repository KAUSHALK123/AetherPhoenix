import datetime
import logging
from typing import Any, Dict, List

from shared.contracts.planner import Goal, IntentCategory

logger = logging.getLogger(__name__)


class GoalMetadataGenerator:
    """
    Enriches extracted goals with metadata including confidence scores,
    timestamps, tags, priority estimates, and risk evaluations.
    """

    DOMAIN_KEYWORDS = {
        "browser": ["web", "browse", "url", "site", "html", "http", "download"],
        "desktop": ["window", "app", "application", "desktop", "click", "screen"],
        "content": [
            "ppt",
            "presentation",
            "slide",
            "pdf",
            "doc",
            "report",
            "write",
            "draft",
        ],
        "coding": ["code", "python", "git", "repo", "commit", "bug", "refactor"],
        "system": ["file", "folder", "directory", "process", "powershell", "setting"],
        "research": ["research", "search", "find", "analyze", "summarize", "info"],
    }

    def compute_confidence_score(self, goal: Goal) -> float:
        """
        Computes a confidence score between 0.0 and 1.0 for an extracted goal.
        """
        score = 0.5  # Base score

        # Intent clarity bonus
        if goal.category != IntentCategory.UNKNOWN:
            score += 0.2

        # Expected outcomes bonus
        if goal.expected_outcomes:
            score += 0.15

        # Sub-goals structure bonus
        if goal.sub_goals:
            score += 0.1

        # Description length bonus
        words = goal.description.split()
        if len(words) >= 5:
            score += 0.05

        return min(1.0, round(score, 2))

    def detect_domain_tags(self, text: str) -> List[str]:
        """
        Extracts domain tags based on keyword matching.
        """
        tags = []
        lower_text = text.lower()

        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            if any(kw in lower_text for kw in keywords):
                tags.append(domain)

        if not tags:
            tags.append("general")

        return tags

    def estimate_risk_level(self, goal: Goal) -> str:
        """
        Estimates the risk level for a goal.
        """
        lower_text = (goal.title + " " + goal.description).lower()

        if any(
            word in lower_text
            for word in ["registry", "driver", "format", "wipe", "kernel"]
        ):
            return "critical"
        elif any(
            word in lower_text for word in ["delete", "remove", "kill", "uninstall"]
        ):
            return "high"
        elif any(
            word in lower_text for word in ["modify", "update", "write", "install"]
        ):
            return "medium"
        elif any(word in lower_text for word in ["create", "generate", "draft"]):
            return "low"

        return "safe"

    def generate_goal_metadata(self, goal: Goal) -> Dict[str, Any]:
        """
        Generates a comprehensive metadata dictionary for a Goal node.
        """
        text = goal.title + " " + goal.description
        confidence = self.compute_confidence_score(goal)
        tags = self.detect_domain_tags(text)
        risk = self.estimate_risk_level(goal)

        return {
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "confidence_score": confidence,
            "domain_tags": tags,
            "estimated_risk": risk,
            "sub_goal_count": len(goal.sub_goals),
            "outcome_count": len(goal.expected_outcomes),
        }

    def enrich_goal(self, goal: Goal) -> Goal:
        """
        Recursively enriches a goal node and all child sub-goals with metadata.
        """
        goal.metadata.update(self.generate_goal_metadata(goal))

        for child in goal.sub_goals:
            self.enrich_goal(child)

        return goal
