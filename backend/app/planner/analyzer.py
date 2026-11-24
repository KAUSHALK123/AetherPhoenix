import logging
from typing import List

from shared.contracts.planner import IntentCategory, PlannerRequest, UserRequirement

from app.planner.normalizer import (
    is_diagnostic_terminal_command,
    normalize_text,
)

logger = logging.getLogger(__name__)


class RequirementAnalyzer:
    """Analyzes incoming user requests to determine intent, constraints, and requirements.

    This acts as the first stage of the planning pipeline, before any tasks
    are generated.
    """

    def analyze_intent(self, text: str) -> IntentCategory:
        """Determines the primary intent of the user's request.

        Normalizes typos and recognizes diagnostic commands as data retrieval.
        """
        norm_text = normalize_text(text)
        lower_text = norm_text.lower()

        # 1. Direct diagnostic / network / terminal inspection commands are DATA_RETRIEVAL
        if is_diagnostic_terminal_command(lower_text):
            return IntentCategory.DATA_RETRIEVAL

        # 2. System modification / execution actions
        if any(
            word in lower_text
            for word in [
                "create",
                "add",
                "update",
                "modify",
                "delete",
                "organize",
                "sort",
                "clean up",
                "cleanup",
                "move",
                "copy",
                "group",
                "local file organizer",
                "file organizer",
                "type",
                "open",
                "launch",
                "click",
                "press",
                "submit",
                "tap",
                "select",
                "run",
                "exec",
                "execute",
                "powershell",
                "terminal",
                "cmd",
                "install",
            ]
        ):
            return IntentCategory.SYSTEM_MODIFICATION

        # 3. Data retrieval / inspection actions
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
                "list",
                "view",
                "inspect",
                "explore",
                "display",
                "what's in",
                "whats in",
                "what is in",
                "what folders",
                "what files",
                "tell me what",
                "tell me",
                "whats on",
                "what's on",
                "diff",
                "history",
            ]
        ):
            return IntentCategory.DATA_RETRIEVAL

        # 4. Content / deliverable generation actions
        elif any(
            word in lower_text
            for word in [
                "write",
                "generate",
                "draft",
                "build",
                "ppt",
                "pdf",
                "slides",
                "presentation",
            ]
        ):
            return IntentCategory.CONTENT_GENERATION

        return IntentCategory.UNKNOWN

    def extract_requirements(self, text: str) -> List[str]:
        """Extracts specific actionable requirements from the text."""
        norm = normalize_text(text).strip()
        if not norm:
            return []
        return [norm]

    def detect_constraints(self, text: str) -> List[str]:
        """Identifies any limitations or constraints applied to the request."""
        constraints = []
        lower_text = normalize_text(text).lower()
        if "fast" in lower_text or "quick" in lower_text:
            constraints.append("performance: high")
        if "safe" in lower_text or "secure" in lower_text:
            constraints.append("security: strict")
        if "no internet" in lower_text or "offline" in lower_text:
            constraints.append("network: offline_only")
        return constraints

    def analyze_request(self, request: PlannerRequest) -> UserRequirement:
        """Fully parses the PlannerRequest into a structured UserRequirement."""
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
