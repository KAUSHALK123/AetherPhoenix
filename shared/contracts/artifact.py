from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ArtifactType(str, Enum):
    """Supported artifact types."""

    PPT = "PPT"
    PDF = "PDF"
    REPORTS = "REPORTS"
    IMAGES = "IMAGES"
    LOGS = "LOGS"
    CODE = "CODE"
    ZIP = "ZIP"
    SCREENSHOT = "SCREENSHOT"
    DATA = "DATA"


class Artifact(BaseModel):
    """Artifact contract representing generated outputs in the system."""

    artifact_id: UUID = Field(default_factory=uuid4)
    workflow_id: UUID
    task_id: UUID | None = None
    name: str
    filepath: str
    artifact_type: ArtifactType
    size_bytes: int = Field(default=0, ge=0)
    checksum: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @staticmethod
    def compute_checksum(content: bytes) -> str:
        """Computes SHA-256 checksum for byte content."""
        import hashlib

        return hashlib.sha256(content).hexdigest()
