import hashlib
import logging
import math
from abc import ABC, abstractmethod
from threading import Lock
from typing import Any
from uuid import UUID

from shared.contracts.vector import VectorRecord, VectorSearchResult

logger = logging.getLogger(__name__)


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Computes cosine similarity score between two dense vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    return max(-1.0, min(1.0, dot_product / (norm_a * norm_b)))


class BaseEmbeddingProvider(ABC):
    """
    Abstract interface for text embedding models/providers.
    """

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generates dense vector embedding for a single text string."""
        pass

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generates dense vector embeddings for a list of text strings."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Returns vector dimension produced by this provider."""
        pass


class DeterministicHashEmbeddingProvider(BaseEmbeddingProvider):
    """
    Default lightweight embedding provider using feature hashing and n-gram frequencies.
    Produces deterministic, normalized float vectors of fixed dimension (default 128)
    without external API keys or heavy binary dependencies.
    """

    def __init__(self, dimension: int = 128) -> None:
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    def _compute_vector(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        if not text or not text.strip():
            return vec

        words = text.lower().split()

        # Word n-grams (unigrams & bigrams)
        tokens = list(words)
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i + 1]}")

        for token in tokens:
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dim
            sign = 1.0 if (h >> 16) & 1 else -1.0
            vec[idx] += sign

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]

        return vec

    async def embed_text(self, text: str) -> list[float]:
        return self._compute_vector(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._compute_vector(t) for t in texts]


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Mock embedding provider for unit testing fixed vector dimensions.
    """

    def __init__(
        self, dimension: int = 4, fixed_vector: list[float] | None = None
    ) -> None:
        self._dim = dimension
        self.fixed_vector = fixed_vector

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_text(self, text: str) -> list[float]:
        if self.fixed_vector:
            return self.fixed_vector
        val = float(len(text) % 10) / 10.0
        return [val] * self._dim

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed_text(t) for t in texts]


class BaseVectorStoreProvider(ABC):
    """
    Abstract interface for vector database storage backends.
    """

    @abstractmethod
    async def insert(self, record: VectorRecord) -> VectorRecord:
        """Inserts or updates a VectorRecord."""
        pass

    @abstractmethod
    async def insert_batch(self, records: list[VectorRecord]) -> list[VectorRecord]:
        """Inserts or updates multiple VectorRecords."""
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[VectorSearchResult]:
        """Performs vector similarity search with optional metadata filtering."""
        pass

    @abstractmethod
    async def get(self, memory_id: UUID | str) -> VectorRecord | None:
        """Retrieves a VectorRecord by memory ID."""
        pass

    @abstractmethod
    async def delete(self, memory_id: UUID | str) -> bool:
        """Deletes a VectorRecord by memory ID."""
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clears all vector records from storage."""
        pass

    @abstractmethod
    async def count(self) -> int:
        """Returns total vector count."""
        pass


class InMemoryVectorStoreProvider(BaseVectorStoreProvider):
    """
    Default in-memory implementation of BaseVectorStoreProvider.
    Uses exact cosine similarity matching and dictionary metadata filtering.
    """

    def __init__(self) -> None:
        self._lock = Lock()
        self._records: dict[str, VectorRecord] = {}

    def _to_key(self, val: UUID | str) -> str:
        return str(val)

    async def insert(self, record: VectorRecord) -> VectorRecord:
        key = self._to_key(record.memory_id)
        with self._lock:
            self._records[key] = record.model_copy(deep=True)
            logger.info(
                f"InMemoryVectorStore inserted vector for memory_id={key} "
                f"(dim={len(record.vector)})"
            )
            return record

    async def insert_batch(self, records: list[VectorRecord]) -> list[VectorRecord]:
        with self._lock:
            for rec in records:
                key = self._to_key(rec.memory_id)
                self._records[key] = rec.model_copy(deep=True)
            logger.info(f"InMemoryVectorStore inserted batch of {len(records)} vectors")
            return records

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[VectorSearchResult]:
        if not query_vector:
            return []

        with self._lock:
            candidates = list(self._records.values())

        results: list[VectorSearchResult] = []
        for rec in candidates:
            # Metadata filtering check
            if filter_metadata:
                match = True
                for k, v in filter_metadata.items():
                    if rec.metadata.get(k) != v:
                        match = False
                        break
                if not match:
                    continue

            score = _cosine_similarity(query_vector, rec.vector)
            if score >= min_score:
                results.append(
                    VectorSearchResult(
                        memory_id=rec.memory_id,
                        score=score,
                        document=rec.document,
                        metadata=rec.metadata,
                    )
                )

        # Sort by highest score first
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    async def get(self, memory_id: UUID | str) -> VectorRecord | None:
        key = self._to_key(memory_id)
        with self._lock:
            rec = self._records.get(key)
            if rec:
                return rec.model_copy(deep=True)
            return None

    async def delete(self, memory_id: UUID | str) -> bool:
        key = self._to_key(memory_id)
        with self._lock:
            if key in self._records:
                del self._records[key]
                logger.info(f"InMemoryVectorStore deleted vector for memory_id={key}")
                return True
            return False

    async def clear(self) -> None:
        with self._lock:
            self._records.clear()
            logger.info("InMemoryVectorStore cleared all vectors")

    async def count(self) -> int:
        with self._lock:
            return len(self._records)


class VectorDatabaseService:
    """
    High-level Vector Database Service responsible for text embedding,
    storing memory vectors, semantic similarity searching, and metadata filtering.
    """

    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider | None = None,
        vector_store_provider: BaseVectorStoreProvider | None = None,
    ) -> None:
        self.embedding_provider = (
            embedding_provider or DeterministicHashEmbeddingProvider()
        )
        self.vector_store_provider = (
            vector_store_provider or InMemoryVectorStoreProvider()
        )

    async def store_memory(
        self,
        memory_id: UUID | str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> VectorRecord:
        """
        Embeds document text and stores vector record associated with memory ID.
        """
        if not text:
            raise ValueError("Cannot embed or store empty memory text")

        vector = await self.embedding_provider.embed_text(text)
        record = VectorRecord(
            memory_id=memory_id,
            vector=vector,
            document=text,
            metadata=metadata or {},
        )
        return await self.vector_store_provider.insert(record)

    async def search_similar(
        self,
        query_text: str,
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
        min_score: float = 0.0,
    ) -> list[VectorSearchResult]:
        """
        Generates embedding for query_text and performs similarity search.
        """
        if not query_text:
            return []

        query_vector = await self.embedding_provider.embed_text(query_text)
        return await self.vector_store_provider.search(
            query_vector=query_vector,
            top_k=top_k,
            filter_metadata=filter_metadata,
            min_score=min_score,
        )

    async def get_memory_vector(self, memory_id: UUID | str) -> VectorRecord | None:
        """Retrieves vector record by memory ID."""
        return await self.vector_store_provider.get(memory_id)

    async def delete_memory_vector(self, memory_id: UUID | str) -> bool:
        """Deletes vector record by memory ID."""
        return await self.vector_store_provider.delete(memory_id)

    async def clear(self) -> None:
        """Clears all vectors from storage."""
        await self.vector_store_provider.clear()


_vector_db_service_instance: VectorDatabaseService | None = None


def get_vector_db_service() -> VectorDatabaseService:
    """Returns global singleton VectorDatabaseService instance."""
    global _vector_db_service_instance
    if _vector_db_service_instance is None:
        _vector_db_service_instance = VectorDatabaseService()
    return _vector_db_service_instance


def reset_vector_db_service() -> VectorDatabaseService:
    """Resets and returns a fresh global VectorDatabaseService instance."""
    global _vector_db_service_instance
    _vector_db_service_instance = VectorDatabaseService()
    return _vector_db_service_instance
