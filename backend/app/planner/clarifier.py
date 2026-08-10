import logging
from typing import List

from shared.contracts.planner import (
    ClarificationResult,
    IntentCategory,
    UserRequirement,
)

logger = logging.getLogger(__name__)


class ClarificationEngine:
    """
    Evaluates UserRequirements to detect missing information.
    If information is missing, it generates a clarification question.
    This strictly prevents incomplete data from proceeding to the planning phase.
    """

    def detect_missing_info(self, requirement: UserRequirement) -> List[str]:
        """
        Analyzes the requirement to find missing fields.
        """
        missing_fields = []
        if requirement.intent == IntentCategory.UNKNOWN:
            missing_fields.append("intent")

        if not requirement.requirements:
            missing_fields.append("requirements")
            
        # Detect vague file organization requests
        req_text = " ".join(requirement.requirements).lower()
        if "organize" in req_text and "categoriz" not in req_text and "sort" not in req_text:
            missing_fields.append("categorization_strategy")

        return missing_fields

    def generate_question(self, missing_fields: List[str]) -> str:
        """
        Generates a contextual follow-up question based on what's missing.
        """
        if not missing_fields:
            return ""

        if "intent" in missing_fields and "requirements" in missing_fields:
            return (
                "I'm not quite sure what you'd like me to do. "
                "Could you provide more details?"
            )
        elif "intent" in missing_fields:
            return (
                "Could you clarify the main goal of your request? "
                "I need to know what kind of action to take."
            )
        elif "requirements" in missing_fields:
            return (
                "I understand the general goal, but could you specify "
                "exactly what you need?"
            )
        elif "categorization_strategy" in missing_fields:
            return (
                "How would you like the files categorized?"
            )

        return "Could you provide more context for your request?"

    def evaluate_requirement(self, requirement: UserRequirement) -> ClarificationResult:
        """
        Evaluates the requirement and returns a result indicating whether
        clarification is needed, along with the generated question.
        """
        logger.info("Evaluating UserRequirement for clarification...")
        missing_fields = self.detect_missing_info(requirement)

        if missing_fields:
            question = self.generate_question(missing_fields)
            return ClarificationResult(
                needs_clarification=True,
                question=question,
                missing_fields=missing_fields,
            )

        return ClarificationResult(
            needs_clarification=False, question=None, missing_fields=[]
        )
