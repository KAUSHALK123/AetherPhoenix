import pyautogui

from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class MouseActionError(Exception):
    pass


class MouseController:
    """Abstraction for basic mouse actions."""

    @staticmethod
    def click(x: int, y: int, button: str = "left"):
        logger.info(f"Mouse click at ({x}, {y}) with {button} button")
        try:
            pyautogui.click(x=x, y=y, button=button)
        except Exception as e:
            logger.error(f"Mouse click failed: {e}")
            raise MouseActionError(f"Failed to click at ({x}, {y})") from e

    @staticmethod
    def move_to(x: int, y: int, duration: float = 0.5):
        logger.info(f"Mouse move to ({x}, {y}) over {duration}s")
        try:
            pyautogui.moveTo(x=x, y=y, duration=duration)
        except Exception as e:
            logger.error(f"Mouse move failed: {e}")
            raise MouseActionError(f"Failed to move to ({x}, {y})") from e

    @staticmethod
    def scroll(clicks: int):
        logger.info(f"Mouse scroll {clicks} clicks")
        try:
            pyautogui.scroll(clicks)
        except Exception as e:
            logger.error(f"Mouse scroll failed: {e}")
            raise MouseActionError(f"Failed to scroll {clicks} clicks") from e
