import hashlib
import math
import re
from pathlib import Path
from typing import Any

from apps.backend.config import Settings


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")


class LexicalEmbeddingModel:
    name = "lexical-hashing-v1"

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]

    def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions

        for token in self._tokens(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            return vector

        return [value / magnitude for value in vector]

    def _tokens(self, text: str) -> list[str]:
        return TOKEN_PATTERN.findall(text.lower())


class SentenceTransformerTextEmbeddingModel:
    def __init__(self, model_name: str) -> None:
        self.name = model_name
        self._model: Any | None = None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._to_list(vector) for vector in self._load_model().encode(texts, normalize_embeddings=True)]

    def embed_text(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is required for RAG_TEXT_EMBEDDING_PROVIDER=sentence-transformers."
                ) from exc

            self._model = SentenceTransformer(self.name)
        return self._model

    def _to_list(self, vector: Any) -> list[float]:
        return [float(value) for value in vector]


class SentenceTransformerImageEmbeddingModel(SentenceTransformerTextEmbeddingModel):
    def embed_image_paths(self, image_paths: list[Path]) -> list[list[float]]:
        try:
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError(
                "Pillow is required for RAG_IMAGE_EMBEDDING_PROVIDER=sentence-transformers-clip."
            ) from exc

        images = [Image.open(path) for path in image_paths]
        try:
            return [self._to_list(vector) for vector in self._load_model().encode(images, normalize_embeddings=True)]
        finally:
            for image in images:
                image.close()


class FastEmbedTextEmbeddingModel:
    def __init__(self, model_name: str) -> None:
        self.name = model_name
        self._model: Any | None = None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._load_model().embed(texts)
        return [self._to_list(vector) for vector in vectors]

    def embed_text(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def _load_model(self) -> Any:
        if self._model is None:
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:
                raise RuntimeError("fastembed is required for RAG_TEXT_EMBEDDING_PROVIDER=fastembed.") from exc

            self._model = TextEmbedding(model_name=self.name)
        return self._model

    def _to_list(self, vector: Any) -> list[float]:
        return [float(value) for value in vector]


class FastEmbedImageTextEmbeddingModel:
    def __init__(self, image_model_name: str, text_model_name: str) -> None:
        self.name = image_model_name
        self.text_model_name = text_model_name
        self._image_model: Any | None = None
        self._text_model: Any | None = None

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = self._load_text_model().embed(texts)
        return [self._to_list(vector) for vector in vectors]

    def embed_text(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_image_paths(self, image_paths: list[Path]) -> list[list[float]]:
        vectors = self._load_image_model().embed([str(path) for path in image_paths])
        return [self._to_list(vector) for vector in vectors]

    def _load_image_model(self) -> Any:
        if self._image_model is None:
            try:
                from fastembed import ImageEmbedding
            except ImportError as exc:
                raise RuntimeError("fastembed is required for RAG_IMAGE_EMBEDDING_PROVIDER=fastembed-clip.") from exc

            self._image_model = ImageEmbedding(model_name=self.name)
        return self._image_model

    def _load_text_model(self) -> Any:
        if self._text_model is None:
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:
                raise RuntimeError("fastembed is required for RAG_IMAGE_EMBEDDING_PROVIDER=fastembed-clip.") from exc

            self._text_model = TextEmbedding(model_name=self.text_model_name)
        return self._text_model

    def _to_list(self, vector: Any) -> list[float]:
        return [float(value) for value in vector]


def build_text_embedding_model(settings: Settings) -> LexicalEmbeddingModel | SentenceTransformerTextEmbeddingModel:
    if settings.rag_text_embedding_provider == "lexical":
        return LexicalEmbeddingModel()
    if settings.rag_text_embedding_provider == "fastembed":
        return FastEmbedTextEmbeddingModel(settings.rag_text_embedding_model)
    if settings.rag_text_embedding_provider == "sentence-transformers":
        return SentenceTransformerTextEmbeddingModel(settings.rag_text_embedding_model)

    raise ValueError(f"Unsupported text embedding provider: {settings.rag_text_embedding_provider}")


def build_image_embedding_model(
    settings: Settings,
) -> LexicalEmbeddingModel | SentenceTransformerImageEmbeddingModel:
    if settings.rag_image_embedding_provider == "lexical":
        return LexicalEmbeddingModel()
    if settings.rag_image_embedding_provider == "fastembed-clip":
        return FastEmbedImageTextEmbeddingModel(
            image_model_name=settings.rag_image_embedding_model,
            text_model_name=settings.rag_image_text_embedding_model,
        )
    if settings.rag_image_embedding_provider == "sentence-transformers-clip":
        return SentenceTransformerImageEmbeddingModel(settings.rag_image_embedding_model)

    raise ValueError(f"Unsupported image embedding provider: {settings.rag_image_embedding_provider}")
