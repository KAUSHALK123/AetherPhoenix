from unittest.mock import patch

import pytest
from PIL import Image

from app.tools.desktop.interface import DesktopTool
from app.tools.desktop.screenshot import (
    DesktopScreenshotController,
    DesktopScreenshotError,
)


@pytest.fixture
def mock_pil_image():
    return Image.new("RGB", (1920, 1080), color="blue")


@pytest.fixture
def mock_region_image():
    return Image.new("RGB", (300, 200), color="red")


@patch("app.tools.desktop.screenshot.pyautogui.screenshot")
def test_desktop_screenshot_fullscreen(mock_screenshot, mock_pil_image):
    mock_screenshot.return_value = mock_pil_image

    img = DesktopScreenshotController.capture_fullscreen()
    assert img.width == 1920
    assert img.height == 1080
    mock_screenshot.assert_called_once_with(None)


@patch("app.tools.desktop.screenshot.pyautogui.screenshot")
def test_desktop_screenshot_fullscreen_with_path(
    mock_screenshot, mock_pil_image, tmp_path
):
    out_file = str(tmp_path / "custom_full.png")
    mock_screenshot.return_value = mock_pil_image

    img = DesktopScreenshotController.capture_fullscreen(output_path=out_file)
    assert img.width == 1920
    mock_screenshot.assert_called_once_with(out_file)


@patch("app.tools.desktop.screenshot.pyautogui.screenshot")
def test_desktop_screenshot_region(mock_screenshot, mock_region_image):
    mock_screenshot.return_value = mock_region_image

    img = DesktopScreenshotController.capture_region(x=50, y=60, width=300, height=200)
    assert img.width == 300
    assert img.height == 200
    mock_screenshot.assert_called_once_with(None, region=(50, 60, 300, 200))


def test_desktop_screenshot_region_invalid_dimensions():
    with pytest.raises(DesktopScreenshotError, match="Invalid region dimensions"):
        DesktopScreenshotController.capture_region(x=0, y=0, width=0, height=100)

    with pytest.raises(DesktopScreenshotError, match="Invalid region dimensions"):
        DesktopScreenshotController.capture_region(x=0, y=0, width=100, height=-10)

    with pytest.raises(DesktopScreenshotError, match="Invalid region coordinates"):
        DesktopScreenshotController.capture_region(x=-1, y=0, width=100, height=100)


@patch(
    "app.tools.desktop.screenshot.pyautogui.screenshot",
    side_effect=Exception("Display disconnected"),
)
def test_desktop_screenshot_fullscreen_failure(mock_screenshot):
    with pytest.raises(DesktopScreenshotError, match="Failed to capture full screen"):
        DesktopScreenshotController.capture_fullscreen()


@patch("app.tools.desktop.screenshot.pyautogui.size", return_value=(2560, 1440))
def test_desktop_screenshot_get_screen_size(mock_size):
    size = DesktopScreenshotController.get_screen_size()
    assert size == (2560, 1440)


@patch("app.tools.desktop.screenshot.DesktopScreenshotController.capture_fullscreen")
def test_desktop_tool_execute_screenshot_fullscreen(mock_capture, mock_pil_image):
    mock_capture.return_value = mock_pil_image
    tool = DesktopTool()

    result = tool.execute("screenshot_fullscreen", {})
    assert result["status"] == "success"
    assert result["action"] == "screenshot_fullscreen"
    assert result["width"] == 1920
    assert result["height"] == 1080
    mock_capture.assert_called_once_with(output_path=None)


@patch("app.tools.desktop.screenshot.DesktopScreenshotController.capture_region")
def test_desktop_tool_execute_screenshot_region(mock_capture, mock_region_image):
    mock_capture.return_value = mock_region_image
    tool = DesktopTool()

    result = tool.execute(
        "screenshot_region",
        {"x": 100, "y": 150, "width": 300, "height": 200},
    )
    assert result["status"] == "success"
    assert result["action"] == "screenshot_region"
    assert result["width"] == 300
    assert result["height"] == 200
    mock_capture.assert_called_once_with(
        x=100, y=150, width=300, height=200, output_path=None
    )
