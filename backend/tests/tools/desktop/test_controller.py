from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.exceptions import PermissionDeniedException
from app.core.permissions.manager import PermissionManager
from app.tools.desktop.application import ApplicationController
from app.tools.desktop.controller import DesktopController
from app.tools.desktop.exceptions import (
    ApplicationNotFoundError,
    ApplicationUnavailableError,
    WindowNotFoundError,
)
from app.tools.desktop.models import (
    ApplicationInfo,
    DesktopSessionConfig,
    DesktopState,
    WindowBounds,
    WindowInfo,
)


@pytest.mark.asyncio
async def test_desktop_controller_session_lifecycle():
    controller = DesktopController()
    assert controller.is_session_active() is False

    # Start session
    wf_id = uuid4()
    task_id = uuid4()
    session = await controller.start_session(
        workflow_id=wf_id,
        task_id=task_id,
        config=DesktopSessionConfig(session_timeout_seconds=300),
    )
    assert session is not None
    assert controller.is_session_active() is True
    assert controller.get_active_session() == session

    # End session
    await controller.end_session(session.session_id)
    assert controller.is_session_active() is False
    assert controller.get_active_session() is None


@pytest.mark.asyncio
@patch.object(ApplicationController, "launch_app")
async def test_application_launch_success(mock_launch):
    app_info = ApplicationInfo(
        process_id=1234, name="notepad.exe", path="C:\\Windows\\notepad.exe"
    )
    mock_launch.return_value = app_info

    controller = DesktopController()
    session = await controller.start_session()

    result = await controller.launch_application(app_path="notepad.exe")

    mock_launch.assert_called_once_with(
        app_path="notepad.exe",
        args=None,
        timeout=10.0,
        working_dir=None,
        allowed_apps=None,
    )
    assert result.process_id == 1234
    assert result.name == "notepad.exe"
    assert 1234 in session.launched_processes


@pytest.mark.asyncio
async def test_application_launch_not_found():
    controller = DesktopController()
    with pytest.raises(ApplicationNotFoundError):
        await controller.launch_application(app_path="C:\\non_existent_path\\ghost.exe")


@pytest.mark.asyncio
async def test_application_launch_prohibited():
    controller = DesktopController()
    with pytest.raises(ApplicationUnavailableError, match="prohibited"):
        await controller.launch_application(app_path="cmd.exe")


@pytest.mark.asyncio
async def test_application_launch_disallowed_by_session():
    controller = DesktopController()
    config = DesktopSessionConfig(allowed_applications=["notepad.exe"])
    await controller.start_session(config=config)

    with pytest.raises(ApplicationUnavailableError, match="not in the permitted list"):
        await controller.launch_application(app_path="calc.exe")


@pytest.mark.asyncio
@patch.object(ApplicationController, "terminate_app")
async def test_application_termination_success(mock_terminate):
    mock_terminate.return_value = True

    controller = DesktopController()
    session = await controller.start_session()
    app_info = ApplicationInfo(process_id=5678, name="notepad.exe")
    session.register_process(app_info)

    result = await controller.close_application(pid=5678)

    mock_terminate.assert_called_once_with(
        pid=5678, title=None, force=False, timeout=5.0
    )
    assert result is True
    assert 5678 not in session.launched_processes


@pytest.mark.asyncio
@patch("app.tools.desktop.controller.Desktop")
async def test_window_discovery_and_filtering(mock_desktop_class):
    mock_dt_instance = MagicMock()
    mock_desktop_class.return_value = mock_dt_instance

    win1 = MagicMock()
    win1.window_text.return_value = "Document - WordPad"
    win1.is_visible.return_value = True
    win1.handle = 1001
    win1.process_id = 111
    win1.rectangle.return_value = MagicMock(
        left=10, top=20, width=lambda: 800, height=lambda: 600
    )
    win1.class_name.return_value = "WordPadClass"

    win2 = MagicMock()
    win2.window_text.return_value = "Calculator"
    win2.is_visible.return_value = True
    win2.handle = 1002
    win2.process_id = 222
    win2.rectangle.return_value = MagicMock(
        left=50, top=50, width=lambda: 400, height=lambda: 500
    )
    win2.class_name.return_value = "CalcClass"

    mock_dt_instance.windows.return_value = [win1, win2]

    controller = DesktopController()

    # Discover all
    all_windows = await controller.get_windows()
    assert len(all_windows) == 2
    assert all_windows[0].title == "Document - WordPad"
    assert all_windows[0].bounds == WindowBounds(x=10, y=20, width=800, height=600)

    # Filter title
    filtered = await controller.get_windows(filter_title="calculator")
    assert len(filtered) == 1
    assert filtered[0].title == "Calculator"

    # Filter PID
    pid_filtered = await controller.get_windows(filter_process_id=111)
    assert len(pid_filtered) == 1
    assert pid_filtered[0].handle == 1001


@pytest.mark.asyncio
@patch("app.tools.desktop.controller.Desktop")
async def test_window_focus_success(mock_desktop_class):
    mock_dt_instance = MagicMock()
    mock_desktop_class.return_value = mock_dt_instance

    win = MagicMock()
    win.window_text.return_value = "Notepad - Test"
    win.handle = 2001
    win.process_id = 333
    win.rectangle.return_value = MagicMock(
        left=0, top=0, width=lambda: 600, height=lambda: 400
    )

    mock_dt_instance.windows.return_value = [win]

    controller = DesktopController()
    focused = await controller.focus_window(title="Notepad")

    win.restore.assert_called_once()
    win.set_focus.assert_called_once()
    assert focused.title == "Notepad - Test"
    assert focused.is_active is True


@pytest.mark.asyncio
@patch("app.tools.desktop.controller.Desktop")
async def test_window_focus_not_found(mock_desktop_class):
    mock_dt_instance = MagicMock()
    mock_desktop_class.return_value = mock_dt_instance
    mock_dt_instance.windows.return_value = []

    controller = DesktopController()
    with pytest.raises(WindowNotFoundError):
        await controller.focus_window(title="Missing Window Title")


@pytest.mark.asyncio
@patch("app.tools.desktop.controller.Desktop")
async def test_get_active_window(mock_desktop_class):
    mock_dt_instance = MagicMock()
    mock_desktop_class.return_value = mock_dt_instance

    win = MagicMock()
    win.window_text.return_value = "Active App"
    win.handle = 3001
    win.process_id = 444
    win.is_visible.return_value = True
    win.rectangle.return_value = MagicMock(
        left=0, top=0, width=lambda: 100, height=lambda: 100
    )

    mock_dt_instance.windows.return_value = [win]

    controller = DesktopController()

    with patch.object(controller, "_get_foreground_window_handle", return_value=3001):
        active = await controller.get_active_window()
        assert active is not None
        assert active.title == "Active App"
        assert active.is_active is True


@pytest.mark.asyncio
@patch("app.tools.desktop.controller.Desktop")
async def test_get_active_window_none(mock_desktop_class):
    mock_dt_instance = MagicMock()
    mock_desktop_class.return_value = mock_dt_instance
    mock_dt_instance.windows.return_value = []

    controller = DesktopController()
    with patch.object(controller, "_get_foreground_window_handle", return_value=None):
        active = await controller.get_active_window()
        assert active is None


@pytest.mark.asyncio
@patch.object(DesktopController, "get_screen_resolution")
@patch.object(DesktopController, "get_windows")
@patch.object(DesktopController, "get_active_window")
async def test_get_desktop_state(mock_active, mock_windows, mock_res):
    from app.tools.desktop.models import ScreenResolution

    mock_res.return_value = ScreenResolution(width=1920, height=1080)
    mock_active.return_value = WindowInfo(handle=1, title="Active", is_active=True)
    mock_windows.return_value = [WindowInfo(handle=1, title="Active", is_active=True)]

    controller = DesktopController()
    session = await controller.start_session()

    state = await controller.get_desktop_state()

    assert isinstance(state, DesktopState)
    assert state.screen_resolution.width == 1920
    assert state.active_window.title == "Active"
    assert len(state.open_windows) == 1
    assert state.session is not None
    assert state.session.session_id == session.session_id


@pytest.mark.asyncio
async def test_permission_denied():
    pm = MagicMock(spec=PermissionManager)
    pm.check_permission.return_value = False

    controller = DesktopController(permission_manager=pm)

    with pytest.raises(PermissionDeniedException):
        await controller.launch_application(app_path="notepad.exe")

    with pytest.raises(PermissionDeniedException):
        await controller.get_windows()

    with pytest.raises(PermissionDeniedException):
        await controller.focus_window(title="notepad")


@pytest.mark.asyncio
@patch("app.tools.desktop.mouse.pyautogui.click")
@patch("app.tools.desktop.mouse.pyautogui.moveTo")
@patch("app.tools.desktop.mouse.pyautogui.scroll")
@patch("app.tools.desktop.keyboard.pyautogui.write")
@patch("app.tools.desktop.keyboard.pyautogui.press")
@patch("app.tools.desktop.keyboard.pyautogui.hotkey")
async def test_mouse_and_keyboard_actions(
    mock_hotkey, mock_press, mock_write, mock_scroll, mock_move, mock_click
):
    controller = DesktopController()
    await controller.start_session()

    # Mouse Click
    res_click = await controller.click(100, 200, button="left")
    mock_click.assert_called_once_with(
        x=100, y=200, button="left", clicks=1, interval=0.0, duration=0.0
    )
    assert res_click["action"] == "mouse_click"

    # Mouse Move
    res_move = await controller.move_to(300, 400, duration=0.2)
    mock_move.assert_called_once_with(x=300, y=400, duration=0.2)
    assert res_move["action"] == "mouse_move"

    # Mouse Scroll
    res_scroll = await controller.scroll(5)
    mock_scroll.assert_called_once_with(5)
    assert res_scroll["action"] == "mouse_scroll"

    # Keyboard Type
    res_type = await controller.type_text("Hello World", interval=0.01)
    mock_write.assert_called_once_with("Hello World", interval=0.01)
    assert res_type["action"] == "keyboard_type"

    # Keyboard Press
    res_press = await controller.press_key("enter")
    mock_press.assert_called_once_with("enter")
    assert res_press["action"] == "keyboard_press"

    # Keyboard Hotkey
    res_hotkey = await controller.hotkey("ctrl", "s")
    mock_hotkey.assert_called_once_with("ctrl", "s")
    assert res_hotkey["action"] == "keyboard_hotkey"


@pytest.mark.asyncio
@patch.object(ApplicationController, "launch_app")
async def test_execute_action_dispatcher(mock_launch):
    mock_launch.return_value = ApplicationInfo(process_id=999, name="notepad.exe")

    controller = DesktopController()

    # start_session
    res_start = await controller.execute_action("start_session", {})
    assert res_start.success is True
    assert "session" in res_start.output

    # launch_app
    res_launch = await controller.execute_action(
        "launch_app", {"app_path": "notepad.exe"}
    )
    assert res_launch.success is True
    assert res_launch.output["application"]["name"] == "notepad.exe"

    # end_session
    res_end = await controller.execute_action("end_session", {})
    assert res_end.success is True

    # unknown action
    res_unknown = await controller.execute_action("unknown_action_xyz", {})
    assert res_unknown.success is False
    assert "Unsupported desktop action" in res_unknown.error
