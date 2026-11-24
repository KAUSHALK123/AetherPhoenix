"""Natural language text normalization and entity extraction for AetherPhoenix Planner.

Provides typo correction, grammatical relaxation, domain keyword normalization,
and structured entity extraction to enable intelligent tool routing.
"""

import difflib
import re
from typing import Any, Dict, List, Optional, Set

# Explicit dictionary of common typos, phonetic misspellings, and shortcuts
TYPO_MAP: Dict[str, str] = {
    # Actions
    "reseach": "research",
    "reaserch": "research",
    "reserch": "research",
    "presntation": "presentation",
    "presentaion": "presentation",
    "presenation": "presentation",
    "preso": "presentation",
    "prep": "prepare",
    "opn": "open",
    "prject": "project",
    "proejct": "project",
    "projct": "project",
    "dowlnoad": "downloads",
    "dowlnoads": "downloads",
    "downlaods": "downloads",
    "downlod": "download",
    "downlods": "downloads",
    "dnload": "download",
    "orgnize": "organize",
    "organise": "organize",
    "organiz": "organize",
    "inspct": "inspect",
    "inspec": "inspect",
    "chck": "check",
    "fnd": "find",
    "gthub": "github",
    "gihub": "github",
    "repositry": "repository",
    "repostory": "repository",
    "trminal": "terminal",
    "trmnl": "terminal",
    "pwrshl": "powershell",
    "pwoershell": "powershell",
    "pwsh": "powershell",
    "ipconfg": "ipconfig",
    "ipconfing": "ipconfig",
    "ipconifg": "ipconfig",
    "whomi": "whoami",
    "hostnam": "hostname",
    "netstat": "netstat",
    "systminfo": "systeminfo",
    "nd": "and",
    "wat": "what",
    "wats": "what is",
    "whats": "what is",
    "plz": "please",
    "pls": "please",
    "vscod": "vscode",
    "vs-code": "vscode",
    "framwork": "framework",
    "framewrk": "framework",
    "frameworks": "frameworks",
}

# Domain vocabulary for fuzzy matching (words >= 4 chars)
DOMAIN_VOCABULARY: Set[str] = {
    "research",
    "presentation",
    "powerpoint",
    "slides",
    "document",
    "project",
    "organize",
    "downloads",
    "desktop",
    "directory",
    "folder",
    "terminal",
    "powershell",
    "command",
    "execute",
    "inspect",
    "github",
    "repository",
    "commit",
    "branch",
    "diff",
    "changes",
    "history",
    "framework",
    "frameworks",
    "ipconfig",
    "whoami",
    "hostname",
    "systeminfo",
    "browser",
    "export",
    "search",
    "extract",
}

# Known single or compound terminal inspection commands (Read-only / Diagnostic)
DIAGNOSTIC_TERMINAL_COMMANDS: Set[str] = {
    "ipconfig",
    "ping",
    "whoami",
    "hostname",
    "netstat",
    "systeminfo",
    "tracert",
    "nslookup",
    "route",
    "arp",
    "uptime",
    "dir",
    "ls",
    "get-process",
    "get-service",
}

# Dangerous / data-loss commands and keywords
DATA_LOSS_KEYWORDS: Set[str] = {
    "delete all",
    "remove all",
    "drop table",
    "drop database",
    "format c:",
    "format d:",
    "format drive",
    "wipe drive",
    "wipe disk",
    "rm -rf",
    "rmdir /s",
    "del /f /s /q",
}


def normalize_text(text: str) -> str:
    """Normalizes text by correcting common typos, slang, and whitespace.

    Preserves URLs, command arguments, and casing-sensitive identifiers.
    """
    if not text or not text.strip():
        return ""

    tokens = text.strip().split()
    normalized_tokens: List[str] = []

    for token in tokens:
        # Preserve URLs, paths, or command flags
        if (
            "://" in token
            or token.startswith("/")
            or token.startswith("-")
            or "\\" in token
        ):
            normalized_tokens.append(token)
            continue

        clean_token = re.sub(r"^[^\w]+|[^\w]+$", "", token).lower()

        if clean_token in TYPO_MAP:
            replacement = TYPO_MAP[clean_token]
            # Retain surrounding punctuation
            prefix = token[: len(token) - len(token.lstrip("^.,;!?'\"()[]{}"))]
            suffix = token[len(token.rstrip("^.,;!?'\"()[]{}")) :]
            normalized_tokens.append(f"{prefix}{replacement}{suffix}")
            continue

        # Fuzzy matching against domain vocabulary if word length >= 5
        if len(clean_token) >= 5 and clean_token not in DOMAIN_VOCABULARY:
            matches = difflib.get_close_matches(
                clean_token, DOMAIN_VOCABULARY, n=1, cutoff=0.82
            )
            if matches:
                prefix = token[: len(token) - len(token.lstrip("^.,;!?'\"()[]{}"))]
                suffix = token[len(token.rstrip("^.,;!?'\"()[]{}")) :]
                normalized_tokens.append(f"{prefix}{matches[0]}{suffix}")
                continue

        normalized_tokens.append(token)

    return " ".join(normalized_tokens)


def is_diagnostic_terminal_command(text: str) -> Optional[str]:
    """Detects whether text is a direct read-only terminal/diagnostic command.

    Returns the canonical command name if recognized, else None.
    """
    cleaned = normalize_text(text).strip().lower()

    # Direct match or query match like 'whats my ipconfig' or 'check ipconfig' or 'run ipconfig'
    for cmd in DIAGNOSTIC_TERMINAL_COMMANDS:
        # Exact match or with flags e.g. "ipconfig /all", "ping 8.8.8.8"
        if cleaned == cmd or cleaned.startswith(f"{cmd} "):
            return cmd
        # Natural phrasing e.g. "whats my ipconfig", "run ipconfig", "check my ipconfig"
        if re.search(r"\b" + re.escape(cmd) + r"\b", cleaned):
            # Exclude if explicitly creating a presentation or document about it
            if not any(
                w in cleaned
                for w in [
                    "presentation",
                    "ppt",
                    "pdf",
                    "slides",
                    "deck",
                    "generate",
                    "create",
                ]
            ):
                return cmd

    return None


def extract_entities(
    text: str, context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Extracts semantic entities, applications, targets, and parameters from text."""
    normalized = normalize_text(text)
    lower = normalized.lower()
    ctx = context or {}

    # Target Application
    target_app = None
    if any(
        k in lower for k in ["vs code", "vscode", "visual studio code", "open code"]
    ):
        target_app = "Visual Studio Code"
    elif "notepad" in lower:
        target_app = "Notepad"
    elif "calculator" in lower or "calc" in lower:
        target_app = "Calculator"

    # Repository
    repo = None
    repo_match = re.search(r"([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)", text)
    if repo_match:
        repo = repo_match.group(1)
    elif ctx.get("repository"):
        repo = ctx["repository"]
    elif ctx.get("repo"):
        repo = ctx["repo"]

    # File extensions
    file_extensions = []
    for ext in [
        ".pdf",
        ".pptx",
        ".ppt",
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".json",
        ".csv",
        ".docx",
        ".txt",
    ]:
        if (
            ext in lower
            or f" {ext[1:]} " in f" {lower} "
            or f" {ext[1:]}s " in f" {lower} "
        ):
            file_extensions.append(ext)

    # Directories
    directories = []
    if "download" in lower or "downloads" in lower:
        directories.append("Downloads")
    if "desktop" in lower:
        directories.append("Desktop")
    if "document" in lower or "documents" in lower or "docs" in lower:
        directories.append("Documents")
    for drive in ["c:", "d:", "e:"]:
        if drive in lower:
            directories.append(drive.upper())

    # Data loss risk
    has_data_loss_risk = any(k in lower for k in DATA_LOSS_KEYWORDS)

    # Diagnostic command
    diag_cmd = is_diagnostic_terminal_command(text)

    return {
        "normalized_text": normalized,
        "target_app": target_app,
        "repository": repo,
        "file_extensions": file_extensions,
        "directories": directories,
        "has_data_loss_risk": has_data_loss_risk,
        "diagnostic_command": diag_cmd,
    }
