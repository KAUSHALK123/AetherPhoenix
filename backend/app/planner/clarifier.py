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

    def _is_file_organization_intent(self, text: str) -> bool:
        lower = text.lower()
        has_action = any(
            w in lower
            for w in [
                "organize",
                "sort",
                "clean up",
                "cleanup",
                "local file organizer",
                "file organizer",
                "categorize",
                "group files",
            ]
        )
        has_file_kw = any(
            w in lower
            for w in [
                "file",
                "files",
                "folder",
                "folders",
                "directory",
                "directories",
                "downloads",
                "desktop",
                "docs",
                "documents",
                "organizer",
            ]
        )
        return (has_action and has_file_kw) or ("organizer" in lower)

    def detect_missing_info(self, requirement: UserRequirement) -> List[str]:
        """
        Analyzes the requirement to find missing fields.
        """
        missing_fields = []
        req_text = (
            " ".join(requirement.requirements).lower()
            if requirement.requirements
            else ""
        )

        # Priority 1: Check for file organization intent
        if self._is_file_organization_intent(req_text):
            has_folder = any(
                f in req_text
                for f in [
                    "download",
                    "downloads",
                    "desktop",
                    "documents",
                    "docs",
                    "pictures",
                    "videos",
                    "music",
                    ":\\",
                    ":/",
                    "/home",
                    "/user",
                    "target directory",
                    "source directory",
                ]
            )
            has_criteria = any(
                c in req_text
                for c in [
                    "by file type",
                    "by type",
                    "by extension",
                    "file type",
                    "extension",
                    "by date",
                    "by size",
                    "date",
                    "size",
                    "alphabetical",
                    "by category",
                    "categoriz",
                    "pdf",
                    "images",
                    "videos",
                    "docs",
                    "sort by",
                ]
            )

            if not has_folder:
                missing_fields.append("source_folder")
            if not has_criteria:
                missing_fields.append("organization_criteria")

            # If both folder and criteria are provided, no clarification needed!
            return missing_fields

        if requirement.intent == IntentCategory.UNKNOWN:
            missing_fields.append("intent")

        if not requirement.requirements:
            missing_fields.append("requirements")

        return missing_fields

    def generate_question(self, missing_fields: List[str]) -> str:
        """
        Generates a contextual follow-up question based on what's missing.
        """
        if not missing_fields:
            return ""

        # File organization clarification
        if (
            "source_folder" in missing_fields
            or "organization_criteria" in missing_fields
        ):
            return (
                "To organize your files, please clarify:\n"
                "- Which folder would you like to organize? (Downloads, Desktop, custom path)\n"
                "- How should files be organized? (By file type / extension, by date, by size)\n"
                "- Should files be moved or copied?"
            )

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
            options = None
            if (
                "source_folder" in missing_fields
                or "organization_criteria" in missing_fields
            ):
                options = [
                    "Organize Downloads by file type",
                    "Organize Desktop by category",
                    "Sort files by date created",
                ]
            return ClarificationResult(
                needs_clarification=True,
                question=question,
                missing_fields=missing_fields,
                options=options,
            )

        return ClarificationResult(
            needs_clarification=False, question=None, missing_fields=[], options=None
        )
