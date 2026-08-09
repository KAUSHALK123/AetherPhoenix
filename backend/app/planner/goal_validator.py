import logging
from typing import List, Tuple

from shared.contracts.planner import Goal, IntentCategory

logger = logging.getLogger(__name__)


class GoalValidator:
    """
    Validates goal structures and raw request texts for safety, completeness,
    clarity, and adherence to system capability boundaries.
    """

    PROHIBITED_KEYWORDS = [
        "hack a bank",
        "delete windows",
        "destroy system",
        "steal data",
        "wipe disk",
        "format c:",
        "bypass password",
        "malware",
        "ransomware",
    ]

    VAGUE_TERMS = ["stuff", "do something", "thing", "asdf", "test1234", "whatever"]

    def validate_raw_request(self, text: str) -> Tuple[bool, List[str]]:
        """
        Validates raw request text before goal extraction.
        """
        errors = []
        cleaned = text.strip()

        if not cleaned:
            errors.append("Goal request message cannot be empty.")
            return False, errors

        if len(cleaned) < 3:
            errors.append(
                "Goal request message is too short to extract meaningful objectives."
            )
            return False, errors

        lower_text = cleaned.lower()
        for prohibited in self.PROHIBITED_KEYWORDS:
            if prohibited in lower_text:
                errors.append(
                    f"Request violates safety policies: '{prohibited}' is prohibited."
                )
                return False, errors

        for vague in self.VAGUE_TERMS:
            if cleaned.lower() == vague:
                errors.append(f"Request is too ambiguous or vague: '{cleaned}'.")
                return False, errors

        return True, errors

    def validate_goal_node(self, goal: Goal) -> Tuple[bool, List[str]]:
        """
        Validates a single Goal object for required attributes and completeness.
        """
        errors = []

        if not goal.title or not goal.title.strip():
            errors.append("Goal title cannot be empty.")

        if not goal.description or not goal.description.strip():
            errors.append("Goal description cannot be empty.")

        if goal.category == IntentCategory.UNKNOWN and not goal.description.strip():
            errors.append("Goal has unknown intent and description lacks detail.")

        is_valid = len(errors) == 0
        return is_valid, errors

    def validate_hierarchy(self, root_goal: Goal) -> Tuple[bool, List[str]]:
        """
        Validates an entire Goal hierarchy recursively.
        """
        all_errors = []

        node_valid, node_errors = self.validate_goal_node(root_goal)
        if not node_valid:
            all_errors.extend(node_errors)

        for child in root_goal.sub_goals:
            if child.parent_id != root_goal.goal_id:
                all_errors.append(
                    f"Sub-goal '{child.title}' has invalid parent_id "
                    f"'{child.parent_id}'. Expected '{root_goal.goal_id}'."
                )

            child_valid, child_errors = self.validate_hierarchy(child)
            if not child_valid:
                all_errors.extend(child_errors)

        return len(all_errors) == 0, all_errors
