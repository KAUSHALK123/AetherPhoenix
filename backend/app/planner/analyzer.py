import logging
from typing import List

from shared.contracts.planner import IntentCategory, PlannerRequest, UserRequirement

logger = logging.getLogger(__name__)


class RequirementAnalyzer:
    """
    Analyzes incoming user requests to determine intent, constraints, and requirements.
    This acts as the first stage of the planning pipeline, before any tasks
    are generated.
    """

    def analyze_intent(self, text: str) -> IntentCategory:
        """
        Determines the primary intent of the user's request.
        Currently uses a mock heuristic based on keywords.
        """
        lower_text = text.lower()
        if any(
            word in lower_text
            for word in [
                "create",
                "add",
                "update",
                "modify",
                "delete",
                "type",
                "open",
                "launch",
                "click",
                "run",
                "exec",
                "execute",
                "ipconfig",
                "powershell",
                "terminal",
                "cmd",
                "install",
            ]
        ):
            return IntentCategory.SYSTEM_MODIFICATION
        elif any(
            word in lower_text
            for word in [
                "get",
                "find",
                "search",
                "read",
                "show",
                "browse",
                "extract",
                "fetch",
                "check",
            ]
        ):
            return IntentCategory.DATA_RETRIEVAL
        elif any(
            word in lower_text
            for word in ["write", "generate", "draft", "build", "ppt", "pdf", "slides"]
        ):
            return IntentCategory.CONTENT_GENERATION
        return IntentCategory.UNKNOWN

    def extract_requirements(self, text: str) -> List[str]:
        """
        Extracts specific actionable requirements from the text.
        (Mock implementation).
        """
        if not text.strip():
            return []
        # A real implementation would use NLP. Here we just return the cleaned text
        # as a single requirement.
        return [text.strip()]

    def detect_constraints(self, text: str) -> List[str]:
        """
        Identifies any limitations or constraints applied to the request.
        """
        constraints = []
        lower_text = text.lower()
        if "fast" in lower_text or "quick" in lower_text:
            constraints.append("performance: high")
        if "safe" in lower_text or "secure" in lower_text:
            constraints.append("security: strict")
        if "no internet" in lower_text or "offline" in lower_text:
            constraints.append("network: offline_only")
        return constraints

    def analyze_request(self, request: PlannerRequest) -> UserRequirement:
        """
        Fully parses the PlannerRequest into a structured UserRequirement.
        """
        logger.info(f"Analyzing request for session {request.session_id}")

        intent = self.analyze_intent(request.message)
        requirements = self.extract_requirements(request.message)
        constraints = self.detect_constraints(request.message)

        return UserRequirement(
            intent=intent,
            requirements=requirements,
            constraints=constraints,
            category=intent.value,
        )
