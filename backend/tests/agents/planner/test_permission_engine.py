import uuid

from shared.contracts.permission import PermissionType, RiskLevel
from shared.contracts.task import Task, TaskCategory

from app.agents.planner.permission_engine import PermissionDetectionEngine


def create_task(
    category: TaskCategory,
    task_name: str = "Test Task",
    description: str = "A test task",
    required_tool: str = "test_tool",
) -> Task:
    return Task(
        workflow_id=uuid.uuid4(),
        task_name=task_name,
        description=description,
        required_tool=required_tool,
        category=category,
        expected_output="Success",
    )


def test_safe_task_no_permissions():
    engine = PermissionDetectionEngine()
    t1 = create_task(
        category=TaskCategory.OTHER, description="Do some basic calculation"
    )

    tasks, requests = engine.detect_permissions([t1])

    assert len(tasks) == 1
    assert len(requests) == 0
    assert len(tasks[0].permissions) == 0
    assert tasks[0].risk_level == RiskLevel.LOW.value


def test_browser_task():
    engine = PermissionDetectionEngine()
    t1 = create_task(
        category=TaskCategory.BROWSER, description="Search google for recent news"
    )

    tasks, requests = engine.detect_permissions([t1])

    assert len(tasks) == 1
    assert len(requests) == 2
    assert PermissionType.BROWSER_ACCESS.value in tasks[0].permissions
    assert PermissionType.INTERNET.value in tasks[0].permissions
    assert tasks[0].risk_level == RiskLevel.MEDIUM.value


def test_file_deletion_critical_risk():
    engine = PermissionDetectionEngine()
    t1 = create_task(
        category=TaskCategory.FILE_SYSTEM,
        task_name="Delete temp files",
        description="remove the old log files",
    )

    tasks, requests = engine.detect_permissions([t1])

    assert len(tasks) == 1
    assert len(requests) == 1
    assert PermissionType.FILE_SYSTEM.value in tasks[0].permissions
    assert tasks[0].risk_level == RiskLevel.CRITICAL.value


def test_software_installation():
    engine = PermissionDetectionEngine()
    t1 = create_task(
        category=TaskCategory.OTHER,
        task_name="Install Node.js",
        description="setup node.js for the project",
    )

    tasks, requests = engine.detect_permissions([t1])

    assert len(tasks) == 1
    assert len(requests) == 2
    assert PermissionType.ADMINISTRATOR.value in tasks[0].permissions
    assert PermissionType.FILE_SYSTEM.value in tasks[0].permissions
    assert tasks[0].risk_level == RiskLevel.HIGH.value


def test_desktop_control():
    engine = PermissionDetectionEngine()
    t1 = create_task(category=TaskCategory.DESKTOP, description="Open an application")

    tasks, requests = engine.detect_permissions([t1])

    assert len(tasks) == 1
    assert len(requests) == 2
    assert PermissionType.ADMINISTRATOR.value in tasks[0].permissions
    assert PermissionType.CLIPBOARD.value in tasks[0].permissions
    assert tasks[0].risk_level == RiskLevel.HIGH.value


def test_external_api_access():
    engine = PermissionDetectionEngine()
    t1 = create_task(
        category=TaskCategory.OTHER,
        task_name="Fetch weather",
        description="call external API to get weather",
    )

    tasks, requests = engine.detect_permissions([t1])

    assert len(tasks) == 1
    assert len(requests) == 1
    assert PermissionType.INTERNET.value in tasks[0].permissions
    assert tasks[0].risk_level == RiskLevel.LOW.value


def test_registry_modification():
    engine = PermissionDetectionEngine()
    t1 = create_task(
        category=TaskCategory.POWERSHELL,
        task_name="Modify registry",
        description="update registry keys for the app",
    )

    tasks, requests = engine.detect_permissions([t1])

    assert len(tasks) == 1
    assert len(requests) == 3
    assert PermissionType.REGISTRY.value in tasks[0].permissions
    assert PermissionType.ADMINISTRATOR.value in tasks[0].permissions
    assert PermissionType.POWERSHELL.value in tasks[0].permissions
    assert tasks[0].risk_level == RiskLevel.CRITICAL.value


def test_mixed_plan():
    engine = PermissionDetectionEngine()
    t1 = create_task(category=TaskCategory.OTHER, description="Safe task")
    t2 = create_task(category=TaskCategory.BROWSER, description="Search")
    t3 = create_task(category=TaskCategory.FILE_SYSTEM, description="delete old files")

    tasks, requests = engine.detect_permissions([t1, t2, t3])

    assert len(tasks) == 3
    # t1: 0, t2: 2, t3: 1
    assert len(requests) == 3

    # Verify t1
    assert tasks[0].risk_level == RiskLevel.LOW.value
    assert len(tasks[0].permissions) == 0

    # Verify t2
    assert tasks[1].risk_level == RiskLevel.MEDIUM.value
    assert len(tasks[1].permissions) == 2

    # Verify t3
    assert tasks[2].risk_level == RiskLevel.CRITICAL.value
    assert len(tasks[2].permissions) == 1
