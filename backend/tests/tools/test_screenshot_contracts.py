from uuid import uuid4

import pytest
from pydantic import ValidationError
from shared.contracts.screenshot import (
    CaptureRegion,
    CaptureSource,
    ImageFormat,
    ScreenshotRequest,
    ScreenshotResult,
)


def test_capture_region_valid():
    region = CaptureRegion(x=10, y=20, width=800, height=600)
    assert region.x == 10
    assert region.y == 20
    assert region.width == 800
    assert region.height == 600
    assert region.to_tuple() == (10, 20, 800, 600)
    assert region.to_bbox() == (10, 20, 810, 620)


def test_capture_region_validation_failures():
    # Negative coordinates
    with pytest.raises(ValidationError):
        CaptureRegion(x=-1, y=0, width=100, height=100)

    with pytest.raises(ValidationError):
        CaptureRegion(x=0, y=-5, width=100, height=100)

    # Zero or negative dimensions
    with pytest.raises(ValidationError):
        CaptureRegion(x=0, y=0, width=0, height=100)

    with pytest.raises(ValidationError):
        CaptureRegion(x=0, y=0, width=100, height=-10)


def test_screenshot_request_defaults():
    req = ScreenshotRequest()
    assert req.source == CaptureSource.DESKTOP
    assert req.region is None
    assert req.format == ImageFormat.PNG
    assert req.quality is None
    assert req.output_path is None
    assert req.full_page is False
    assert req.metadata == {}


def test_screenshot_request_format_normalization():
    req_jpg = ScreenshotRequest(format="jpg")
    assert req_jpg.format == ImageFormat.JPEG

    req_jpeg = ScreenshotRequest(format="jpeg")
    assert req_jpeg.format == ImageFormat.JPEG

    req_webp = ScreenshotRequest(format="webp")
    assert req_webp.format == ImageFormat.WEBP


def test_screenshot_result_contract():
    shot_id = uuid4()
    result = ScreenshotResult(
        screenshot_id=shot_id,
        filepath="/tmp/screenshot.png",
        file_name="screenshot.png",
        source=CaptureSource.DESKTOP,
        format=ImageFormat.PNG,
        width=1920,
        height=1080,
        size_bytes=1048576,
        checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )

    assert result.screenshot_id == shot_id
    assert result.filepath == "/tmp/screenshot.png"
    assert result.status == "SUCCESS"
    assert result.is_temporary is True
    assert result.width == 1920
    assert result.height == 1080

    # Test serialization
    dump = result.model_dump(mode="json")
    assert dump["format"] == "PNG"
    assert dump["source"] == "DESKTOP"
    assert dump["status"] == "SUCCESS"
