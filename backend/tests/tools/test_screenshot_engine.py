import io
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image
from shared.contracts.screenshot import (
    CaptureRegion,
    CaptureSource,
    ImageFormat,
    ScreenshotRequest,
    ScreenshotResult,
)

from app.core.exceptions import PermissionDeniedException
from app.tools.desktop.screenshot import (
    DesktopScreenshotError,
)
from app.tools.screenshot.engine import ScreenshotCaptureError, ScreenshotEngine


@pytest.fixture
def mock_desktop_img():
    return Image.new("RGBA", (1920, 1080), color=(255, 0, 0, 255))


@pytest.fixture
def mock_region_img():
    return Image.new("RGBA", (400, 300), color=(0, 255, 0, 255))


@pytest.fixture
def mock_permission_manager():
    pm = MagicMock()
    pm.check_permission = MagicMock(return_value=True)
    return pm


@pytest.fixture
def denied_permission_manager():
    pm = MagicMock()
    pm.check_permission = MagicMock(return_value=False)
    return pm


@pytest.mark.asyncio
async def test_capture_desktop_fullscreen(tmp_path, mock_desktop_img):
    engine = ScreenshotEngine(temp_dir=tmp_path)

    with patch.object(
        engine.desktop_controller, "capture_fullscreen", return_value=mock_desktop_img
    ):
        result = await engine.capture_desktop(format=ImageFormat.PNG)

        assert isinstance(result, ScreenshotResult)
        assert result.status == "SUCCESS"
        assert result.source == CaptureSource.DESKTOP
        assert result.format == ImageFormat.PNG
        assert result.width == 1920
        assert result.height == 1080
        assert result.size_bytes > 0
        assert len(result.checksum) == 64
        assert Path(result.filepath).exists()
        assert result.is_temporary is True
        assert result.filepath in engine.get_managed_files()


@pytest.mark.asyncio
async def test_capture_desktop_jpeg_quality(tmp_path, mock_desktop_img):
    engine = ScreenshotEngine(temp_dir=tmp_path)

    with patch.object(
        engine.desktop_controller, "capture_fullscreen", return_value=mock_desktop_img
    ):
        result = await engine.capture_desktop(format=ImageFormat.JPEG, quality=85)

        assert result.format == ImageFormat.JPEG
        assert result.file_name.endswith(".jpg") or result.file_name.endswith(".jpeg")
        assert Path(result.filepath).exists()


@pytest.mark.asyncio
async def test_capture_desktop_custom_output_path(tmp_path, mock_desktop_img):
    engine = ScreenshotEngine(temp_dir=tmp_path)
    custom_dest = str(tmp_path / "custom_dir" / "saved_screen.png")

    with patch.object(
        engine.desktop_controller, "capture_fullscreen", return_value=mock_desktop_img
    ):
        result = await engine.capture_desktop(output_path=custom_dest)

        assert result.filepath == str(Path(custom_dest).resolve())
        assert result.is_temporary is False
        assert Path(custom_dest).exists()
        assert result.filepath not in engine.get_managed_files()


@pytest.mark.asyncio
async def test_capture_region_model(tmp_path, mock_region_img):
    engine = ScreenshotEngine(temp_dir=tmp_path)
    region = CaptureRegion(x=100, y=150, width=400, height=300)

    with patch.object(
        engine.desktop_controller, "capture_region", return_value=mock_region_img
    ) as mock_cap:
        result = await engine.capture_region(region=region)

        assert result.source == CaptureSource.REGION
        assert result.width == 400
        assert result.height == 300
        mock_cap.assert_called_once_with(x=100, y=150, width=400, height=300)


@pytest.mark.asyncio
async def test_capture_region_tuple(tmp_path, mock_region_img):
    engine = ScreenshotEngine(temp_dir=tmp_path)

    with patch.object(
        engine.desktop_controller, "capture_region", return_value=mock_region_img
    ) as mock_cap:
        result = await engine.capture_region(region=(50, 60, 400, 300))

        assert result.width == 400
        assert result.height == 300
        mock_cap.assert_called_once_with(x=50, y=60, width=400, height=300)


@pytest.mark.asyncio
async def test_capture_browser(tmp_path, mock_desktop_img):
    # Prepare mock raw bytes from PIL image
    buf = io.BytesIO()
    mock_desktop_img.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    mock_browser = AsyncMock()
    mock_browser.capture_screenshot = AsyncMock(return_value=raw_bytes)

    engine = ScreenshotEngine(temp_dir=tmp_path, browser_controller=mock_browser)
    result = await engine.capture_browser(full_page=True)

    assert result.source == CaptureSource.BROWSER
    assert result.width == 1920
    assert result.height == 1080
    mock_browser.capture_screenshot.assert_called_once_with(
        output_path=None,
        full_page=True,
        clip=None,
        image_type="png",
        quality=None,
    )


@pytest.mark.asyncio
async def test_capture_permission_denied(tmp_path, denied_permission_manager):
    engine = ScreenshotEngine(
        temp_dir=tmp_path,
        permission_manager=denied_permission_manager,
    )

    with pytest.raises(PermissionDeniedException, match="Permission denied"):
        await engine.capture_desktop()


@pytest.mark.asyncio
async def test_capture_invalid_region_error(tmp_path):
    engine = ScreenshotEngine(temp_dir=tmp_path)

    with pytest.raises(DesktopScreenshotError):
        await engine.capture_region(region=(-10, 0, 100, 100))


@pytest.mark.asyncio
async def test_capture_failure_handling(tmp_path):
    engine = ScreenshotEngine(temp_dir=tmp_path)

    with patch.object(
        engine.desktop_controller,
        "capture_fullscreen",
        side_effect=DesktopScreenshotError("Display device error"),
    ):
        with pytest.raises(ScreenshotCaptureError, match="Capture failed"):
            await engine.capture_desktop()


@pytest.mark.asyncio
async def test_temporary_storage_cleanup_single(tmp_path, mock_desktop_img):
    engine = ScreenshotEngine(temp_dir=tmp_path)

    with patch.object(
        engine.desktop_controller, "capture_fullscreen", return_value=mock_desktop_img
    ):
        result = await engine.capture_desktop()
        path = Path(result.filepath)
        assert path.exists()

        success = engine.cleanup(result.filepath)
        assert success is True
        assert not path.exists()
        assert result.filepath not in engine.get_managed_files()


@pytest.mark.asyncio
async def test_cleanup_all(tmp_path, mock_desktop_img):
    engine = ScreenshotEngine(temp_dir=tmp_path)

    with patch.object(
        engine.desktop_controller, "capture_fullscreen", return_value=mock_desktop_img
    ):
        r1 = await engine.capture_desktop()
        r2 = await engine.capture_desktop()
        r3 = await engine.capture_desktop()

        assert len(engine.get_managed_files()) == 3
        assert Path(r1.filepath).exists()
        assert Path(r2.filepath).exists()
        assert Path(r3.filepath).exists()

        deleted = engine.cleanup_all()
        assert deleted == 3
        assert len(engine.get_managed_files()) == 0
        assert not Path(r1.filepath).exists()
        assert not Path(r2.filepath).exists()
        assert not Path(r3.filepath).exists()


@pytest.mark.asyncio
async def test_cleanup_ttl(tmp_path, mock_desktop_img):
    engine = ScreenshotEngine(temp_dir=tmp_path)

    with patch.object(
        engine.desktop_controller, "capture_fullscreen", return_value=mock_desktop_img
    ):
        r1 = await engine.capture_desktop()
        # Artificially age r1
        engine._managed_files[r1.filepath] = time.time() - 100

        r2 = await engine.capture_desktop()

        deleted = engine.cleanup_all(max_age_seconds=50)
        assert deleted == 1
        assert not Path(r1.filepath).exists()
        assert Path(r2.filepath).exists()

        engine.cleanup(r2.filepath)


@pytest.mark.asyncio
async def test_async_context_manager_cleanup(tmp_path, mock_desktop_img):
    saved_path = None
    async with ScreenshotEngine(temp_dir=tmp_path) as engine:
        with patch.object(
            engine.desktop_controller,
            "capture_fullscreen",
            return_value=mock_desktop_img,
        ):
            res = await engine.capture_desktop()
            saved_path = Path(res.filepath)
            assert saved_path.exists()

    # After exit, file should be cleaned up automatically
    assert not saved_path.exists()


@pytest.mark.asyncio
async def test_sync_context_manager_cleanup(tmp_path, mock_desktop_img):
    saved_path = None
    with ScreenshotEngine(temp_dir=tmp_path) as engine:
        with patch.object(
            engine.desktop_controller,
            "capture_fullscreen",
            return_value=mock_desktop_img,
        ):
            # Capture using async run or helper
            req = ScreenshotRequest(source=CaptureSource.DESKTOP)
            res = await engine.capture(req)
            saved_path = Path(res.filepath)
            assert saved_path.exists()

    assert not saved_path.exists()


@pytest.mark.asyncio
async def test_multiple_consecutive_captures(
    tmp_path, mock_desktop_img, mock_region_img
):
    engine = ScreenshotEngine(temp_dir=tmp_path)

    with (
        patch.object(
            engine.desktop_controller,
            "capture_fullscreen",
            return_value=mock_desktop_img,
        ),
        patch.object(
            engine.desktop_controller, "capture_region", return_value=mock_region_img
        ),
    ):
        results = []
        for i in range(5):
            if i % 2 == 0:
                res = await engine.capture_desktop()
            else:
                res = await engine.capture_region(region=(0, 0, 100, 100))
            results.append(res)

        assert len(results) == 5
        assert len(set(r.checksum for r in results)) >= 1
        assert len(engine.get_managed_files()) == 5

        engine.cleanup_all()
        assert len(engine.get_managed_files()) == 0
