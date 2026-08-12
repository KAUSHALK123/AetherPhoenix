import pyautogui

from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class KeyboardActionError(Exception):
    pass


class KeyboardController:
    """Abstraction for basic keyboard actions."""

    @staticmethod
    def type_text(text: str, interval: float = 0.05):
        logger.info("Keyboard typing text (content hidden for security)")
        try:
            pyautogui.write(text, interval=interval)
        except Exception as e:
            logger.error(f"Keyboard type_text failed: {e}")
            raise KeyboardActionError("Failed to type text") from e

    @staticmethod
    def press_key(key: str):
        logger.info(f"Keyboard press key: {key}")
        try:
            pyautogui.press(key)
        except Exception as e:
            logger.error(f"Keyboard press failed: {e}")
            raise KeyboardActionError(f"Failed to press key: {key}") from e

    @staticmethod
    def hotkey(*keys: str):
        logger.info(f"Keyboard hotkey: {'+'.join(keys)}")
        try:
            pyautogui.hotkey(*keys)
        except Exception as e:
            logger.error(f"Keyboard hotkey failed: {e}")
            raise KeyboardActionError(f"Failed to execute hotkey: {keys}") from e
