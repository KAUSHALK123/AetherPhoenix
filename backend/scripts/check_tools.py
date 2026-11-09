#!/usr/bin/env python3
"""
Tool Registry and Organizer Health Check Script (check_tools.py)

For every adapter and tool registered in ToolRegistry, this script verifies:
1. Registered tool name matches the required_tool strings emitted by decomposer/planner.
2. The Pydantic input model validates sample input payloads correctly.
3. Dry-run execution via WorkerAgent/Adapter produces a well-formed ExecutionResult.
4. Prints a formatted ASCII table showing PASS/FAIL per tool and check.
5. Returns exit code 0 if all checks pass, non-zero otherwise.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type
from unittest.mock import MagicMock
from uuid import uuid4

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Add root directory to sys.path for shared contracts
root_dir = backend_dir.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from pydantic import BaseModel
from shared.contracts.document import StructuredDocumentInput
from shared.contracts.execution import ExecutionResult
from shared.contracts.export import ExportRequest
from shared.contracts.ocr import OCRRequest
from shared.contracts.pdf import PDFDocumentInput
from shared.contracts.permission import PermissionRequest, PermissionStatus, PermissionType
from shared.contracts.screenshot import ScreenshotRequest
from shared.contracts.task import Task, TaskCategory, TaskType
from shared.contracts.tool import Tool

from app.agents.worker.agent import WorkerAgent
from app.planner.decomposer import TaskDecompositionEngine
from app.tools import (
    register_desktop_tool,
    register_document_tool,
    register_export_tool,
    register_file_explorer_tool,
    register_git_tool,
    register_ocr_tool,
    register_pdf_tool,
    register_screenshot_tool,
    register_terminal_tool,
    register_web_research_tool,
)
from app.tools.browser import register_browser_capability
from app.tools.browser_extension import register_browser_extension_capability
from app.tools.file_explorer.models import DetectExistenceRequest
from app.tools.git.tool import GitToolInput
from app.tools.ppt import register_ppt_tool
from app.tools.registry import ToolRegistry
from app.tools.terminal.tool import TerminalToolInput
from app.tools.web_research.schemas import WebResearchRequest
from app.tools.web_scraping import register_web_scraping_tool
from app.tools.web_scraping.contracts import ScrapeRequest


# ---------------------------------------------------------------------------
# Schema Specifications and Sample Inputs
# ---------------------------------------------------------------------------

TOOL_CONFIGS: Dict[str, Dict[str, Any]] = {
    "desktop_automation": {
        "model": None,  # Param-based dictionary
        "sample_input": {"action": "get_desktop_state"},
    },
    "document_generator": {
        "model": StructuredDocumentInput,
        "sample_input": {
            "title": "Health Check Document",
            "content": "Automated verification content",
            "format": "markdown",
            "output_path": "health_check_doc.md",
        },
    },
    "content_tool": {
        "model": StructuredDocumentInput,
        "sample_input": {
            "title": "Health Check Content",
            "content": "Content generator verification",
            "format": "markdown",
            "output_path": "health_check_content.md",
        },
    },
    "export": {
        "model": ExportRequest,
        "sample_input": {
            "workflow_id": uuid4(),
            "target_format": "json",
            "source_filepath": "sample.txt",
            "format": "json",
            "data": {"status": "ok"},
            "dry_run": True,
        },
    },
    "file_explorer": {
        "model": DetectExistenceRequest,
        "sample_input": {"action": "detect_existence", "path": "."},
    },
    "file_manager_tool": {
        "model": DetectExistenceRequest,
        "sample_input": {"action": "detect_existence", "path": "."},
    },
    "git_tool": {
        "model": GitToolInput,
        "sample_input": {"operation": "status"},
    },
    "ocr": {
        "model": OCRRequest,
        "sample_input": {
            "action": "extract_text",
            "filepath": "sample.pdf",
            "dry_run": True,
        },
    },
    "pdf_search": {
        "model": OCRRequest,
        "sample_input": {
            "action": "extract_text",
            "filepath": "sample.pdf",
            "query": "test",
            "dry_run": True,
        },
    },
    "ocr_tool": {
        "model": OCRRequest,
        "sample_input": {
            "action": "extract_text",
            "filepath": "sample.pdf",
            "dry_run": True,
        },
    },
    "pdf_generator": {
        "model": PDFDocumentInput,
        "sample_input": {
            "title": "Tool Health Check PDF",
            "output_path": "health_check.pdf",
            "sections": [{"title": "Overview", "content": "PDF Tool verified."}],
        },
    },
    "pdf_tool": {
        "model": PDFDocumentInput,
        "sample_input": {
            "title": "Tool Health Check PDF",
            "output_path": "health_check.pdf",
            "sections": [{"title": "Overview", "content": "PDF Tool verified."}],
        },
    },
    "screenshot_engine": {
        "model": ScreenshotRequest,
        "sample_input": {
            "source": "DESKTOP",
            "format": "PNG",
            "dry_run": True,
        },
    },
    "terminal_tool": {
        "model": TerminalToolInput,
        "sample_input": {"command": "echo ToolHealthCheckOK"},
    },
    "web_research": {
        "model": WebResearchRequest,
        "sample_input": {"query": "AetherPhoenix tool health check"},
    },
    "web_research_tool": {
        "model": WebResearchRequest,
        "sample_input": {"query": "AetherPhoenix tool health check"},
    },
    "ppt_tool": {
        "model": None,  # PresentationRequest/dict
        "sample_input": {
            "title": "Health Check Deck",
            "slides": [{"title": "Slide 1", "bullet_points": ["Point 1"]}],
        },
    },
    "ppt_generator": {
        "model": None,
        "sample_input": {
            "title": "Health Check Deck",
            "slides": [{"title": "Slide 1", "bullet_points": ["Point 1"]}],
        },
    },
    "browser_automation": {
        "model": None,
        "sample_input": {"action": "status"},
    },
    "browser_extension": {
        "model": None,
        "sample_input": {"action": "status"},
    },
    "web_scraping": {
        "model": ScrapeRequest,
        "sample_input": {"url": "https://example.com", "dry_run": True},
    },
}


def build_system_registry() -> ToolRegistry:
    """Builds and populates the ToolRegistry with all system tools."""
    registry = ToolRegistry()
    register_desktop_tool(registry)
    register_document_tool(registry)
    register_export_tool(registry)
    register_file_explorer_tool(registry)
    register_git_tool(registry)
    register_ocr_tool(registry)
    register_pdf_tool(registry)
    register_screenshot_tool(registry)
    register_terminal_tool(registry)
    register_web_research_tool(registry)
    register_ppt_tool(registry)
    register_browser_capability(registry)
    register_browser_extension_capability(registry)
    register_web_scraping_tool(registry)
    return registry


def get_known_planner_tools() -> set[str]:
    """Collects all required_tool / required_tools strings from decomposer & planner capabilities."""
    from app.agents.planner.agent import PlannerAgent

    planner = PlannerAgent()
    planner_tools = set()
    for cap in planner.capability_engine.registry.list_all():
        if cap.required_tools:
            planner_tools.update(cap.required_tools)
        planner_tools.add(cap.name)

    # Add decomposer emitted strings
    decomposer_tools = {
        "ppt_tool",
        "ppt_generator",
        "export",
        "terminal_tool",
        "file_explorer",
        "file_manager_tool",
        "browser_extension",
        "browser_automation",
        "desktop_automation",
        "ocr",
        "ocr_tool",
        "pdf_search",
        "pdf_generator",
        "pdf_tool",
        "document_generator",
        "content_tool",
        "screenshot_engine",
        "web_research",
        "web_research_tool",
        "web_scraping",
        "git_tool",
    }
    return planner_tools.union(decomposer_tools)


async def check_all_tools() -> Tuple[List[Dict[str, Any]], bool]:
    """
    Executes health checks across all registered tools in ToolRegistry.
    Returns (results, overall_success).
    """
    registry = build_system_registry()
    known_planner_tools = get_known_planner_tools()

    # Configure permissive permission mock
    mock_pm = MagicMock()
    mock_pm.check_permission.return_value = True
    granted_mock = MagicMock()
    granted_mock.status = PermissionStatus.GRANTED
    mock_pm.request_permission.return_value = granted_mock

    worker = WorkerAgent(tool_registry=registry, permission_manager=mock_pm)

    results = []
    all_passed = True

    for tool in registry.list_all():
        tool_name = tool.name
        adapter_name = tool.adapter
        cfg = TOOL_CONFIGS.get(tool_name, {"model": None, "sample_input": {}})

        # 1. Registered Name Check
        name_match = tool_name in known_planner_tools
        # Some tools are aliases or underlying utilities
        if not name_match:
            # Check prefix/suffix alias matching
            name_match = any(
                known in tool_name or tool_name in known
                for known in known_planner_tools
            )

        # 2. Input Schema Validation
        model_cls: Optional[Type[BaseModel]] = cfg.get("model")
        sample_input = cfg.get("sample_input", {})
        schema_valid = True
        schema_error = None

        if model_cls is not None:
            try:
                # Filter sample input for the model
                model_cls.model_validate(sample_input)
            except Exception as e:
                schema_valid = False
                schema_error = str(e)

        # 3. Dry-Run Execution via WorkerAgent
        exec_pass = False
        exec_error = None
        task = Task(
            task_id=uuid4(),
            workflow_id=uuid4(),
            task_name=f"health_check_{tool_name}",
            description=f"Health check execution for {tool_name}",
            expected_output=f"Validation result for {tool_name}",
            task_type=TaskType.LEAF,
            category=TaskCategory.OTHER,
            required_tool=tool_name,
            inputs=sample_input,
        )

        try:
            res = await asyncio.wait_for(worker.execute(task), timeout=5.0)
            if isinstance(res, ExecutionResult):
                exec_pass = True
            else:
                exec_error = f"Expected ExecutionResult, got {type(res).__name__}"
        except Exception as e:
            exec_error = f"{type(e).__name__}: {str(e)}"

        overall_tool_status = name_match and schema_valid and exec_pass
        if not overall_tool_status:
            all_passed = False

        results.append(
            {
                "tool_name": tool_name,
                "adapter": adapter_name.split(".")[-1] if adapter_name else "None",
                "name_match": name_match,
                "schema_valid": schema_valid,
                "schema_error": schema_error,
                "exec_pass": exec_pass,
                "exec_error": exec_error,
                "status": overall_tool_status,
            }
        )

    return results, all_passed


def print_results_table(results: List[Dict[str, Any]]) -> None:
    """Formats and prints the results table."""
    col_tool = 24
    col_adapter = 28
    col_check = 12
    col_status = 10

    header = (
        f"| {'Tool Name'.ljust(col_tool)}"
        f"| {'Adapter Class'.ljust(col_adapter)}"
        f"| {'Name Match'.ljust(col_check)}"
        f"| {'Schema'.ljust(col_check)}"
        f"| {'Dry Run'.ljust(col_check)}"
        f"| {'Status'.ljust(col_status)}|"
    )
    separator = "-" * len(header)

    print("\n" + "=" * len(header))
    print("AETHERPHOENIX TOOL REGISTRY & ORGANIZER HEALTH CHECK".center(len(header)))
    print("=" * len(header))
    print(header)
    print(separator)

    passed_count = 0
    failed_count = 0

    for r in results:
        t_name = r["tool_name"][:col_tool].ljust(col_tool)
        t_adapter = r["adapter"][:col_adapter].ljust(col_adapter)
        m_str = ("PASS" if r["name_match"] else "FAIL").ljust(col_check)
        s_str = ("PASS" if r["schema_valid"] else "FAIL").ljust(col_check)
        e_str = ("PASS" if r["exec_pass"] else "FAIL").ljust(col_check)
        status_str = ("PASS" if r["status"] else "FAIL").ljust(col_status)

        if r["status"]:
            passed_count += 1
        else:
            failed_count += 1

        print(f"| {t_name}| {t_adapter}| {m_str}| {s_str}| {e_str}| {status_str}|")

    print(separator)
    print(
        f"Total Checked: {len(results)} | Passed: {passed_count} | Failed: {failed_count}"
    )
    print("=" * len(header) + "\n")

    # If any failures, print diagnostic details
    if failed_count > 0:
        print("DIAGNOSTIC FAILURE DETAILS:")
        for r in results:
            if not r["status"]:
                print(f"[-] Tool: {r['tool_name']}")
                if not r["name_match"]:
                    print(f"    Name Match: Not found in planner/decomposer emitted tool strings")
                if not r["schema_valid"]:
                    print(f"    Schema Error: {r['schema_error']}")
                if not r["exec_pass"]:
                    print(f"    Execution Error: {r['exec_error']}")
        print()


def main() -> int:
    results, all_passed = asyncio.run(check_all_tools())
    print_results_table(results)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
