import logging
from typing import Any, Dict, List, Optional

from shared.contracts.planner import (
    ClarificationResult,
    IntentCategory,
    UserRequirement,
)

from app.planner.normalizer import (
    extract_entities,
    is_diagnostic_terminal_command,
    normalize_text,
)

logger = logging.getLogger(__name__)


class ClarificationEngine:
    """Evaluates UserRequirements and execution context to detect missing information.

    Follows the principle: Ask the user ONLY when important information is missing.
    Examples:
      - Multiple projects are detected.
      - Repository is not identified.
      - Destination folder is ambiguous.
      - The requested operation could cause data loss.
    Never asks unnecessary questions when request or context provides what is needed.
    """

    def _is_file_organization_intent(self, text: str) -> bool:
        lower = normalize_text(text).lower()
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
                "pdf",
                "pdfs",
            ]
        )
        return (has_action and has_file_kw) or ("organizer" in lower)

    def detect_missing_info(
        self,
        requirement: UserRequirement,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Analyzes the requirement and context to find missing critical fields."""
        missing_fields: List[str] = []
        ctx = context or {}
        req_text = (
            " ".join(requirement.requirements).lower()
            if requirement.requirements
            else ""
        )
        norm_text = normalize_text(req_text)
        lower_norm = norm_text.lower()

        # 0. Direct diagnostic commands never need clarification
        if is_diagnostic_terminal_command(lower_norm):
            return []

        # 1. Check for data loss risk requiring explicit confirmation
        entities = extract_entities(norm_text, ctx)
        if entities.get("has_data_loss_risk") and not ctx.get("confirmed_data_loss"):
            missing_fields.append("data_loss_confirmation")
            return missing_fields

        # 2. Check for multiple projects detected
        if ctx.get("multiple_projects") or len(ctx.get("detected_projects", [])) > 1:
            if not ctx.get("selected_project"):
                missing_fields.append("project_selection")
                return missing_fields

        # 3. Check for GitHub / Repository operations where repository is not identified
        is_git_request = any(
            k in lower_norm
            for k in [
                "github repository",
                "github repo",
                "git repository",
                "git repo",
                "remote repository",
            ]
        )
        if is_git_request:
            repo_identified = (
                entities.get("repository") is not None
                or ctx.get("repository") is not None
                or ctx.get("repo") is not None
                or "aetherphoenix" in lower_norm
                or "kaushalk123" in lower_norm
            )
            # If explicit clarification request or ambiguous remote repository requested
            if not repo_identified and ctx.get("require_explicit_repo"):
                missing_fields.append("repository")
                return missing_fields

        # 4. Check for file organization intent
        if self._is_file_organization_intent(norm_text):
            has_folder = any(
                f in lower_norm
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
            ) or bool(ctx.get("source_folder"))

            has_criteria = any(
                c in lower_norm
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
                    "pdfs",
                    "images",
                    "videos",
                    "docs",
                    "sort by",
                ]
            ) or bool(ctx.get("organization_criteria"))

            if not has_folder:
                missing_fields.append("source_folder")
            if not has_criteria:
                missing_fields.append("organization_criteria")

            # Check if destination folder is explicitly ambiguous
            if ctx.get("ambiguous_destination"):
                missing_fields.append("destination_folder")

            return missing_fields

        if requirement.intent == IntentCategory.UNKNOWN:
            missing_fields.append("intent")

        if not requirement.requirements:
            missing_fields.append("requirements")

        return missing_fields

    def generate_question(self, missing_fields: List[str]) -> str:
        """Generates a contextual follow-up question based on what is missing."""
        if not missing_fields:
            return ""

        if "data_loss_confirmation" in missing_fields:
            return (
                "Warning: The requested operation could cause permanent data loss. "
                "Please confirm if you want to proceed and verify the target path."
            )

        if "project_selection" in missing_fields:
            return (
                "Multiple projects were detected in your workspace. "
                "Which project would you like to open and run?"
            )

        if "repository" in missing_fields:
            return (
                "Which GitHub repository would you like to inspect? "
                "Please provide the repository name (e.g., owner/repo) or confirm using the current local repository."
            )

        if "destination_folder" in missing_fields:
            return "The destination folder is ambiguous. Where would you like the organized files to be moved?"

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

    def evaluate_requirement(
        self,
        requirement: UserRequirement,
        context: Optional[Dict[str, Any]] = None,
    ) -> ClarificationResult:
        """Evaluates the requirement and returns clarification status and question."""
        logger.info("Evaluating UserRequirement for clarification...")
        missing_fields = self.detect_missing_info(requirement, context=context)

        if missing_fields:
            question = self.generate_question(missing_fields)
            options = None
            if "data_loss_confirmation" in missing_fields:
                options = ["Cancel operation", "Proceed with execution"]
            elif "project_selection" in missing_fields:
                options = (context or {}).get(
                    "detected_projects", ["Project 1", "Project 2"]
                )
            elif "repository" in missing_fields:
                options = [
                    "Current local repository",
                    "Specify repository URL / owner/repo",
                ]
            elif (
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
