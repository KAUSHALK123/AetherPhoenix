import hashlib
import inspect
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

from PIL import Image
from shared.contracts.permission import PermissionType
from shared.contracts.screenshot import (
    CaptureRegion,
    CaptureSource,
    ImageFormat,
    ScreenshotRequest,
    ScreenshotResult,
)

from app.core.exceptions import PermissionDeniedException
from app.core.logging.logger import get_logger
from app.tools.desktop.screenshot import (
    DesktopScreenshotController,
    DesktopScreenshotError,
)

logger = get_logger(__name__)


class ScreenshotCaptureError(Exception):
    """Raised when screenshot capture, encoding, or storage fails."""

    pass


class ScreenshotEngine:
    """
    Central Screenshot Engine for capturing, validating, encoding,
    storing, and managing temporary screenshot artifacts.
    """

    def __init__(
        self,
        permission_manager: Optional[Any] = None,
        temp_dir: Optional[Union[str, Path]] = None,
        desktop_controller: Optional[DesktopScreenshotController] = None,
        browser_controller: Optional[Any] = None,
    ):
        self.permission_manager = permission_manager
        self.desktop_controller = desktop_controller or DesktopScreenshotController()
        self.browser_controller = browser_controller

        # Setup isolated managed temp directory
        if temp_dir:
            self.temp_dir = Path(temp_dir)
        else:
            self.temp_dir = Path(tempfile.gettempdir()) / "aether_phoenix_screenshots"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Track managed temporary screenshot file paths and creation timestamps
        self._managed_files: Dict[str, float] = {}

    async def _check_permission(
        self,
        source: CaptureSource,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
    ) -> None:
        """
        Enforces permission validation for screen capture.
        """
        if not self.permission_manager:
            return

        perm_to_check = (
            PermissionType.BROWSER_ACCESS
            if source == CaptureSource.BROWSER
            else PermissionType.SCREEN_CAPTURE
        )

        wf_str = str(workflow_id) if workflow_id else "global"
        action = f"Screenshot capture from {source.value}"

        try:
            if hasattr(self.permission_manager, "check_permission"):
                check_fn = self.permission_manager.check_permission
                if inspect.iscoroutinefunction(check_fn):
                    is_granted = await check_fn(
                        action=action,
                        permission_type=perm_to_check,
                        workflow_id=wf_str,
                        context={"task_id": str(task_id) if task_id else None},
                    )
                else:
                    res = check_fn(
                        action=action,
                        permission_type=perm_to_check,
                        workflow_id=wf_str,
                    )
                    if hasattr(res, "__await__"):
                        is_granted = await res
                    else:
                        is_granted = bool(res)

                if not is_granted:
                    # Fallback check with DESKTOP_AUTOMATION
                    if perm_to_check == PermissionType.SCREEN_CAPTURE:
                        alt_res = self.permission_manager.check_permission(
                            action=action,
                            permission_type=PermissionType.DESKTOP_AUTOMATION,
                            workflow_id=wf_str,
                        )
                        if hasattr(alt_res, "__await__"):
                            is_granted = await alt_res
                        else:
                            is_granted = bool(alt_res)

                if not is_granted:
                    raise PermissionDeniedException(
                        f"Permission denied: Missing '{perm_to_check.value}'."
                    )
        except PermissionDeniedException:
            raise
        except Exception as e:
            logger.warning(f"Permission check encountered error: {e}")
            raise PermissionDeniedException(
                f"Permission check failed for '{perm_to_check.value}': {str(e)}"
            )

    def _generate_temp_path(self, format: ImageFormat) -> Path:
        """Generates a secure, unique destination path in the managed temp directory."""
        ext = format.value.lower()
        if ext == "jpeg":
            ext = "jpg"
        file_name = f"screenshot_{uuid4().hex}.{ext}"
        return self.temp_dir / file_name

    @staticmethod
    def _compute_checksum(filepath: str | Path) -> str:
        """Calculates SHA-256 checksum of an image file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _save_and_encode_image(
        self,
        image: Image.Image,
        output_path: Path,
        format: ImageFormat,
        quality: Optional[int] = None,
    ) -> None:
        """Encodes and saves a PIL Image with format and quality options."""
        save_format = format.value.upper()
        if save_format == "JPEG" and image.mode in ("RGBA", "LA", "P"):
            # JPEG doesn't support alpha transparency; convert to RGB
            background = Image.new("RGB", image.size, (255, 255, 255))
            if image.mode == "RGBA":
                background.paste(image, mask=image.split()[3])
            else:
                background.paste(image)
            image = background

        save_kwargs = {}
        if quality and save_format in ("JPEG", "WEBP"):
            save_kwargs["quality"] = quality

        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(str(output_path), format=save_format, **save_kwargs)

    async def capture(self, request: ScreenshotRequest) -> ScreenshotResult:
        """
        Executes a screenshot capture based on the provided ScreenshotRequest.

        Args:
            request: Structured screenshot capture parameters.

        Returns:
            ScreenshotResult metadata contract.
        """
        start_time = time.time()
        logger.info(
            f"Executing screenshot capture (source={request.source.value}, "
            f"format={request.format.value})"
        )

        # 1. Permission check
        await self._check_permission(
            source=request.source,
            workflow_id=request.workflow_id,
            task_id=request.task_id,
        )

        # 2. Determine target file path
        is_temp = request.output_path is None
        if request.output_path:
            dest_path = Path(request.output_path)
            dest_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            dest_path = self._generate_temp_path(request.format)

        try:
            # 3. Capture image according to source
            if request.source == CaptureSource.BROWSER:
                if not self.browser_controller:
                    raise ScreenshotCaptureError(
                        "Browser controller is not configured."
                    )

                clip_dict = None
                if request.region:
                    clip_dict = {
                        "x": float(request.region.x),
                        "y": float(request.region.y),
                        "width": float(request.region.width),
                        "height": float(request.region.height),
                    }

                # Check if browser controller has capture_screenshot method
                if hasattr(self.browser_controller, "capture_screenshot"):
                    raw_bytes = await self.browser_controller.capture_screenshot(
                        output_path=None,
                        full_page=request.full_page,
                        clip=clip_dict,
                        image_type=(
                            "jpeg" if request.format == ImageFormat.JPEG else "png"
                        ),
                        quality=request.quality,
                    )
                    import io

                    img = Image.open(io.BytesIO(raw_bytes))
                    self._save_and_encode_image(
                        img, dest_path, request.format, request.quality
                    )
                else:
                    raise ScreenshotCaptureError(
                        "Browser controller lacks screenshot capability."
                    )

            elif request.source == CaptureSource.REGION:
                if not request.region:
                    raise ScreenshotCaptureError(
                        "Region parameters required for REGION capture."
                    )
                img = self.desktop_controller.capture_region(
                    x=request.region.x,
                    y=request.region.y,
                    width=request.region.width,
                    height=request.region.height,
                )
                self._save_and_encode_image(
                    img, dest_path, request.format, request.quality
                )

            else:  # DESKTOP
                if request.region:
                    img = self.desktop_controller.capture_region(
                        x=request.region.x,
                        y=request.region.y,
                        width=request.region.width,
                        height=request.region.height,
                    )
                else:
                    img = self.desktop_controller.capture_fullscreen()
                self._save_and_encode_image(
                    img, dest_path, request.format, request.quality
                )

            # 4. Validation and Metadata extraction
            if not dest_path.exists():
                raise ScreenshotCaptureError(
                    f"Failed to create screenshot file at {dest_path}"
                )

            size_bytes = dest_path.stat().st_size
            if size_bytes == 0:
                raise ScreenshotCaptureError("Screenshot file is empty (0 bytes).")

            with Image.open(dest_path) as saved_img:
                width, height = saved_img.size

            checksum = self._compute_checksum(dest_path)
            abs_filepath = str(dest_path.resolve())

            if is_temp:
                self._managed_files[abs_filepath] = time.time()

            elapsed_ms = (time.time() - start_time) * 1000.0
            logger.info(
                f"Screenshot successfully captured: {dest_path.name} "
                f"({width}x{height}, {size_bytes} bytes, {elapsed_ms:.1f}ms)"
            )

            return ScreenshotResult(
                filepath=abs_filepath,
                file_name=dest_path.name,
                source=request.source,
                format=request.format,
                width=width,
                height=height,
                size_bytes=size_bytes,
                checksum=checksum,
                captured_at=datetime.now(timezone.utc),
                status="SUCCESS",
                is_temporary=is_temp,
                metadata={
                    **request.metadata,
                    "execution_time_ms": elapsed_ms,
                    "quality": request.quality,
                },
            )

        except PermissionDeniedException:
            raise
        except Exception as e:
            logger.error(f"Screenshot capture failed: {str(e)}")
            if is_temp and dest_path.exists():
                try:
                    dest_path.unlink()
                except Exception:
                    pass
            raise ScreenshotCaptureError(f"Capture failed: {str(e)}") from e

    async def capture_desktop(
        self,
        format: ImageFormat = ImageFormat.PNG,
        output_path: Optional[str] = None,
        quality: Optional[int] = None,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScreenshotResult:
        """Convenience method for desktop full-screen capture."""
        req = ScreenshotRequest(
            source=CaptureSource.DESKTOP,
            format=format,
            output_path=output_path,
            quality=quality,
            workflow_id=workflow_id,
            task_id=task_id,
            metadata=metadata or {},
        )
        return await self.capture(req)

    async def capture_region(
        self,
        region: Union[CaptureRegion, Tuple[int, int, int, int], Dict[str, int]],
        format: ImageFormat = ImageFormat.PNG,
        output_path: Optional[str] = None,
        quality: Optional[int] = None,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScreenshotResult:
        """Convenience method for region-based capture."""
        try:
            if isinstance(region, (tuple, list)):
                if len(region) != 4:
                    raise DesktopScreenshotError(
                        f"Region tuple must have 4 elements, got {len(region)}"
                    )
                cap_region = CaptureRegion(
                    x=region[0], y=region[1], width=region[2], height=region[3]
                )
            elif isinstance(region, dict):
                cap_region = CaptureRegion(**region)
            else:
                cap_region = region
        except Exception as e:
            raise DesktopScreenshotError(
                f"Invalid region specification: {str(e)}"
            ) from e

        req = ScreenshotRequest(
            source=CaptureSource.REGION,
            region=cap_region,
            format=format,
            output_path=output_path,
            quality=quality,
            workflow_id=workflow_id,
            task_id=task_id,
            metadata=metadata or {},
        )
        return await self.capture(req)

    async def capture_browser(
        self,
        browser_tool: Optional[Any] = None,
        region: Optional[CaptureRegion] = None,
        full_page: bool = False,
        format: ImageFormat = ImageFormat.PNG,
        output_path: Optional[str] = None,
        quality: Optional[int] = None,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScreenshotResult:
        """Convenience method for browser screenshot capture."""
        if browser_tool:
            self.browser_controller = browser_tool

        req = ScreenshotRequest(
            source=CaptureSource.BROWSER,
            region=region,
            full_page=full_page,
            format=format,
            output_path=output_path,
            quality=quality,
            workflow_id=workflow_id,
            task_id=task_id,
            metadata=metadata or {},
        )
        return await self.capture(req)

    def cleanup(self, filepath_or_id: Union[str, UUID]) -> bool:
        """
        Cleans up a single managed screenshot file.

        Args:
            filepath_or_id: File path or screenshot identifier.

        Returns:
            True if file was deleted, False otherwise.
        """
        path_str = str(filepath_or_id)
        target_path = None

        if path_str in self._managed_files:
            target_path = Path(path_str)
            del self._managed_files[path_str]
        else:
            p = Path(path_str)
            if p.exists():
                target_path = p

        if target_path and target_path.exists():
            try:
                target_path.unlink()
                logger.info(f"Cleaned up temporary screenshot: {target_path}")
                return True
            except Exception as e:
                logger.warning(f"Failed to delete screenshot file {target_path}: {e}")
                return False
        return False

    def cleanup_all(self, max_age_seconds: Optional[float] = None) -> int:
        """
        Cleans up all managed temporary screenshots.
        Optional max_age_seconds filters for files older than threshold.

        Args:
            max_age_seconds: Optional age threshold in seconds.

        Returns:
            Number of cleaned up files.
        """
        now = time.time()
        deleted_count = 0
        to_remove = []

        for path_str, created_at in list(self._managed_files.items()):
            if max_age_seconds is None or (now - created_at) >= max_age_seconds:
                p = Path(path_str)
                if p.exists():
                    try:
                        p.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.warning(f"Error removing {p}: {e}")
                to_remove.append(path_str)

        for path_str in to_remove:
            self._managed_files.pop(path_str, None)

        logger.info(f"Cleaned up {deleted_count} temporary screenshot file(s).")
        return deleted_count

    def get_managed_files(self) -> List[str]:
        """Returns list of currently managed temporary screenshot file paths."""
        return list(self._managed_files.keys())

    # Context Manager support for scoped lifecycle cleanup
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_all()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_all()
