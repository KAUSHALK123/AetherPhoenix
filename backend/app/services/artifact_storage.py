import logging
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from threading import Lock
from uuid import UUID

from shared.contracts.artifact import Artifact, ArtifactType

from app.core.config import get_config

logger = logging.getLogger(__name__)


class BaseArtifactStorageProvider(ABC):
    """
    Abstract base interface for pluggable artifact storage providers.
    """

    @abstractmethod
    async def save_artifact(
        self,
        artifact: Artifact,
        content: bytes | str | None = None,
        source_path: str | Path | None = None,
    ) -> Artifact:
        """Saves artifact binary/text content or source file and registers metadata."""
        pass

    @abstractmethod
    async def get_artifact_metadata(self, artifact_id: UUID | str) -> Artifact | None:
        """Retrieves metadata of an artifact by ID."""
        pass

    @abstractmethod
    async def read_artifact_content(self, artifact_id: UUID | str) -> bytes | None:
        """Reads binary file content of an artifact by ID."""
        pass

    @abstractmethod
    async def delete_artifact(
        self, artifact_id: UUID | str, force: bool = False
    ) -> bool:
        """Deletes an artifact according to lifecycle rules."""
        pass

    @abstractmethod
    async def list_artifacts(
        self,
        workflow_id: UUID | str | None = None,
        task_id: UUID | str | None = None,
        artifact_type: ArtifactType | str | None = None,
    ) -> list[Artifact]:
        """Lists artifacts filtered by workflow, task, or type."""
        pass


class LocalFileSystemArtifactStorageProvider(BaseArtifactStorageProvider):
    """
    Default local file system implementation of BaseArtifactStorageProvider.
    """

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self._lock = Lock()
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            cfg = get_config()
            self.base_dir = Path(cfg.ARTIFACTS_DIR)

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._registry: dict[UUID, Artifact] = {}

    def _to_uuid(self, val: UUID | str) -> UUID:
        """Utility method to safely convert string or UUID to UUID."""
        if isinstance(val, UUID):
            return val
        return UUID(str(val))

    async def save_artifact(
        self,
        artifact: Artifact,
        content: bytes | str | None = None,
        source_path: str | Path | None = None,
    ) -> Artifact:
        """
        Persists artifact content/file on local disk and registers metadata.
        """
        with self._lock:
            artifact_id = artifact.artifact_id
            workflow_dir = self.base_dir / str(artifact.workflow_id)
            workflow_dir.mkdir(parents=True, exist_ok=True)

            target_filename = f"{artifact_id}_{artifact.name}"
            target_path = workflow_dir / target_filename

            file_bytes: bytes = b""

            if source_path:
                src = Path(source_path)
                if not src.exists():
                    raise FileNotFoundError(f"Source file not found: {source_path}")
                file_bytes = src.read_bytes()
                shutil.copy2(src, target_path)
            elif content is not None:
                if isinstance(content, str):
                    file_bytes = content.encode("utf-8")
                else:
                    file_bytes = content
                target_path.write_bytes(file_bytes)
            elif Path(artifact.filepath).exists():
                existing = Path(artifact.filepath)
                file_bytes = existing.read_bytes()
                if existing.resolve() != target_path.resolve():
                    shutil.copy2(existing, target_path)
            else:
                # Placeholder metadata registration without file content
                target_path = Path(artifact.filepath)
                file_bytes = b""

            checksum = artifact.checksum
            if file_bytes and not checksum:
                checksum = Artifact.compute_checksum(file_bytes)

            size_bytes = len(file_bytes) if file_bytes else artifact.size_bytes

            updated_artifact = artifact.model_copy(
                update={
                    "filepath": str(target_path.resolve()),
                    "size_bytes": size_bytes,
                    "checksum": checksum,
                }
            )

            self._registry[artifact_id] = updated_artifact
            logger.info(
                f"LocalFS Storage saved artifact {artifact_id} "
                f"('{updated_artifact.name}', {size_bytes} bytes) to {target_path}"
            )
            return updated_artifact

    async def get_artifact_metadata(self, artifact_id: UUID | str) -> Artifact | None:
        """Retrieves registered artifact metadata."""
        art_id = self._to_uuid(artifact_id)
        with self._lock:
            art = self._registry.get(art_id)
            if art:
                return art.model_copy(deep=True)
            return None

    async def read_artifact_content(self, artifact_id: UUID | str) -> bytes | None:
        """Reads raw binary content of stored artifact."""
        art_id = self._to_uuid(artifact_id)
        with self._lock:
            art = self._registry.get(art_id)
            if not art:
                logger.warning(f"Artifact {art_id} not found in registry")
                return None

            fp = Path(art.filepath)
            if not fp.exists():
                logger.warning(f"Artifact file missing on disk: {fp}")
                return None

            return fp.read_bytes()

    async def delete_artifact(
        self, artifact_id: UUID | str, force: bool = False
    ) -> bool:
        """
        Deletes artifact file and metadata according to lifecycle rules.
        """
        art_id = self._to_uuid(artifact_id)
        with self._lock:
            art = self._registry.get(art_id)
            if not art:
                logger.warning(f"Cannot delete: Artifact {art_id} not found")
                return False

            # Enforce lifecycle protection rules
            is_locked = art.metadata.get("is_locked", False) or art.metadata.get(
                "protected", False
            )
            if is_locked and not force:
                logger.warning(
                    f"Cannot delete protected artifact {art_id} without force=True"
                )
                raise ValueError(f"Artifact {art_id} is protected by lifecycle rules")

            fp = Path(art.filepath)
            if fp.exists():
                try:
                    fp.unlink()
                except Exception as e:
                    logger.error(f"Failed to delete artifact file {fp}: {e}")

            del self._registry[art_id]
            logger.info(f"Deleted artifact {art_id} ('{art.name}')")
            return True

    async def list_artifacts(
        self,
        workflow_id: UUID | str | None = None,
        task_id: UUID | str | None = None,
        artifact_type: ArtifactType | str | None = None,
    ) -> list[Artifact]:
        """Lists registered artifacts matching optional filters."""
        wf_id = self._to_uuid(workflow_id) if workflow_id else None
        t_id = self._to_uuid(task_id) if task_id else None
        target_type = (
            artifact_type.value
            if isinstance(artifact_type, ArtifactType)
            else artifact_type
        )

        with self._lock:
            results: list[Artifact] = []
            for art in self._registry.values():
                if wf_id and art.workflow_id != wf_id:
                    continue
                if t_id and art.task_id != t_id:
                    continue
                if target_type:
                    art_t = (
                        art.artifact_type.value
                        if isinstance(art.artifact_type, ArtifactType)
                        else str(art.artifact_type)
                    )
                    if art_t != str(target_type):
                        continue
                results.append(art.model_copy(deep=True))

            return results


class ArtifactStorageService:
    """
    Central service manager for registering, storing, retrieving, and managing
    workflow and task artifacts across replaceable storage providers.
    """

    def __init__(self, provider: BaseArtifactStorageProvider | None = None) -> None:
        self.provider = provider or LocalFileSystemArtifactStorageProvider()

    async def register_artifact(
        self,
        artifact: Artifact,
        content: bytes | str | None = None,
        source_path: str | Path | None = None,
    ) -> Artifact:
        """Registers a new artifact and persists its content."""
        saved = await self.provider.save_artifact(
            artifact=artifact, content=content, source_path=source_path
        )
        logger.info(
            f"ArtifactStorageService registered artifact {saved.artifact_id} "
            f"for workflow {saved.workflow_id} (Task: {saved.task_id})"
        )
        return saved

    async def get_artifact(self, artifact_id: UUID | str) -> Artifact | None:
        """Retrieves artifact metadata by artifact ID."""
        return await self.provider.get_artifact_metadata(artifact_id)

    async def get_artifact_content(self, artifact_id: UUID | str) -> bytes | None:
        """Retrieves binary content of an artifact by ID."""
        return await self.provider.read_artifact_content(artifact_id)

    async def delete_artifact(
        self, artifact_id: UUID | str, force: bool = False
    ) -> bool:
        """Deletes an artifact by ID enforcing lifecycle protection rules."""
        return await self.provider.delete_artifact(artifact_id, force=force)

    async def list_artifacts(
        self,
        workflow_id: UUID | str | None = None,
        task_id: UUID | str | None = None,
        artifact_type: ArtifactType | str | None = None,
    ) -> list[Artifact]:
        """Lists artifacts filtered by workflow, task, or type."""
        return await self.provider.list_artifacts(
            workflow_id=workflow_id,
            task_id=task_id,
            artifact_type=artifact_type,
        )


_artifact_storage_service_instance: ArtifactStorageService | None = None


def get_artifact_storage_service() -> ArtifactStorageService:
    """
    Returns global singleton ArtifactStorageService instance.
    """
    global _artifact_storage_service_instance
    if _artifact_storage_service_instance is None:
        _artifact_storage_service_instance = ArtifactStorageService()
    return _artifact_storage_service_instance


def reset_artifact_storage_service() -> ArtifactStorageService:
    """
    Resets and returns a fresh global ArtifactStorageService instance.
    """
    global _artifact_storage_service_instance
    _artifact_storage_service_instance = ArtifactStorageService()
    return _artifact_storage_service_instance
