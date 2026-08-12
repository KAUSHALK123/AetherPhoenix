from unittest.mock import MagicMock, patch

import pytest

from app.tools.desktop.application import ApplicationActionError, ApplicationController


@patch("app.tools.desktop.application.Application")
def test_application_launch(mock_app_class):
    mock_instance = MagicMock()
    mock_app_class.return_value = mock_instance
    mock_instance.start.return_value = "fake_app_obj"

    result = ApplicationController.launch("notepad.exe")

    mock_app_class.assert_called_once_with(backend="uia")
    mock_instance.start.assert_called_once_with("notepad.exe")
    assert result == "fake_app_obj"


@patch("app.tools.desktop.application.Application")
def test_application_connect(mock_app_class):
    mock_instance = MagicMock()
    mock_app_class.return_value = mock_instance
    mock_instance.connect.return_value = "fake_app_obj"

    result = ApplicationController.connect("Untitled - Notepad")

    mock_app_class.assert_called_once_with(backend="uia")
    mock_instance.connect.assert_called_once_with(title="Untitled - Notepad")
    assert result == "fake_app_obj"


@patch("app.tools.desktop.application.Application")
def test_application_launch_failure(mock_app_class):
    mock_app_class.side_effect = Exception("App start failed")

    with pytest.raises(ApplicationActionError, match="Failed to launch notepad.exe"):
        ApplicationController.launch("notepad.exe")
