from typing import Optional, Tuple

try:
    import pyautogui
except (ImportError, Exception):
    pyautogui = None
from PIL import Image

from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class DesktopScreenshotError(Exception):
    """Raised when a desktop screenshot capture operation fails."""

    pass


class DesktopScreenshotController:
    """
    Abstraction for desktop screenshot capture operations using PyAutoGUI and Pillow.
    Supports full-screen capture, region capture, and resolution query.
    """

    @staticmethod
    def get_screen_size() -> Tuple[int, int]:
        """
        Retrieves the primary screen width and height.

        Returns:
            Tuple of (width, height) in pixels.
        """
        try:
            size = pyautogui.size()
            return (int(size[0]), int(size[1]))
        except Exception as e:
            logger.warning(f"Could not determine screen size via pyautogui: {e}")
            return (1920, 1080)

    @staticmethod
    def capture_fullscreen(output_path: Optional[str] = None) -> Image.Image:
        """
        Captures the entire desktop display.

        Args:
            output_path: Optional file path to save the captured image directly.

        Returns:
            PIL Image instance of the captured screen.

        Raises:
            DesktopScreenshotError: If screen capture fails.
        """
        logger.info("Capturing desktop full-screen screenshot")
        try:
            image = pyautogui.screenshot(output_path)
            if image is None and output_path:
                image = Image.open(output_path)
            logger.info(f"Captured desktop full-screen: {image.width}x{image.height}")
            return image
        except Exception as e:
            logger.error(f"Desktop full-screen capture failed: {e}")
            raise DesktopScreenshotError(
                f"Failed to capture full screen: {str(e)}"
            ) from e

    @staticmethod
    def capture_region(
        x: int,
        y: int,
        width: int,
        height: int,
        output_path: Optional[str] = None,
    ) -> Image.Image:
        """
        Captures a specific coordinate region of the desktop display.

        Args:
            x: Top-left X coordinate (pixels).
            y: Top-left Y coordinate (pixels).
            width: Region width (pixels).
            height: Region height (pixels).
            output_path: Optional file path to save the captured image.

        Returns:
            PIL Image instance of the captured region.

        Raises:
            DesktopScreenshotError: If dimensions are invalid or capture fails.
        """
        logger.info(f"Capturing desktop region at ({x}, {y}, {width}, {height})")

        if width <= 0 or height <= 0:
            raise DesktopScreenshotError(
                f"Invalid region dimensions: {width}x{height}. Both must be > 0."
            )
        if x < 0 or y < 0:
            raise DesktopScreenshotError(
                f"Invalid region coordinates: ({x}, {y}). Cannot be negative."
            )

        try:
            # pyautogui.screenshot takes region=(left, top, width, height)
            region_tuple = (int(x), int(y), int(width), int(height))
            image = pyautogui.screenshot(output_path, region=region_tuple)
            if image is None and output_path:
                image = Image.open(output_path)
            logger.info(
                f"Successfully captured desktop region: {image.width}x{image.height}"
            )
            return image
        except Exception as e:
            logger.error(
                f"Desktop region capture failed at ({x}, {y}, {width}, {height}): {e}"
            )
            raise DesktopScreenshotError(
                f"Failed to capture desktop region: {str(e)}"
            ) from e
