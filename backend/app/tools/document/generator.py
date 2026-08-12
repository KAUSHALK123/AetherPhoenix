import csv
import hashlib
import io
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID

from shared.contracts.artifact import Artifact, ArtifactType
from shared.contracts.document import (
    DocumentElement,
    DocumentElementType,
    DocumentFormat,
    DocumentGenerationResult,
    DocumentSection,
    StructuredDocumentInput,
)

from app.core.exceptions import (
    InputValidationException,
    ToolExecutionException,
)
from app.core.logging import get_logger
from app.core.permissions import PermissionManager

logger = get_logger(__name__)


class DocumentGenerator:
    """
    Core Document Generator capability for converting structured content into
    Markdown, Text, HTML, JSON, and CSV documents.
    """

    FORMAT_EXTENSIONS: Dict[DocumentFormat, List[str]] = {
        DocumentFormat.MARKDOWN: [".md", ".markdown"],
        DocumentFormat.TEXT: [".txt", ".text"],
        DocumentFormat.HTML: [".html", ".htm"],
        DocumentFormat.JSON: [".json"],
        DocumentFormat.CSV: [".csv"],
    }

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        allowed_base_dirs: Optional[List[Path]] = None,
    ) -> None:
        self.permission_manager = permission_manager
        self.allowed_base_dirs = allowed_base_dirs or []

    def validate_output_path(
        self,
        output_path: str,
        expected_format: DocumentFormat = DocumentFormat.MARKDOWN,
        overwrite: bool = False,
    ) -> Path:
        """
        Validates and sanitizes output file path to ensure path safety,
        correct file extensions, base directory restrictions, and overwrite policy.
        """
        if not output_path or not output_path.strip():
            raise InputValidationException(
                message="Output path cannot be empty.",
                details={"output_path": output_path},
            )

        if "\0" in output_path:
            raise InputValidationException(
                message="Invalid output path containing null byte.",
                details={"output_path": output_path},
            )

        try:
            path_obj = Path(output_path).expanduser().resolve()
        except Exception as exc:
            raise InputValidationException(
                message=f"Failed to resolve target output path: {str(exc)}",
                details={"output_path": output_path, "error": str(exc)},
            ) from exc

        # Check format extension
        allowed_exts = self.FORMAT_EXTENSIONS.get(expected_format, [".md", ".txt"])
        if path_obj.suffix.lower() not in allowed_exts:
            raise InputValidationException(
                message=(
                    f"Output path extension '{path_obj.suffix}' does not match "
                    f"expected format '{expected_format.value}' "
                    f"(Allowed: {allowed_exts})."
                ),
                details={"output_path": str(path_obj), "format": expected_format.value},
            )

        # Restrict destination path if allowed_base_dirs specified
        if self.allowed_base_dirs:
            resolved_bases = [b.resolve() for b in self.allowed_base_dirs]
            is_allowed = any(
                path_obj == base or base in path_obj.parents for base in resolved_bases
            )
            if not is_allowed:
                raise InputValidationException(
                    message=(
                        f"Target path '{path_obj}' is outside approved directories."
                    ),
                    details={"output_path": str(path_obj)},
                )

        # Existing file handling
        if path_obj.exists() and not overwrite:
            raise InputValidationException(
                message=(
                    f"Target file already exists at '{path_obj}' and "
                    "overwrite is False."
                ),
                details={"output_path": str(path_obj)},
            )

        # Create parent directory safely
        try:
            path_obj.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            raise InputValidationException(
                message=f"Cannot create directory for path '{path_obj}': {str(exc)}",
                details={"output_path": str(path_obj)},
            ) from exc

        return path_obj

    def check_permissions(self, workflow_id: Optional[UUID]) -> None:
        """Enforces permission check if PermissionManager is provided."""
        if self.permission_manager and workflow_id:
            logger.info(
                f"Enforcing permission check for workflow {workflow_id}"
            )
            for p in ["FILE_WRITE", "FILE_SYSTEM_WRITE", "FILE_SYSTEM"]:
                try:
                    self.permission_manager.enforce_permission(p, workflow_id)
                    return
                except Exception:
                    continue
            # Fallback enforce
            self.permission_manager.enforce_permission("FILE_SYSTEM", workflow_id)

    def generate(self, input_data: StructuredDocumentInput) -> DocumentGenerationResult:
        """
        Generates a document from structured content input.

        Args:
            input_data: Validated StructuredDocumentInput model.

        Returns:
            DocumentGenerationResult containing generation status and metadata.
        """
        start_time = time.time()

        # 1. Permission check
        self.check_permissions(input_data.workflow_id)

        # 2. Path validation
        target_path = self.validate_output_path(
            output_path=input_data.output_path,
            expected_format=input_data.format,
            overwrite=input_data.overwrite,
        )

        # 3. Content validation
        has_title = bool(input_data.title and input_data.title.strip())
        has_content = bool(input_data.content and input_data.content.strip())
        has_elements = bool(input_data.elements)
        has_sections = bool(input_data.sections)

        if not (has_title or has_content or has_elements or has_sections):
            raise InputValidationException(
                message=(
                    "Document input must contain at least a title or "
                    "non-empty content elements/sections."
                ),
                details={"output_path": str(target_path)},
            )

        # 4. Render document content
        try:
            rendered_text = self._render_document(input_data)
        except Exception as exc:
            raise ToolExecutionException(
                message=f"Failed to render document: {str(exc)}",
                details={"format": input_data.format.value, "error": str(exc)},
            ) from exc

        # 5. Write to output file
        try:
            target_path.write_text(rendered_text, encoding="utf-8")
        except Exception as exc:
            raise ToolExecutionException(
                message=(
                    f"Failed to write output document to file '{target_path}': "
                    f"{str(exc)}"
                ),
                details={"output_path": str(target_path), "error": str(exc)},
            ) from exc

        # 6. Compute file metadata
        content_bytes = rendered_text.encode("utf-8")
        file_size_bytes = len(content_bytes)
        sha256_checksum = hashlib.sha256(content_bytes).hexdigest()
        lines = rendered_text.splitlines()
        line_count = len(lines)
        word_count = len(rendered_text.split())

        duration_ms = (time.time() - start_time) * 1000.0
        logger.info(
            f"Successfully generated {input_data.format.value} document "
            f"at '{target_path}' ({file_size_bytes} bytes, {word_count} words, "
            f"{duration_ms:.2f}ms)"
        )

        return DocumentGenerationResult(
            status="SUCCESS",
            filepath=str(target_path.resolve()),
            file_name=target_path.name,
            file_size_bytes=file_size_bytes,
            format=input_data.format,
            checksum_sha256=sha256_checksum,
            created_at=datetime.now(timezone.utc),
            word_count=word_count,
            line_count=line_count,
            metadata={
                **input_data.metadata,
                "duration_ms": duration_ms,
                "has_sections": len(input_data.sections),
                "has_elements": len(input_data.elements),
            },
            workflow_id=input_data.workflow_id,
            task_id=input_data.task_id,
        )

    def create_artifact(
        self,
        result: DocumentGenerationResult,
        workflow_id: UUID,
        task_id: Optional[UUID] = None,
    ) -> Artifact:
        """Constructs an Artifact object from document generation results."""
        return Artifact(
            workflow_id=workflow_id,
            task_id=task_id or result.task_id,
            name=result.file_name,
            filepath=result.filepath,
            artifact_type=ArtifactType.REPORTS,
            size_bytes=result.file_size_bytes,
            checksum=result.checksum_sha256,
            metadata={
                "format": result.format.value,
                "word_count": result.word_count,
                "line_count": result.line_count,
                "generated_at": result.created_at.isoformat(),
            },
        )

    def _render_document(self, input_data: StructuredDocumentInput) -> str:
        """Routes rendering logic to specific format generators."""
        fmt = input_data.format
        if fmt == DocumentFormat.MARKDOWN:
            return self._render_markdown(input_data)
        elif fmt == DocumentFormat.TEXT:
            return self._render_text(input_data)
        elif fmt == DocumentFormat.HTML:
            return self._render_html(input_data)
        elif fmt == DocumentFormat.JSON:
            return self._render_json(input_data)
        elif fmt == DocumentFormat.CSV:
            return self._render_csv(input_data)
        else:
            return self._render_markdown(input_data)

    def _render_markdown(self, input_data: StructuredDocumentInput) -> str:
        lines: List[str] = []

        if input_data.title:
            lines.append(f"# {input_data.title}")
            lines.append("")

        if input_data.subtitle:
            lines.append(f"*{input_data.subtitle}*")
            lines.append("")

        if input_data.author:
            lines.append(f"**Author:** {input_data.author}")
            lines.append("")

        if input_data.content:
            lines.append(input_data.content.strip())
            lines.append("")

        for elem in input_data.elements:
            lines.extend(self._render_markdown_element(elem))

        for section in input_data.sections:
            lines.extend(self._render_markdown_section(section))

        return "\n".join(lines).strip() + "\n"

    def _render_markdown_element(self, elem: DocumentElement) -> List[str]:
        lines: List[str] = []
        etype = elem.element_type

        if etype == DocumentElementType.HEADING:
            level = "#" * (elem.level or 1)
            lines.append(f"{level} {elem.text or ''}")
            lines.append("")
        elif etype == DocumentElementType.PARAGRAPH:
            text = elem.text or ""
            if elem.bold:
                text = f"**{text}**"
            lines.append(text)
            lines.append("")
        elif etype == DocumentElementType.LIST:
            items = elem.items or []
            for i, item in enumerate(items, 1):
                prefix = f"{i}." if elem.is_numbered else "-"
                lines.append(f"{prefix} {item}")
            lines.append("")
        elif etype == DocumentElementType.TABLE:
            headers = elem.headers or []
            rows = elem.rows or []
            if headers:
                lines.append("| " + " | ".join(headers) + " |")
                lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            for row in rows:
                lines.append("| " + " | ".join(row) + " |")
            lines.append("")
        elif etype == DocumentElementType.CODE_BLOCK:
            lang = elem.language or ""
            code = elem.code or elem.text or ""
            lines.append(f"```{lang}")
            lines.append(code)
            lines.append("```")
            lines.append("")
        elif etype == DocumentElementType.KEY_VALUE:
            data = elem.data or {}
            for k, v in data.items():
                lines.append(f"- **{k}**: {v}")
            lines.append("")

        return lines

    def _render_markdown_section(self, section: DocumentSection) -> List[str]:
        lines: List[str] = []
        if section.title:
            level = "#" * (section.level or 2)
            lines.append(f"{level} {section.title}")
            lines.append("")
        if section.content:
            lines.append(section.content.strip())
            lines.append("")
        for elem in section.elements:
            lines.extend(self._render_markdown_element(elem))
        return lines

    def _render_text(self, input_data: StructuredDocumentInput) -> str:
        lines: List[str] = []

        if input_data.title:
            lines.append(input_data.title.upper())
            lines.append("=" * len(input_data.title))
            lines.append("")

        if input_data.subtitle:
            lines.append(input_data.subtitle)
            lines.append("")

        if input_data.author:
            lines.append(f"Author: {input_data.author}")
            lines.append("")

        if input_data.content:
            lines.append(input_data.content.strip())
            lines.append("")

        for elem in input_data.elements:
            lines.extend(self._render_text_element(elem))

        for section in input_data.sections:
            if section.title:
                lines.append(section.title)
                lines.append("-" * len(section.title))
                lines.append("")
            if section.content:
                lines.append(section.content.strip())
                lines.append("")
            for elem in section.elements:
                lines.extend(self._render_text_element(elem))

        return "\n".join(lines).strip() + "\n"

    def _render_text_element(self, elem: DocumentElement) -> List[str]:
        lines: List[str] = []
        etype = elem.element_type

        if etype == DocumentElementType.HEADING:
            lines.append((elem.text or "").upper())
            lines.append("")
        elif etype == DocumentElementType.PARAGRAPH:
            lines.append(elem.text or "")
            lines.append("")
        elif etype == DocumentElementType.LIST:
            items = elem.items or []
            for i, item in enumerate(items, 1):
                prefix = f"{i}." if elem.is_numbered else "*"
                lines.append(f"  {prefix} {item}")
            lines.append("")
        elif etype == DocumentElementType.TABLE:
            headers = elem.headers or []
            rows = elem.rows or []
            if headers:
                lines.append("\t".join(headers))
            for row in rows:
                lines.append("\t".join(row))
            lines.append("")
        elif etype == DocumentElementType.CODE_BLOCK:
            lines.append(elem.code or elem.text or "")
            lines.append("")
        elif etype == DocumentElementType.KEY_VALUE:
            data = elem.data or {}
            for k, v in data.items():
                lines.append(f"  {k}: {v}")
            lines.append("")

        return lines

    def _render_html(self, input_data: StructuredDocumentInput) -> str:
        body_html: List[str] = []

        if input_data.title:
            body_html.append(f"<h1>{input_data.title}</h1>")
        if input_data.subtitle:
            body_html.append(f"<p><em>{input_data.subtitle}</em></p>")
        if input_data.author:
            body_html.append(f"<p><strong>Author:</strong> {input_data.author}</p>")
        if input_data.content:
            body_html.append(f"<p>{input_data.content.strip()}</p>")

        for elem in input_data.elements:
            body_html.append(self._render_html_element(elem))

        for section in input_data.sections:
            sec_html = []
            if section.title:
                tag = f"h{min(section.level + 1, 6)}"
                sec_html.append(f"<{tag}>{section.title}</{tag}>")
            if section.content:
                sec_html.append(f"<p>{section.content.strip()}</p>")
            for elem in section.elements:
                sec_html.append(self._render_html_element(elem))
            body_html.append(f"<section>{''.join(sec_html)}</section>")

        joined_body = "\n  ".join(body_html)
        html_doc = (
            "<!DOCTYPE html>\n"
            "<html>\n"
            "<head>\n"
            '  <meta charset="utf-8">\n'
            f"  <title>{input_data.title or 'Document'}</title>\n"
            "</head>\n"
            "<body>\n"
            f"  {joined_body}\n"
            "</body>\n"
            "</html>\n"
        )
        return html_doc

    def _render_html_element(self, elem: DocumentElement) -> str:
        etype = elem.element_type
        if etype == DocumentElementType.HEADING:
            tag = f"h{min(elem.level or 1, 6)}"
            return f"<{tag}>{elem.text or ''}</{tag}>"
        elif etype == DocumentElementType.PARAGRAPH:
            text = elem.text or ""
            if elem.bold:
                text = f"<strong>{text}</strong>"
            return f"<p>{text}</p>"
        elif etype == DocumentElementType.LIST:
            tag = "ol" if elem.is_numbered else "ul"
            items_html = "".join([f"<li>{it}</li>" for it in elem.items or []])
            return f"<{tag}>{items_html}</{tag}>"
        elif etype == DocumentElementType.TABLE:
            headers_html = "".join([f"<th>{h}</th>" for h in elem.headers or []])
            rows_html = "".join(
                [
                    f"<tr>{''.join([f'<td>{cell}</td>' for cell in row])}</tr>"
                    for row in elem.rows or []
                ]
            )
            return (
                f"<table><thead><tr>{headers_html}</tr></thead>"
                f"<tbody>{rows_html}</tbody></table>"
            )
        elif etype == DocumentElementType.CODE_BLOCK:
            return f"<pre><code>{elem.code or elem.text or ''}</code></pre>"
        elif etype == DocumentElementType.KEY_VALUE:
            items_html = "".join(
                [
                    f"<li><strong>{k}:</strong> {v}</li>"
                    for k, v in (elem.data or {}).items()
                ]
            )
            return f"<ul>{items_html}</ul>"
        return ""

    def _render_json(self, input_data: StructuredDocumentInput) -> str:
        data_dict = input_data.model_dump(mode="json")
        return json.dumps(data_dict, indent=2)

    def _render_csv(self, input_data: StructuredDocumentInput) -> str:
        output_buffer = io.StringIO()
        writer = csv.writer(output_buffer)

        # Look for table element first
        table_elem = None
        for elem in input_data.elements:
            if elem.element_type == DocumentElementType.TABLE:
                table_elem = elem
                break

        if table_elem:
            if table_elem.headers:
                writer.writerow(table_elem.headers)
            for row in table_elem.rows or []:
                writer.writerow(row)
        else:
            # Fallback to key-value rows or metadata / general elements
            writer.writerow(["Key", "Value"])
            if input_data.title:
                writer.writerow(["Title", input_data.title])
            if input_data.subtitle:
                writer.writerow(["Subtitle", input_data.subtitle])
            if input_data.author:
                writer.writerow(["Author", input_data.author])
            if input_data.content:
                writer.writerow(["Content", input_data.content])
            for elem in input_data.elements:
                if elem.element_type == DocumentElementType.KEY_VALUE and elem.data:
                    for k, v in elem.data.items():
                        writer.writerow([k, str(v)])
                elif elem.text:
                    writer.writerow([elem.element_type.value, elem.text])

        return output_buffer.getvalue()
