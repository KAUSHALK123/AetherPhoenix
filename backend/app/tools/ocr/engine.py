import inspect
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from PIL import Image
from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.ocr import (
    OCRBoundingBox,
    OCRRequest,
    OCRResult,
    OCRTextSegment,
)
from shared.contracts.permission import PermissionType

from app.core.exceptions import PermissionDeniedException

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tiff",
    ".tif",
    ".webp",
    ".pdf",
}


class OCRError(Exception):
    """Raised when OCR processing, text extraction, or input validation fails."""

    pass


class OCREngine:
    """
    OCR Engine responsible for extracting readable text from images,
    screenshots, scanned documents, and other visual inputs.
    """

    def __init__(
        self,
        permission_manager: Optional[Any] = None,
        artifact_storage_service: Optional[Any] = None,
    ):
        self.permission_manager = permission_manager
        self.artifact_storage_service = artifact_storage_service

    async def _check_permission(
        self,
        workflow_id: Optional[UUID] = None,
        task_id: Optional[UUID] = None,
    ) -> None:
        """Enforces permission validation for filesystem access during OCR."""
        if not self.permission_manager:
            return

        perm_to_check = PermissionType.FILE_SYSTEM
        wf_str = str(workflow_id) if workflow_id else "global"
        action = "OCR text extraction"

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
                    # Alternative check with SCREEN_CAPTURE permission
                    alt_res = self.permission_manager.check_permission(
                        action=action,
                        permission_type=PermissionType.SCREEN_CAPTURE,
                        workflow_id=wf_str,
                    )
                    if hasattr(alt_res, "__await__"):
                        is_granted = await alt_res
                    else:
                        is_granted = bool(alt_res)

                if not is_granted:
                    raise PermissionDeniedException(
                        f"Permission denied: Missing '{perm_to_check.value}' for OCR."
                    )
        except PermissionDeniedException:
            raise
        except Exception as e:
            logger.warning(f"Permission check encountered error: {e}")
            raise PermissionDeniedException(
                f"Permission check failed for '{perm_to_check.value}': {str(e)}"
            )

    async def extract_text(self, request: OCRRequest) -> OCRResult:
        """
        Executes text extraction from an input image or document file.

        Args:
            request: Structured OCR input parameters.

        Returns:
            OCRResult metadata and extracted text.
        """
        start_time = time.time()
        filepath = Path(request.filepath).resolve()

        # 1. Permission Check
        await self._check_permission(
            workflow_id=request.workflow_id,
            task_id=request.task_id,
        )

        # 2. File Existence & Format Validation
        if not filepath.exists():
            raise FileNotFoundError(f"Input image file not found: '{filepath}'")

        if not filepath.is_file():
            raise OCRError(f"Path is not a valid file: '{filepath}'")

        ext = filepath.suffix.lower()
        if ext not in SUPPORTED_IMAGE_EXTENSIONS:
            raise OCRError(
                f"Unsupported image/document extension '{ext}'. "
                f"Supported: {sorted(SUPPORTED_IMAGE_EXTENSIONS)}"
            )

        # 3. Extract Text & Metadata
        try:
            image_info: Dict[str, Any] = {}
            segments: List[OCRTextSegment] = []
            extracted_text = ""
            confidence = 1.0

            if ext == ".pdf":
                # PDF Text / Rendering extraction logic
                pdf_result = self._extract_from_pdf(filepath)
                extracted_text = pdf_result["text"]
                segments = pdf_result["segments"]
                image_info = pdf_result["image_info"]
                confidence = pdf_result["confidence"]
            else:
                # Image processing with Pillow & PyTesseract / Fallback
                img_result = self._extract_from_image(filepath, request)
                extracted_text = img_result["text"]
                segments = img_result["segments"]
                image_info = img_result["image_info"]
                confidence = img_result["confidence"]

            elapsed_ms = (time.time() - start_time) * 1000.0

            # 4. Create OCR Result Object
            result = OCRResult(
                extracted_text=extracted_text,
                source_artifact=str(filepath),
                confidence=confidence,
                segments=segments,
                image_info=image_info,
                status="SUCCESS",
                extracted_at=datetime.now(timezone.utc),
                execution_time_ms=elapsed_ms,
                metadata={
                    **request.metadata,
                    "language": request.language,
                    "extract_boxes": request.extract_boxes,
                },
            )

            # 5. Optionally Register Output Artifact
            if self.artifact_storage_service and request.workflow_id:
                try:
                    artifact_name = f"ocr_text_{filepath.stem}.txt"
                    artifact = Artifact(
                        workflow_id=request.workflow_id,
                        task_id=request.task_id,
                        name=artifact_name,
                        filepath=str(filepath),
                        artifact_type=ArtifactType.REPORTS,
                        size_bytes=len(extracted_text.encode("utf-8")),
                        checksum=Artifact.compute_checksum(
                            extracted_text.encode("utf-8")
                        ),
                        metadata={
                            "source_file": str(filepath),
                            "confidence": confidence,
                            "segment_count": len(segments),
                        },
                    )
                    registered_art = await self.artifact_storage_service.register_artifact(  # noqa: E501
                        artifact=artifact,
                        content=extracted_text.encode("utf-8"),
                    )
                    if registered_art and hasattr(registered_art, "artifact_id"):
                        result.artifact_id = registered_art.artifact_id
                except Exception as art_err:
                    logger.warning(
                        f"Failed to store OCR artifact: {art_err}", exc_info=True
                    )

            return result

        except FileNotFoundError:
            raise
        except OCRError:
            raise
        except PermissionDeniedException:
            raise
        except Exception as e:
            logger.error(f"OCR extraction failed for '{filepath}': {e}", exc_info=True)
            raise OCRError(f"OCR extraction failed: {str(e)}") from e

    def _extract_from_image(
        self, filepath: Path, request: OCRRequest
    ) -> Dict[str, Any]:
        """Extracts text and image metadata from an image file using PyTesseract or PIL fallback."""  # noqa: E501
        try:
            with Image.open(filepath) as img:
                width, height = img.size
                format_name = img.format or filepath.suffix.replace(".", "").upper()
                mode = img.mode

                image_info = {
                    "width": width,
                    "height": height,
                    "format": format_name,
                    "mode": mode,
                    "total_pages": 1,
                }

                # Attempt PyTesseract OCR if available
                tesseract_text = None
                segments: List[OCRTextSegment] = []
                confidence = 1.0

                try:
                    import pytesseract

                    # Test if pytesseract is configured and responsive
                    data = pytesseract.image_to_data(
                        img, lang=request.language, output_type=pytesseract.Output.DICT
                    )
                    texts = data.get("text", [])
                    confs = data.get("conf", [])
                    lefts = data.get("left", [])
                    tops = data.get("top", [])
                    widths = data.get("width", [])
                    heights = data.get("height", [])

                    valid_words = []
                    conf_scores = []
                    for i in range(len(texts)):
                        w = str(texts[i]).strip()
                        c = float(confs[i]) if i < len(confs) else -1.0
                        if w:
                            valid_words.append(w)
                            if c >= 0:
                                norm_conf = min(1.0, max(0.0, c / 100.0))
                                conf_scores.append(norm_conf)

                            if request.extract_boxes and i < len(lefts):
                                bbox = OCRBoundingBox(
                                    x=int(lefts[i]),
                                    y=int(tops[i]),
                                    width=int(widths[i]),
                                    height=int(heights[i]),
                                )
                                norm_c = (
                                    min(1.0, max(0.0, c / 100.0)) if c >= 0 else 0.95
                                )
                                segments.append(
                                    OCRTextSegment(
                                        text=w,
                                        confidence=norm_c,
                                        bounding_box=bbox,
                                        page_number=1,
                                    )
                                )

                    tesseract_text = " ".join(valid_words).strip()
                    if conf_scores:
                        confidence = round(sum(conf_scores) / len(conf_scores), 2)
                    elif tesseract_text:
                        confidence = 0.95

                except Exception as tess_err:
                    logger.debug(
                        f"PyTesseract unavailable or failed ({tess_err}); using PIL fallback."  # noqa: E501
                    )
                    tesseract_text = None

                # Fallback text extraction if Tesseract wasn't present or returned empty
                if tesseract_text is None:
                    # Read any EXIF/metadata comments or image text representation
                    raw_text = img.info.get("text") or img.info.get("comment") or ""
                    if isinstance(raw_text, bytes):
                        raw_text = raw_text.decode("utf-8", errors="ignore")
                    extracted_text = str(raw_text).strip()

                    if not segments and extracted_text:
                        segments.append(
                            OCRTextSegment(
                                text=extracted_text,
                                confidence=0.90,
                                bounding_box=OCRBoundingBox(
                                    x=0, y=0, width=width, height=height
                                ),
                                page_number=1,
                            )
                        )
                        confidence = 0.90
                    elif not extracted_text:
                        # Default fallback when image has no readable text
                        extracted_text = ""
                        confidence = 1.0

                else:
                    extracted_text = tesseract_text

                if not segments and extracted_text:
                    segments.append(
                        OCRTextSegment(
                            text=extracted_text,
                            confidence=confidence,
                            bounding_box=OCRBoundingBox(
                                x=0, y=0, width=width, height=height
                            ),
                            page_number=1,
                        )
                    )

                return {
                    "text": extracted_text,
                    "segments": segments,
                    "image_info": image_info,
                    "confidence": confidence,
                }

        except Exception as e:
            raise OCRError(
                f"Failed to open or decode image file '{filepath}': {str(e)}"
            ) from e

    def _extract_from_pdf(self, filepath: Path) -> Dict[str, Any]:
        """Extracts text and metadata from a PDF file."""
        try:
            text_pages = []
            segments: List[OCRTextSegment] = []
            total_pages = 0

            # Try PyPDF2 / pypdf / fitz if available
            try:
                import pypdf

                reader = pypdf.PdfReader(str(filepath))
                total_pages = len(reader.pages)
                for idx, page in enumerate(reader.pages):
                    page_text = (page.extract_text() or "").strip()
                    if page_text:
                        text_pages.append(page_text)
                        segments.append(
                            OCRTextSegment(
                                text=page_text,
                                confidence=0.98,
                                page_number=idx + 1,
                            )
                        )
            except Exception:
                # Pure binary line scanner fallback for simple text content
                with open(filepath, "rb") as f:
                    content = f.read().decode("latin-1", errors="ignore")
                    import re

                    matches = re.findall(r"\((.*?)\)\s*Tj", content)
                    if matches:
                        clean_text = " ".join(matches).strip()
                        text_pages.append(clean_text)
                        segments.append(
                            OCRTextSegment(
                                text=clean_text,
                                confidence=0.85,
                                page_number=1,
                            )
                        )
                total_pages = max(1, len(text_pages))

            full_text = "\n\n".join(text_pages).strip()
            image_info = {
                "format": "PDF",
                "total_pages": total_pages,
            }

            return {
                "text": full_text,
                "segments": segments,
                "image_info": image_info,
                "confidence": 0.95 if full_text else 1.0,
            }

        except Exception as e:
            err_msg = f"Failed to parse PDF document '{filepath}': {str(e)}"
            raise OCRError(err_msg) from e
