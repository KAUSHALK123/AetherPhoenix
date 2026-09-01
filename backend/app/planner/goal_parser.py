import logging
import re
from typing import List, Tuple

from shared.contracts.planner import GoalPriority, IntentCategory

logger = logging.getLogger(__name__)


class GoalParser:
    """
    Parses natural language requests into structured primary objectives,
    sub-goals, and expected outcomes without generating executable tasks.
    """

    SUBGOAL_DELIMITERS = [
        r";\s*",
        r"\n+",
        r",\s*",
        (
            r"\b(?:then|and then|after that|first|secondly|second|"
            r"thirdly|third|finally|also|next|and)\b"
        ),
        r"\d+\.\s+",
        r"[-*]\s+",
    ]

    OUTCOME_KEYWORDS = {
        "create": "Created artifact or document",
        "generate": "Generated output",
        "write": "Written content or file",
        "build": "Built project or component",
        "find": "Retrieved data or information",
        "search": "Search results",
        "get": "Obtained resource",
        "fetch": "Fetched data",
        "read": "Read content",
        "update": "Updated system configuration or state",
        "modify": "Modified target entity",
        "delete": "Removed target resource",
        "remove": "Removed target resource",
        "fix": "Resolved issue or defect",
        "organize": "Organized structure",
        "run": "Executed command or script",
        "exec": "Executed command",
        "execute": "Executed command",
        "open": "Opened application or target path",
        "launch": "Launched application",
        "extract": "Extracted target content or text",
    }

    def parse_intent(self, text: str) -> IntentCategory:
        """
        Determines the IntentCategory of a request based on linguistic markers.
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
                "remove",
                "fix",
                "install",
                "run",
                "exec",
                "execute",
                "open",
                "launch",
            ]
        ):
            return IntentCategory.SYSTEM_MODIFICATION
        elif any(
            word in lower_text
            for word in ["get", "find", "search", "read", "show", "fetch", "check", "extract"]
        ):
            return IntentCategory.DATA_RETRIEVAL
        elif any(
            word in lower_text
            for word in ["write", "generate", "draft", "summarize", "build"]
        ):
            return IntentCategory.CONTENT_GENERATION
        return IntentCategory.UNKNOWN

    def parse_priority(self, text: str) -> GoalPriority:
        """
        Infers priority from urgency keywords.
        """
        lower_text = text.lower()
        if any(
            word in lower_text
            for word in ["urgent", "asap", "critical", "immediately", "emergency"]
        ):
            return GoalPriority.CRITICAL
        elif any(
            word in lower_text
            for word in ["high priority", "important", "fast", "quick"]
        ):
            return GoalPriority.HIGH
        elif any(
            word in lower_text for word in ["low priority", "whenever", "eventually"]
        ):
            return GoalPriority.LOW
        return GoalPriority.MEDIUM

    def extract_subgoal_phrases(self, text: str) -> List[str]:
        """
        Splits text into sub-goal candidate phrases using conjunctions,
        delimiters, and list indicators.
        """
        pattern = "|".join(self.SUBGOAL_DELIMITERS)
        raw_chunks = re.split(pattern, text, flags=re.IGNORECASE)

        phrases = []
        for chunk in raw_chunks:
            cleaned = chunk.strip(" .,;-*\t\n")
            if cleaned and len(cleaned) > 2:
                phrases.append(cleaned)

        return phrases

    def extract_outcomes(self, text: str) -> List[str]:
        """
        Identifies expected outcomes from goal descriptions.
        """
        outcomes = []
        lower_text = text.lower()

        # Check for explicit file format outcomes
        file_formats = [
            "ppt",
            "pptx",
            "presentation",
            "slide",
            "slides",
            "pdf",
            "docx",
            "csv",
            "json",
            "report",
            "image",
            "screenshot",
            "log",
        ]
        for fmt in file_formats:
            if fmt in lower_text:
                outcomes.append(f"Generated {fmt.upper()} file/artifact")

        # Check verb-based outcomes
        for keyword, outcome_desc in self.OUTCOME_KEYWORDS.items():
            if re.search(r"\b" + keyword + r"\b", lower_text):
                outcomes.append(f"{outcome_desc} from '{keyword}' request")

        if not outcomes:
            outcomes.append("Successful goal execution outcome")

        # Remove duplicate outcome strings while preserving order
        unique_outcomes = []
        for outcome in outcomes:
            if outcome not in unique_outcomes:
                unique_outcomes.append(outcome)

        return unique_outcomes

    def parse_raw_goal(
        self, text: str
    ) -> Tuple[str, str, List[Tuple[str, str]], List[str]]:
        """
        Parses text into primary title, description, raw subgoals,
        and expected outcomes. Each subgoal is a (sub_title, sub_desc) tuple.
        """
        cleaned_text = text.strip()
        if not cleaned_text:
            return "", "", [], []

        # Primary title is derived from the first line or sentence
        lines = [line.strip() for line in cleaned_text.splitlines() if line.strip()]
        first_line = lines[0] if lines else cleaned_text

        # Truncate primary title to reasonable length if too long
        title = first_line if len(first_line) <= 80 else first_line[:77] + "..."
        description = cleaned_text

        # Extract sub-goal phrases
        subgoal_phrases = self.extract_subgoal_phrases(cleaned_text)

        subgoals_raw: List[Tuple[str, str]] = []

        # If multiple distinct sub-goal phrases exist, format them as sub-goals
        if len(subgoal_phrases) > 1:
            for idx, phrase in enumerate(subgoal_phrases, start=1):
                sub_title = phrase if len(phrase) <= 80 else phrase[:77] + "..."
                sub_desc = f"Sub-goal {idx}: {phrase}"
                subgoals_raw.append((sub_title, sub_desc))
        elif len(subgoal_phrases) == 1 and subgoal_phrases[0] != cleaned_text:
            phrase = subgoal_phrases[0]
            sub_title = phrase if len(phrase) <= 80 else phrase[:77] + "..."
            subgoals_raw.append((sub_title, f"Sub-goal 1: {phrase}"))

        outcomes = self.extract_outcomes(cleaned_text)

        return title, description, subgoals_raw, outcomes
