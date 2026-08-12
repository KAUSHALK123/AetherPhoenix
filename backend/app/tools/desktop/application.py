from pywinauto import Application

from app.core.logging.logger import get_logger

logger = get_logger(__name__)


class ApplicationActionError(Exception):
    pass


class ApplicationController:
    """Abstraction for supported application interactions."""

    @staticmethod
    def launch(app_path: str):
        logger.info(f"Launching application: {app_path}")
        try:
            app = Application(backend="uia").start(app_path)
            return app
        except Exception as e:
            logger.error(f"Failed to launch application: {e}")
            raise ApplicationActionError(f"Failed to launch {app_path}") from e

    @staticmethod
    def connect(title: str):
        logger.info(f"Connecting to application with title: {title}")
        try:
            app = Application(backend="uia").connect(title=title)
            return app
        except Exception as e:
            logger.error(f"Failed to connect to application: {e}")
            raise ApplicationActionError(f"Failed to connect to {title}") from e
