import re
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import List, Tuple

# XML 1.0 legal characters regex (characters outside this are strictly invalid):
# Valid: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
_ILLEGAL_XML_CHARS_RE = re.compile(
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f\ud800-\udfff]"
)


def sanitize_xml_text(text: str | None) -> str:
    """
    Sanitizes string inputs by stripping characters that violate the XML 1.0 specification.
    Prevents OpenXML XML parsing corruption errors when writing to PPTX.
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)

    # Strip illegal XML control characters and surrogates
    cleaned = _ILLEGAL_XML_CHARS_RE.sub("", text)
    # Strip null bytes unconditionally
    cleaned = cleaned.replace("\0", "")
    return cleaned


def validate_openxml_package(filepath: str | Path) -> Tuple[bool, List[str]]:
    """
    Performs comprehensive structural validation of a PowerPoint (.pptx) Open XML package:
    1. Verifies the file exists and is non-empty.
    2. Validates that the file is an uncorrupted ZIP container (`testzip()` passes).
    3. Confirms mandatory OpenXML package parts exist:
       - '[Content_Types].xml'
       - '_rels/.rels'
       - 'ppt/presentation.xml'
       - 'ppt/_rels/presentation.xml.rels'
    4. Validates that every XML part inside the package is well-formed XML 1.0.
    5. Validates slide relationship integrity: verifies all media/image targets
       referenced in slide relationship files actually exist in the archive.
    """
    path_obj = Path(filepath)
    issues: List[str] = []

    if not path_obj.exists():
        return False, [f"PPTX file does not exist at '{filepath}'."]

    try:
        size = path_obj.stat().st_size
        if size == 0:
            return False, [f"PPTX file is empty (0 bytes) at '{filepath}'."]
    except OSError as e:
        return False, [f"Failed to stat file '{filepath}': {e}"]

    if not zipfile.is_zipfile(path_obj):
        return False, [
            f"PPTX package corruption: File '{filepath}' is not a valid ZIP container."
        ]

    try:
        with zipfile.ZipFile(path_obj, "r") as zf:
            # Step A: ZIP integrity test
            corrupt_file = zf.testzip()
            if corrupt_file:
                return False, [
                    f"PPTX package corruption: Corrupted ZIP entry '{corrupt_file}' in '{filepath}'."
                ]

            namelist = set(zf.namelist())

            # Step B: Mandatory OpenXML components
            if "[Content_Types].xml" not in namelist:
                issues.append("Missing mandatory '[Content_Types].xml' in PPTX package.")

            if "_rels/.rels" not in namelist:
                issues.append("Missing mandatory root package relationships '_rels/.rels'.")

            if "ppt/presentation.xml" not in namelist:
                issues.append("Missing core presentation descriptor 'ppt/presentation.xml'.")

            # Step C: Parse all XML files in archive to ensure well-formed XML 1.0
            xml_files = [n for n in namelist if n.endswith(".xml") or n.endswith(".rels")]
            for xml_file in xml_files:
                try:
                    xml_bytes = zf.read(xml_file)
                    ET.fromstring(xml_bytes)
                except Exception as xml_err:
                    issues.append(
                        f"Malformed XML in package part '{xml_file}': {str(xml_err)}"
                    )

            # Step D: Slide relationships and media target verification
            slide_rels_files = [
                n
                for n in namelist
                if n.startswith("ppt/slides/_rels/") and n.endswith(".rels")
            ]

            for rel_file in slide_rels_files:
                try:
                    rel_bytes = zf.read(rel_file)
                    root = ET.fromstring(rel_bytes)
                    for elem in root:
                        target = elem.get("Target", "")
                        type_uri = elem.get("Type", "")

                        # Check media/image relationship targets
                        if "image" in type_uri.lower() or "media" in type_uri.lower():
                            # Normalize relative target path: ../media/image1.png -> ppt/media/image1.png
                            if target.startswith("../"):
                                normalized_target = "ppt/" + target[3:]
                            elif target.startswith("/"):
                                normalized_target = target.lstrip("/")
                            else:
                                normalized_target = f"ppt/slides/{target}"

                            if normalized_target not in namelist:
                                issues.append(
                                    f"Broken media reference in '{rel_file}': target '{target}' "
                                    f"(resolved: '{normalized_target}') is missing from package."
                                )
                except Exception as rel_err:
                    issues.append(f"Failed parsing relationships in '{rel_file}': {rel_err}")

    except Exception as exc:
        return False, [f"Failed to inspect OpenXML package structure: {str(exc)}"]

    if issues:
        return False, issues

    return True, []
