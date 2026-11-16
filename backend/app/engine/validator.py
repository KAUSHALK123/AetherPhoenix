import os
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from shared.contracts.execution import ExecutionResult
from shared.contracts.task import Task, TaskType


class OutputValidationService:
    """
    Service responsible for validating Worker task execution results
    against success criteria, failure criteria, and artifact expectations.
    """

    def validate(
        self, task: Task, result: ExecutionResult
    ) -> Tuple[bool, Dict[str, bool], List[str]]:
        """
        Validates task execution results and returns:
        - is_valid: bool indicating overall validity
        - checks: dict mapping check names to boolean results
        - issues: list of error/warning strings describing failures
        """
        checks: Dict[str, bool] = {}
        issues: List[str] = []

        # 1. Execution Success Check
        checks["execution_success"] = result.success
        if not result.success:
            is_valid = False
            err_msg = result.error.error_message if result.error else "Unknown"
            issues.append(f"Execution marked unsuccessful. Error: {err_msg}")
            return False, checks, issues

        # 2. Artifact Declarations Verification
        artifact_ok, artifact_issues = self._verify_artifacts(task, result)
        checks["artifacts_valid"] = artifact_ok
        issues.extend(artifact_issues)

        # 3. Output Schema & Data Verification
        output_ok, output_issues = self._verify_output_data(task, result)
        checks["output_valid"] = output_ok
        issues.extend(output_issues)

        # 4. Failure Criteria Verification
        failure_detected, failure_issues = self._check_failure_criteria(task, result)
        checks["no_failure_criteria_triggered"] = not failure_detected
        issues.extend(failure_issues)

        # 5. Placeholder / no-op task verification
        is_phase_task = (
            getattr(task, "task_type", None) == TaskType.PHASE
            or "phase" in task.task_name.lower()
        )
        if not is_phase_task:
            is_placeholder_name = any(
                ph in task.task_name.lower()
                for ph in ["evaluate goal context", "execute primary action"]
            )
            is_noop_task = (
                not task.required_tool
                and not result.artifacts
                and self.is_empty_or_noop_output(result.output)
            )
            if is_placeholder_name or is_noop_task:
                checks["no_placeholder_or_noop"] = False
                issues.append(
                    f"Task '{task.task_name}' is a placeholder or no-op task and cannot count as COMPLETED."
                )
            else:
                checks["no_placeholder_or_noop"] = True
        else:
            checks["no_placeholder_or_noop"] = True

        is_valid = (
            checks["execution_success"]
            and checks["artifacts_valid"]
            and checks["output_valid"]
            and checks["no_failure_criteria_triggered"]
            and checks.get("no_placeholder_or_noop", True)
        )

        return is_valid, checks, issues

    @staticmethod
    def is_empty_or_noop_output(output: Any) -> bool:
        """
        Determines whether the provided output is empty or a no-op placeholder.
        """
        if output is None:
            return True
        if isinstance(output, (dict, list, str)):
            if len(output) == 0:
                return True
        if isinstance(output, str):
            return not output.strip()
        if isinstance(output, dict):
            # Check if all keys are purely no-op or placeholder bookkeeping metadata
            meta_keys = {
                "phase",
                "execution_time",
                "metrics",
                "exit_code",
                "timestamp",
            }
            non_meta_keys = [k for k in output.keys() if k not in meta_keys]
            if not non_meta_keys:
                return True
            if len(non_meta_keys) == 1 and non_meta_keys[0] == "status":
                if str(output.get("status", "")).lower() not in (
                    "completed",
                    "success",
                    "ok",
                ):
                    return True
                return False
            # Check if all non-meta values are empty/None/whitespace
            has_substance = False
            for k in non_meta_keys:
                v = output[k]
                if v is not None:
                    if isinstance(v, (str, list, dict)):
                        if len(v) > 0:
                            if isinstance(v, str) and not v.strip():
                                continue
                            has_substance = True
                            break
                    else:
                        has_substance = True
                        break
            return not has_substance
        return False

    @staticmethod
    def validate_pptx_structure(filepath: str | Path) -> Tuple[bool, List[str]]:
        """
        Performs deep structural validation of a Microsoft PowerPoint (.pptx) file:
        1. Confirms file existence and non-zero size.
        2. Validates that the file is an uncorrupted ZIP container.
        3. Confirms presence of '[Content_Types].xml' and 'ppt/presentation.xml'.
        4. Parses with python-pptx to assert at least 1 slide and non-empty slide text.
        """
        path_obj = Path(filepath)
        if not path_obj.exists():
            return False, [f"PPTX file not found: {filepath}"]
        if path_obj.stat().st_size == 0:
            return False, [f"PPTX file is empty (0 bytes): {filepath}"]

        if not zipfile.is_zipfile(path_obj):
            return False, [
                f"Corrupted deliverable: PPTX file is not a valid ZIP container: {filepath}"
            ]

        try:
            with zipfile.ZipFile(path_obj, "r") as zf:
                bad_file = zf.testzip()
                if bad_file:
                    return False, [
                        f"Corrupted deliverable: Corrupted ZIP entry '{bad_file}' in: {filepath}"
                    ]
                names = set(zf.namelist())
                if "[Content_Types].xml" not in names:
                    return False, [
                        f"Corrupted deliverable: Missing '[Content_Types].xml' in OpenXML archive: {filepath}"
                    ]
                if not any(n.startswith("ppt/presentation.xml") for n in names):
                    return False, [
                        f"Corrupted deliverable: Missing 'ppt/presentation.xml' component in: {filepath}"
                    ]
        except Exception as zip_err:
            return False, [
                f"Corrupted deliverable: Failed to inspect ZIP structure: {zip_err}"
            ]

        try:
            import pptx

            prs = pptx.Presentation(str(path_obj))
            if len(prs.slides) == 0:
                return False, [
                    f"Corrupted deliverable: Presentation has 0 slides: {filepath}"
                ]

            total_text_length = 0
            for slide in prs.slides:
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        for paragraph in shape.text_frame.paragraphs:
                            total_text_length += len(paragraph.text.strip())

            if total_text_length == 0:
                return False, [
                    f"Corrupted deliverable: All {len(prs.slides)} slides contain zero text content: {filepath}"
                ]
        except ImportError:
            pass
        except Exception as pptx_err:
            return False, [
                f"Corrupted deliverable: python-pptx failed to parse presentation: {pptx_err}"
            ]

        return True, []

    @staticmethod
    def validate_pdf_structure(filepath: str | Path) -> Tuple[bool, List[str]]:
        """
        Performs deep structural validation of an Adobe Portable Document Format (.pdf) file:
        1. Confirms file existence and non-zero size.
        2. Validates binary header contains '%PDF-'.
        3. Validates EOF marker '%%EOF' is present in trailing bytes.
        4. Parses with pypdf to verify >= 1 readable page and extractable stream.
        """
        path_obj = Path(filepath)
        if not path_obj.exists():
            return False, [f"PDF file not found: {filepath}"]
        if path_obj.stat().st_size == 0:
            return False, [f"PDF file is empty (0 bytes): {filepath}"]

        try:
            with open(path_obj, "rb") as f:
                header = f.read(1024)
                if b"%PDF-" not in header:
                    return False, [
                        f"Corrupted deliverable: Missing valid '%PDF-' header marker in: {filepath}"
                    ]

                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                read_size = min(file_size, 2048)
                f.seek(-read_size, os.SEEK_END)
                tail = f.read(read_size)
                if b"%%EOF" not in tail:
                    return False, [
                        f"Corrupted deliverable: Missing valid '%%EOF' trailer marker in: {filepath}"
                    ]
        except Exception as read_err:
            return False, [
                f"Corrupted deliverable: Failed reading PDF bytes: {read_err}"
            ]

        try:
            import pypdf

            reader = pypdf.PdfReader(str(path_obj))
            if len(reader.pages) == 0:
                return False, [
                    f"Corrupted deliverable: PDF document has 0 pages: {filepath}"
                ]

            has_content = False
            for page in reader.pages:
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        has_content = True
                        break
                    if "/Contents" in page:
                        has_content = True
                        break
                except Exception:
                    pass

            if not has_content:
                return False, [
                    f"Corrupted deliverable: Document has {len(reader.pages)} page(s) but no extractable text or content stream: {filepath}"
                ]
        except ImportError:
            pass
        except Exception as pypdf_err:
            return False, [
                f"Corrupted deliverable: pypdf failed to parse document structure: {pypdf_err}"
            ]

        return True, []

    @staticmethod
    def validate_json_structure(
        data: Any, expected_keys: Optional[List[str]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validates JSON/dict output structure against expected key constraints.
        """
        if not isinstance(data, dict):
            return False, ["Output is not a valid dictionary/JSON object."]
        if expected_keys:
            missing = [k for k in expected_keys if k not in data]
            if missing:
                return False, [
                    f"Corrupted deliverable: Missing required JSON keys: {', '.join(missing)}"
                ]
        return True, []

    def _verify_artifacts(
        self, task: Task, result: ExecutionResult
    ) -> Tuple[bool, List[str]]:
        """
        Checks that required files/artifacts exist, are accessible, non-empty,
        and structurally uncorrupted (validating PDF, PPTX OpenXML packages).
        """
        issues = []
        is_valid = True

        # 1. Check task's designated artifact location
        if task.artifact_location:
            filepath = task.artifact_location
            resolved_task_path = filepath
            if not os.path.isabs(resolved_task_path) and not os.path.exists(
                resolved_task_path
            ):
                try:
                    from app.core.config import get_config

                    cfg = get_config()
                    res = os.path.join(cfg.ARTIFACTS_DIR, resolved_task_path)
                    if os.path.exists(res):
                        resolved_task_path = res
                except Exception:
                    pass

            if not os.path.exists(resolved_task_path):
                is_valid = False
                issues.append(
                    f"Declared task artifact not found on filesystem: {filepath}"
                )
            elif os.path.getsize(resolved_task_path) == 0:
                is_valid = False
                issues.append(f"Declared task artifact is empty (0 bytes): {filepath}")
            else:
                lower_task_path = resolved_task_path.lower()
                if lower_task_path.endswith(".pptx") or lower_task_path.endswith(
                    ".ppt"
                ):
                    pptx_ok, pptx_issues = self.validate_pptx_structure(
                        resolved_task_path
                    )
                    if not pptx_ok:
                        is_valid = False
                        issues.extend(pptx_issues)
                elif lower_task_path.endswith(".pdf"):
                    pdf_ok, pdf_issues = self.validate_pdf_structure(resolved_task_path)
                    if not pdf_ok:
                        is_valid = False
                        issues.extend(pdf_issues)

        # 2. Check result artifacts
        if result.artifacts:
            for artifact in result.artifacts:
                art_path = artifact.filepath
                resolved_art_path = art_path
                if not os.path.isabs(resolved_art_path) and not os.path.exists(
                    resolved_art_path
                ):
                    try:
                        from app.core.config import get_config

                        cfg = get_config()
                        res = os.path.join(cfg.ARTIFACTS_DIR, resolved_art_path)
                        if os.path.exists(res):
                            resolved_art_path = res
                    except Exception:
                        pass

                if not os.path.exists(resolved_art_path):
                    is_valid = False
                    issues.append(
                        f"Result artifact file not found: {artifact.filepath}"
                    )
                elif os.path.getsize(resolved_art_path) == 0:
                    is_valid = False
                    issues.append(
                        f"Result artifact file is empty (0 bytes): {artifact.filepath}"
                    )
                else:
                    lower_art_path = resolved_art_path.lower()
                    if lower_art_path.endswith(".pptx") or lower_art_path.endswith(
                        ".ppt"
                    ):
                        pptx_ok, pptx_issues = self.validate_pptx_structure(
                            resolved_art_path
                        )
                        if not pptx_ok:
                            is_valid = False
                            issues.extend(pptx_issues)
                    elif lower_art_path.endswith(".pdf"):
                        pdf_ok, pdf_issues = self.validate_pdf_structure(
                            resolved_art_path
                        )
                        if not pdf_ok:
                            is_valid = False
                            issues.extend(pdf_issues)

        # 3. Check result output dict for file paths
        if isinstance(result.output, dict):
            for k in (
                "filepath",
                "path",
                "output_path",
                "file_path",
                "presentation_path",
            ):
                v = result.output.get(k)
                if isinstance(v, str) and (v.endswith(".pptx") or v.endswith(".pdf")):
                    resolved_v = v
                    if not os.path.isabs(resolved_v) and not os.path.exists(resolved_v):
                        try:
                            from app.core.config import get_config

                            cfg = get_config()
                            res = os.path.join(cfg.ARTIFACTS_DIR, resolved_v)
                            if os.path.exists(res):
                                resolved_v = res
                        except Exception:
                            pass
                    if not os.path.exists(resolved_v):
                        is_valid = False
                        issues.append(
                            f"Result output artifact not found on filesystem: {v}"
                        )
                    elif os.path.getsize(resolved_v) == 0:
                        is_valid = False
                        issues.append(
                            f"Corrupted deliverable: Output artifact is empty (0 bytes): {v}"
                        )
                    else:
                        lower_v = resolved_v.lower()
                        if lower_v.endswith(".pptx") or lower_v.endswith(".ppt"):
                            pptx_ok, pptx_issues = self.validate_pptx_structure(
                                resolved_v
                            )
                            if not pptx_ok:
                                is_valid = False
                                issues.extend(pptx_issues)
                        elif lower_v.endswith(".pdf"):
                            pdf_ok, pdf_issues = self.validate_pdf_structure(resolved_v)
                            if not pdf_ok:
                                is_valid = False
                                issues.extend(pdf_issues)

        return is_valid, issues

    def _verify_output_data(
        self, task: Task, result: ExecutionResult
    ) -> Tuple[bool, List[str]]:
        """
        Validates the execution output against expected outputs and success criteria.
        """
        issues = []
        is_valid = True

        has_artifacts = bool(
            result.artifacts
            or (
                task.artifact_location
                and os.path.exists(task.artifact_location)
                and os.path.getsize(task.artifact_location) > 0
            )
        )

        # Check expected output heuristic
        if task.expected_output:
            if not result.output and not has_artifacts:
                is_valid = False
                issues.append(
                    "Expected output was defined, but no output data "
                    "or artifacts were returned."
                )
            elif self.is_empty_or_noop_output(result.output) and not has_artifacts:
                is_valid = False
                issues.append(
                    "Expected output was defined, but tool returned empty or no-op output."
                )

        # Check success criteria
        if task.success_criteria:
            for criterion in task.success_criteria:
                criterion_lower = criterion.lower()

                # Check "file: <path>" criterion
                if criterion_lower.startswith("file:"):
                    filepath = criterion[5:].strip()
                    if not os.path.exists(filepath):
                        is_valid = False
                        issues.append(
                            f"Success criteria failed: File does not exist ({filepath})"
                        )

                # Check "contains: <key>" criterion
                elif criterion_lower.startswith("contains:"):
                    expected_key = criterion[9:].strip()
                    if not result.output or expected_key not in result.output:
                        is_valid = False
                        issues.append(
                            f"Success criteria failed: Output missing "
                            f"required key '{expected_key}'"
                        )

                # Default validation: check if result output is populated
                else:
                    if not result.output and not result.artifacts:
                        is_valid = False
                        issues.append(
                            f"Success criteria failed: '{criterion}' "
                            "could not be verified (empty output)"
                        )
                    elif (
                        self.is_empty_or_noop_output(result.output)
                        and not result.artifacts
                    ):
                        is_valid = False
                        issues.append(
                            f"Success criteria failed: '{criterion}' "
                            "could not be verified (no-op output)"
                        )

        return is_valid, issues

    def _check_failure_criteria(
        self, task: Task, result: ExecutionResult
    ) -> Tuple[bool, List[str]]:
        """
        Checks if any failure criteria have been triggered in output or logs.
        """
        issues = []
        failure_detected = False

        if task.failure_criteria:
            for criterion in task.failure_criteria:
                # Check if criterion exists in output
                if result.output:
                    for key, val in result.output.items():
                        if (
                            criterion.lower() in str(key).lower()
                            or criterion.lower() in str(val).lower()
                        ):
                            failure_detected = True
                            issues.append(
                                f"Failure criteria triggered: "
                                f"'{criterion}' found in output"
                            )
                            break

                # Check if criterion exists in execution logs
                if result.logs:
                    for log in result.logs:
                        if criterion.lower() in log.lower():
                            failure_detected = True
                            issues.append(
                                f"Failure criteria triggered: "
                                f"'{criterion}' found in logs"
                            )
                            break

        return failure_detected, issues
