from pydantic import BaseModel, Field


class ListFilesRequest(BaseModel):
    """Request schema for listing files in a directory."""

    path: str = Field(..., description="The directory path to list.")
    recursive: bool = Field(default=False, description="Whether to list recursively.")


class ReadFileRequest(BaseModel):
    """Request schema for reading a file."""

    path: str = Field(..., description="The file path to read.")


class CreateDirectoryRequest(BaseModel):
    """Request schema for creating a directory."""

    path: str = Field(..., description="The directory path to create.")
    create_parents: bool = Field(
        default=True,
        description="Whether to create parent directories if they don't exist.",
    )


class CopyFileRequest(BaseModel):
    """Request schema for copying a file."""

    source_path: str = Field(..., description="The source file path.")
    destination_path: str = Field(..., description="The destination file path.")


class MoveFileRequest(BaseModel):
    """Request schema for moving a file or directory."""

    source_path: str = Field(..., description="The source file or directory path.")
    destination_path: str = Field(
        ..., description="The destination file or directory path."
    )


class RenameFileRequest(BaseModel):
    """Request schema for renaming a file or directory."""

    path: str = Field(..., description="The current file or directory path.")
    new_name: str = Field(..., description="The new name for the file or directory.")


class DeleteFileRequest(BaseModel):
    """Request schema for deleting a file or directory."""

    path: str = Field(..., description="The file or directory path to delete.")
    recursive: bool = Field(
        default=False, description="Whether to delete recursively (for directories)."
    )
