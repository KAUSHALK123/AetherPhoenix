# Artifact Storage Documentation

## Overview

The **Artifact Storage** module manages creation, persistence, metadata tracking, retrieval, lifecycle protection, and deletion of files and outputs generated during AetherPhoenix workflow executions (such as PDFs, PPTs, documents, screenshots, research reports, and data outputs).

---

## Architecture & Storage Interfaces

### 1. Abstract Provider Architecture

Artifact Storage uses a pluggable, provider-agnostic interface (`BaseArtifactStorageProvider`), enabling seamless integration with local file systems or cloud object stores (e.g. AWS S3, Azure Blob Storage).

```
ArtifactStorageService (Manager)
          │
          ▼
BaseArtifactStorageProvider (Abstract Base Class)
          │
          ├── LocalFileSystemArtifactStorageProvider (Default Implementation)
          └── [Future Cloud/S3 Storage Provider]
```

### 2. Artifact Contract (`shared/contracts/artifact.py`)

| Field | Type | Description |
|---|---|---|
| `artifact_id` | `UUID` | Unique identifier for the artifact |
| `workflow_id` | `UUID` | Associated workflow ID |
| `task_id` | `UUID \| None` | Associated task ID |
| `name` | `str` | Human-readable file/artifact name |
| `filepath` | `str` | Storage path on disk/provider |
| `artifact_type` | `ArtifactType` | Type (`PDF`, `PPT`, `REPORTS`, `IMAGES`, `SCREENSHOT`, `DATA`, `CODE`, `ZIP`, `LOGS`) |
| `size_bytes` | `int` | Size of artifact in bytes |
| `checksum` | `str \| None` | SHA-256 checksum of content |
| `created_at` | `datetime` | Creation timestamp |
| `metadata` | `dict[str, Any]` | Supplementary metadata (e.g. `is_locked`, `protected`) |

---

## Service API (`ArtifactStorageService`)

Location: `backend/app/services/artifact_storage.py`

### Methods

- `register_artifact(artifact: Artifact, content: bytes | str | None = None, source_path: str | Path | None = None) -> Artifact`:
  Registers an artifact, calculates SHA-256 checksum & size, and persists content to storage.
- `get_artifact(artifact_id: UUID | str) -> Artifact | None`:
  Retrieves artifact metadata.
- `get_artifact_content(artifact_id: UUID | str) -> bytes | None`:
  Reads binary file content.
- `delete_artifact(artifact_id: UUID | str, force: bool = False) -> bool`:
  Deletes artifact file and metadata. Enforces lifecycle protection rules (raises `ValueError` if protected and `force=False`).
- `list_artifacts(workflow_id=None, task_id=None, artifact_type=None) -> list[Artifact]`:
  Queries artifacts filtered by workflow, task, or type.

---

## Worker Agent & Runtime Integration

- **`WorkerAgent`**: Exposes `worker.register_artifact(artifact, content, source_path)`, allowing Worker tools to persist generated artifacts directly into `ArtifactStorageService`.
- **Automatic Task Output Tracking**: When tasks complete with output artifacts in `ExecutionResult.artifacts`, `WorkerAgent` registers them in `ArtifactStorageService` automatically.
