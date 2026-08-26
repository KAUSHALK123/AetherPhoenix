import logging
from typing import Any, Dict, Optional
from uuid import UUID

from shared.contracts.browser import BrowserResult
from shared.contracts.permission import PermissionType
from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.core.permissions.manager import PermissionManager, get_permission_manager
from app.tools.browser_extension.connection_manager import (
    BrowserExtensionConnectionManager,
    ExtensionNotConnectedError,
    get_connection_manager,
)

logger = get_logger(__name__)

# List of sensitive action types / keys that trigger strict permission enforcement
SENSITIVE_ACTIONS = {"login", "password", "payment", "send_message", "account_change"}


class BrowserExtensionActionError(Exception):
    """Exception raised for browser extension action failures."""

    pass


class BrowserExtensionController:
    """
    Controller for interacting with the user's browser via the AetherPhoenix Chrome Extension.
    Enforces Safe Execution Mode, Permission System rules, and credential protection.
    """

    def __init__(
        self,
        connection_manager: Optional[BrowserExtensionConnectionManager] = None,
        permission_manager: Optional[PermissionManager] = None,
    ):
        self._connection_manager = connection_manager or get_connection_manager()
        self._permission_manager = permission_manager

    @property
    def permission_manager(self) -> Optional[PermissionManager]:
        if self._permission_manager is False:
            return None
        if self._permission_manager is None:
            try:
                self._permission_manager = get_permission_manager()
            except Exception:
                pass
        return self._permission_manager

    async def _check_permission(
        self,
        action: str,
        context: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
        permission_type: PermissionType = PermissionType.BROWSER_ACCESS,
    ) -> None:
        """Enforces permission policy for browser extension execution."""
        pm = self.permission_manager
        if not pm:
            return

        ctx = context or {}
        if workflow_id:
            ctx["workflow_id"] = str(workflow_id)
        if task_id:
            ctx["task_id"] = str(task_id)

        res = pm.check_permission(
            action=f"BrowserExtension: {action}",
            permission_type=permission_type,
            context=ctx,
            workflow_id=workflow_id,
            task_id=task_id,
        )

        if hasattr(res, "__await__"):
            is_approved = await res
        else:
            is_approved = bool(res)

        if not is_approved:
            logger.warning(f"Permission denied for browser extension action: {action}")
            raise PermissionDeniedException(
                f"Permission denied for browser extension action '{action}'."
            )

    def _sanitize_inputs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitizes action input parameters to ensure sensitive data (passwords, tokens)
        are not stored or logged in plain text.
        """
        sanitized = dict(params)
        for key in list(sanitized.keys()):
            if "password" in key.lower() or "secret" in key.lower() or "token" in key.lower():
                sanitized[key] = "******"
        return sanitized

    def _sanitize_outputs(self, data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Ensures extracted content or element outputs do not return captured credentials.
        """
        if not data:
            return data
        sanitized = dict(data)
        if "value" in sanitized and ("password" in str(sanitized.get("selector", "")).lower() or "password" in str(sanitized.get("type", "")).lower()):
            sanitized["value"] = "[MASKED_CREDENTIAL]"
        return sanitized

    async def detect_active_tab(
        self,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Detects and returns active tab information (url, title, tab_id, window_id)."""
        await self._check_permission(
            action="detect_active_tab",
            workflow_id=workflow_id,
            task_id=task_id,
        )

        try:
            res = await self._connection_manager.send_command(
                action="detect_active_tab",
                task_id=str(task_id) if task_id else None,
                workflow_id=str(workflow_id) if workflow_id else None,
            )
            if not res.success:
                return BrowserResult(success=False, error=res.error or "Failed to detect active tab")
            return BrowserResult(success=True, data=self._sanitize_outputs(res.data))
        except ExtensionNotConnectedError as e:
            return BrowserResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"detect_active_tab failed: {e}")
            return BrowserResult(success=False, error=str(e))

    async def read_page_info(
        self,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Reads permitted page information from the currently active tab."""
        await self._check_permission(
            action="read_page_info",
            workflow_id=workflow_id,
            task_id=task_id,
        )

        try:
            res = await self._connection_manager.send_command(
                action="read_page_info",
                task_id=str(task_id) if task_id else None,
                workflow_id=str(workflow_id) if workflow_id else None,
            )
            if not res.success:
                return BrowserResult(success=False, error=res.error or "Failed to read page info")
            return BrowserResult(success=True, data=self._sanitize_outputs(res.data))
        except ExtensionNotConnectedError as e:
            return BrowserResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"read_page_info failed: {e}")
            return BrowserResult(success=False, error=str(e))

    async def navigate(
        self,
        url: str,
        timeout_ms: float = 30000.0,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Navigates the browser extension to a target URL."""
        await self._check_permission(
            action="navigate",
            context={"url": url},
            workflow_id=workflow_id,
            task_id=task_id,
            permission_type=PermissionType.INTERNET,
        )

        try:
            res = await self._connection_manager.send_command(
                action="navigate",
                parameters={"url": url, "timeout_ms": timeout_ms},
                task_id=str(task_id) if task_id else None,
                workflow_id=str(workflow_id) if workflow_id else None,
                timeout_seconds=timeout_ms / 1000.0,
            )
            if not res.success:
                return BrowserResult(success=False, error=res.error or f"Failed to navigate to {url}")
            return BrowserResult(success=True, data=res.data)
        except ExtensionNotConnectedError as e:
            return BrowserResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"navigate to {url} failed: {e}")
            return BrowserResult(success=False, error=str(e))

    async def open_new_tab(
        self,
        url: str,
        active: bool = True,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Opens a new tab in the user's browser."""
        await self._check_permission(
            action="open_new_tab",
            context={"url": url},
            workflow_id=workflow_id,
            task_id=task_id,
            permission_type=PermissionType.INTERNET,
        )

        try:
            res = await self._connection_manager.send_command(
                action="open_new_tab",
                parameters={"url": url, "active": active},
                task_id=str(task_id) if task_id else None,
                workflow_id=str(workflow_id) if workflow_id else None,
            )
            if not res.success:
                return BrowserResult(success=False, error=res.error or f"Failed to open new tab with {url}")
            return BrowserResult(success=True, data=res.data)
        except ExtensionNotConnectedError as e:
            return BrowserResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"open_new_tab failed: {e}")
            return BrowserResult(success=False, error=str(e))

    async def interact(
        self,
        selector: str,
        action: str,
        value: Optional[str] = None,
        timeout_ms: float = 10000.0,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Interacts with page elements (click, fill, submit) via browser extension."""
        # Detect sensitive actions (e.g., login inputs, password fields, payment forms)
        is_sensitive = (
            action.lower() in SENSITIVE_ACTIONS
            or "password" in selector.lower()
            or "credit" in selector.lower()
            or "pay" in selector.lower()
        )

        params = {"selector": selector, "interaction_action": action, "value": value, "timeout_ms": timeout_ms}
        sanitized_params = self._sanitize_inputs(params)

        await self._check_permission(
            action=f"interact_{action}",
            context={"selector": selector, "is_sensitive": is_sensitive, **sanitized_params},
            workflow_id=workflow_id,
            task_id=task_id,
        )

        try:
            res = await self._connection_manager.send_command(
                action="interact",
                parameters=params,
                task_id=str(task_id) if task_id else None,
                workflow_id=str(workflow_id) if workflow_id else None,
                timeout_seconds=timeout_ms / 1000.0,
            )
            if not res.success:
                return BrowserResult(success=False, error=res.error or f"Failed interaction '{action}' on '{selector}'")
            return BrowserResult(success=True, data=self._sanitize_outputs(res.data))
        except ExtensionNotConnectedError as e:
            return BrowserResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"interact failed: {e}")
            return BrowserResult(success=False, error=str(e))

    async def extract_content(
        self,
        include_html: bool = False,
        selector: Optional[str] = None,
        workflow_id: Optional[UUID | str] = None,
        task_id: Optional[UUID | str] = None,
    ) -> BrowserResult:
        """Extracts text or HTML content from the active tab."""
        await self._check_permission(
            action="extract_content",
            context={"include_html": include_html, "selector": selector},
            workflow_id=workflow_id,
            task_id=task_id,
        )

        try:
            res = await self._connection_manager.send_command(
                action="extract_content",
                parameters={"include_html": include_html, "selector": selector},
                task_id=str(task_id) if task_id else None,
                workflow_id=str(workflow_id) if workflow_id else None,
            )
            if not res.success:
                return BrowserResult(success=False, error=res.error or "Failed to extract content")
            return BrowserResult(success=True, data=self._sanitize_outputs(res.data))
        except ExtensionNotConnectedError as e:
            return BrowserResult(success=False, error=str(e))
        except Exception as e:
            logger.error(f"extract_content failed: {e}")
            return BrowserResult(success=False, error=str(e))
