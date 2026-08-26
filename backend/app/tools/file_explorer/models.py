from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class OpenFolderRequest(BaseModel):
    """Request schema for opening a folder in the OS file explorer."""

    path: str = Field(..., description="The directory path to open.")


class OpenFileRequest(BaseModel):
    """Request schema for opening a file with the default desktop application."""

    path: str = Field(..., description="The file path to open.")


class RevealArtifactRequest(BaseModel):
    """Request schema for revealing an artifact in the OS file explorer."""

    artifact_id: Optional[str] = Field(
        default=None, description="Unique ID of the artifact to reveal."
    )
    artifact_name: Optional[str] = Field(
        default=None, description="Name of the artifact to reveal."
    )
    filepath: Optional[str] = Field(
        default=None, description="Direct file path of the artifact to reveal."
    )


class CreateFolderRequest(BaseModel):
    """Request schema for creating a folder in the file system."""

    path: str = Field(..., description="The directory path to create.")
    create_parents: bool = Field(
        default=True,
        description="Whether to create parent directories if they do not exist.",
    )


class DetectExistenceRequest(BaseModel):
    """Request schema for checking whether a file or directory exists."""

    path: str = Field(..., description="The file or directory path to check.")


class FileMetadataRequest(BaseModel):
    """Request schema for retrieving metadata of a file or directory."""

    path: str = Field(..., description="The file or directory path to inspect.")


class FileMetadataResponse(BaseModel):
    """Structured response containing basic metadata of a file or directory."""

    name: str = Field(..., description="Name of the file or directory.")
    filepath: str = Field(..., description="Absolute or resolved path.")
    exists: bool = Field(..., description="Whether the path exists.")
    is_dir: bool = Field(..., description="True if directory, False if file.")
    size_bytes: int = Field(default=0, description="Size in bytes.")
    extension: str = Field(default="", description="File extension if applicable.")
    created_at: Optional[str] = Field(
        default=None, description="Creation timestamp in ISO format."
    )
    modified_at: Optional[str] = Field(
        default=None, description="Last modification timestamp in ISO format."
    )


class FileExplorerActionResult(BaseModel):
    """Structured output result for File Explorer operations."""

    success: bool = Field(..., description="Whether the action succeeded.")
    action: str = Field(..., description="The action performed.")
    target_path: Optional[str] = Field(
        default=None, description="Target path operated upon."
    )
    message: str = Field(..., description="Human-readable status or result message.")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata produced by the action."
    )
