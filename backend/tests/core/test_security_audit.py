"""Pre-Production Security Review & Vulnerability Regression Test Suite.

Validates remediations for:
1. Destructive command unconditional blocking in SafeExecutionPolicy (CRITICAL)
2. Normalized URL scheme checking (HIGH)
3. PowerShell permission bypass prevention and destructive command rejection (HIGH)
4. ExportEngine path traversal prevention on output_path and source_filepath (CRITICAL)
5. ArtifactStorageService filename sanitization and directory containment (HIGH)
6. FileExplorerExecutor path containment verification (HIGH)
7. Security Headers & Request Body Size Limit Middlewares (MEDIUM)
"""

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.export import ExportFormat, ExportRequest
from shared.contracts.permission import PermissionType, RiskLevel
from shared.contracts.workflow import ExecutionMode

from app.core.exceptions import PermissionDeniedException
from app.core.permissions.policies import (
    DESTRUCTIVE_COMMAND_TOKENS,
    SafeExecutionPolicy,
)
from app.main import app
from app.services.artifact_storage import LocalFileSystemArtifactStorageProvider
from app.tools.export.engine import ExportEngine, ExportError
from app.tools.file_explorer.executor import FileExplorerExecutor
from app.tools.powershell.executor import PowerShellExecutor
from app.tools.powershell.models import PowerShellCommand


class MockPermissionManager:
    def __init__(self, should_approve=True):
        self.should_approve = should_approve
        self.checked_actions = []

    async def check_permission(
        self, action: str, permission_type: PermissionType, **kwargs
    ) -> bool:
        self.checked_actions.append((action, permission_type))
        return self.should_approve


# =============================================================================
# 1. SafeExecutionPolicy Destructive Command & URL Tests
# =============================================================================


def test_destructive_commands_classified_critical_and_blocked():
    """Verify all destructive command patterns are classified as CRITICAL
    and blocked across all modes.
    """
    for token in DESTRUCTIVE_COMMAND_TOKENS:
        ctx = {"command": f"test-prefix {token} /something"}
        assert (
            SafeExecutionPolicy.classify_risk("powershell_execute", ctx)
            == RiskLevel.CRITICAL
        )

        # SAFE mode
        decision_safe = SafeExecutionPolicy.evaluate(
            "powershell_execute", mode=ExecutionMode.SAFE, context=ctx
        )
        assert decision_safe.allowed is False
        assert decision_safe.risk_level == RiskLevel.CRITICAL

        # ASSISTED mode
        decision_assisted = SafeExecutionPolicy.evaluate(
            "powershell_execute", mode=ExecutionMode.ASSISTED, context=ctx
        )
        assert decision_assisted.allowed is False
        assert decision_assisted.risk_level == RiskLevel.CRITICAL

        # AUTONOMOUS mode
        decision_auto = SafeExecutionPolicy.evaluate(
            "powershell_execute", mode=ExecutionMode.AUTONOMOUS, context=ctx
        )
        assert decision_auto.allowed is False
        assert decision_auto.risk_level == RiskLevel.CRITICAL


def test_restricted_urls_normalized_and_blocked():
    """Verify URL scheme parsing normalizes uppercase and whitespace schemes."""
    evasive_urls = [
        "FILE:///etc/passwd",
        "  file:///C:/Windows/System32",
        "GOPHER://malicious.host",
        "javascript:alert(1)",
        "DATA://text/html;base64,PHNjcmlwdD4=",
    ]
    for url in evasive_urls:
        ctx = {"url": url}
        assert (
            SafeExecutionPolicy.classify_risk("browser_navigate", ctx)
            == RiskLevel.CRITICAL
        )

        decision = SafeExecutionPolicy.evaluate(
            "browser_navigate", mode=ExecutionMode.AUTONOMOUS, context=ctx
        )
        assert decision.allowed is False
        assert decision.risk_level == RiskLevel.CRITICAL


# =============================================================================
# 2. PowerShell Executor Security Tests
# =============================================================================


@pytest.mark.asyncio
async def test_powershell_executor_enforces_permission_regardless_of_flag():
    """Verify permission check is never bypassed when require_approval is False."""
    denied_pm = MockPermissionManager(should_approve=False)
    executor = PowerShellExecutor(permission_manager=denied_pm)

    cmd = PowerShellCommand(
        command="Write-Output 'Attempting bypass'",
        require_approval=False,
    )
    with pytest.raises(PermissionDeniedException) as exc_info:
        await executor.execute(cmd)

    assert "Permission denied for PowerShell execution" in str(exc_info.value)
    assert len(denied_pm.checked_actions) == 1


@pytest.mark.asyncio
async def test_powershell_executor_blocks_destructive_commands():
    """Verify destructive commands fail validation before execution."""
    approved_pm = MockPermissionManager(should_approve=True)
    executor = PowerShellExecutor(permission_manager=approved_pm)

    destructive_cmds = [
        "Remove-Item -Path C:\\secret -Recurse -Force",
        "Format-Volume -DriveLetter D",
        "del /f C:\\important.dat",
        "Clear-Disk -Number 1",
        "Set-ExecutionPolicy Unrestricted",
    ]
    for cmd_str in destructive_cmds:
        cmd = PowerShellCommand(command=cmd_str)
        with pytest.raises(PermissionDeniedException) as exc_info:
            await executor.execute(cmd)
        assert "prohibited patterns" in str(exc_info.value)


# =============================================================================
# 3. ExportEngine Path Traversal Tests
# =============================================================================


@pytest.mark.asyncio
async def test_export_engine_blocks_output_path_traversal(tmp_path):
    """Verify output_path traversal outside permitted directories is rejected."""
    storage_dir = tmp_path / "artifacts"
    storage_dir.mkdir()
    provider = LocalFileSystemArtifactStorageProvider(base_dir=storage_dir)
    engine = ExportEngine(artifact_storage_service=provider)

    req = ExportRequest(
        workflow_id=uuid4(),
        target_format=ExportFormat.TXT,
        metadata={"content": "safe text content"},
        output_path=str(Path.home() / "malicious_export.txt"),
        title="malicious_export",
    )

    with pytest.raises(ExportError) as exc_info:
        await engine.export(req)

    assert "outside permitted directories" in str(exc_info.value)


@pytest.mark.asyncio
async def test_export_engine_blocks_source_filepath_traversal(tmp_path):
    """Verify reading arbitrary sensitive system files via source_filepath
    is rejected.
    """
    storage_dir = tmp_path / "artifacts"
    storage_dir.mkdir()
    provider = LocalFileSystemArtifactStorageProvider(base_dir=storage_dir)
    engine = ExportEngine(artifact_storage_service=provider)

    outside_file = Path.home() / f"test_secret_{uuid4().hex}.txt"
    outside_file.write_text("sensitive credentials", encoding="utf-8")
    try:
        req = ExportRequest(
            workflow_id=uuid4(),
            target_format=ExportFormat.TXT,
            source_filepath=str(outside_file),
            title="leak_export",
        )

        with pytest.raises(ExportError) as exc_info:
            await engine.export(req)

        assert "outside permitted directories" in str(exc_info.value)
    finally:
        if outside_file.exists():
            outside_file.unlink()


# =============================================================================
# 4. ArtifactStorageService Filename Sanitization Tests
# =============================================================================


@pytest.mark.asyncio
async def test_artifact_storage_sanitizes_path_traversal_filenames(tmp_path):
    """Verify artifact.name containing traversal characters is sanitized
    and constrained.
    """
    storage_dir = tmp_path / "artifacts"
    storage_dir.mkdir()
    provider = LocalFileSystemArtifactStorageProvider(base_dir=storage_dir)

    wf_id = uuid4()
    malicious_artifact = Artifact(
        workflow_id=wf_id,
        name="../../../../../evil_payload.sh",
        filepath="",
        artifact_type=ArtifactType.CODE,
        size_bytes=10,
    )

    saved = await provider.save_artifact(
        artifact=malicious_artifact,
        content=b"echo 'pwned'",
    )

    saved_path = Path(saved.filepath)
    assert saved_path.exists()
    # Path must remain inside the storage directory
    assert saved_path.is_relative_to(storage_dir.resolve())
    # Filename must be sanitized
    assert ".." not in saved_path.name


# =============================================================================
# 5. FileExplorerExecutor Path Containment Tests
# =============================================================================


@pytest.mark.asyncio
async def test_file_explorer_path_containment():
    """Verify FileExplorerExecutor strictly enforces path containment."""
    executor = FileExplorerExecutor()

    # Sibling folder with common prefix attempt
    sibling_path = str(executor.workspace_dir) + "_compromised/stolen.txt"
    with pytest.raises(ValueError) as exc_info:
        executor._resolve_and_validate_path(sibling_path)

    assert "outside the permitted directories" in str(exc_info.value)


# =============================================================================
# 6. HTTP API Security Headers & Request Limits Tests
# =============================================================================


def test_api_security_headers():
    """Verify standard HTTP security headers are included in API responses."""
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


def test_api_request_body_size_limit():
    """Verify oversized requests are rejected with HTTP 413 Payload Too Large."""
    client = TestClient(app)
    # Exceed 20MB limit via content-length header
    headers = {"content-length": str(25 * 1024 * 1024)}
    response = client.post(
        "/api/v1/planner/submit", json={"message": "hello"}, headers=headers
    )
    assert response.status_code == 413
    assert "Payload Too Large" in response.text
