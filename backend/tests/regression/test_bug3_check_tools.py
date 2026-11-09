"""Regression test for Bug 3: Tool Registry and Organizer Health Check."""

import subprocess
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest

from scripts.check_tools import check_all_tools, build_system_registry


@pytest.mark.asyncio
async def test_all_tools_health_check_passes():
    """Verify check_all_tools() reports 100% PASS for all registered tools."""
    results, all_passed = await check_all_tools()
    assert all_passed is True, f"Tool health check failed with results: {results}"
    assert len(results) >= 15, f"Expected at least 15 tools verified, got {len(results)}"

    for r in results:
        assert r["name_match"] is True, f"Tool '{r['tool_name']}' name match failed"
        assert r["schema_valid"] is True, (
            f"Tool '{r['tool_name']}' schema valid failed: {r['schema_error']}"
        )
        assert r["exec_pass"] is True, (
            f"Tool '{r['tool_name']}' execution failed: {r['exec_error']}"
        )
        assert r["status"] is True, f"Tool '{r['tool_name']}' overall status failed"


def test_check_tools_script_cli_execution():
    """Verify backend/scripts/check_tools.py runs cleanly via CLI and returns exit code 0."""
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "check_tools.py"
    res = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Script failed with output:\n{res.stdout}\n{res.stderr}"
    assert "AETHERPHOENIX TOOL REGISTRY & ORGANIZER HEALTH CHECK" in res.stdout
    assert "Passed: 20" in res.stdout
    assert "Failed: 0" in res.stdout
