from pathlib import Path
from typing import Any

import chromadb

from ai.rag.embeddings import TOKEN_PATTERN, LexicalEmbeddingModel, build_image_embedding_model, build_text_embedding_model
from apps.backend.config import Settings


class ChromaVectorStore:
    text_collection_name = "imci_text_chunks"
    image_collection_name = "imci_page_images"

    def __init__(
        self,
        persist_path: Path,
        embedding_model: Any | None = None,
        image_embedding_model: Any | None = None,
    ) -> None:
        self.persist_path = Path(persist_path)
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self.embedding_model = embedding_model or LexicalEmbeddingModel()
        self.image_embedding_model = image_embedding_model or self.embedding_model
        self.client = chromadb.PersistentClient(path=str(self.persist_path))
        self.text_collection = self.client.get_or_create_collection(
            name=self.text_collection_name,
            metadata={"embedding_model": self.embedding_model.name},
        )
        self.image_collection = self.client.get_or_create_collection(
            name=self.image_collection_name,
            metadata={"embedding_model": self.image_embedding_model.name},
        )

    def reset(self) -> None:
        self._delete_collection(self.text_collection_name)
        self._delete_collection(self.image_collection_name)
        self.text_collection = self.client.get_or_create_collection(
            name=self.text_collection_name,
            metadata={"embedding_model": self.embedding_model.name},
        )
        self.image_collection = self.client.get_or_create_collection(
            name=self.image_collection_name,
            metadata={"embedding_model": self.image_embedding_model.name},
        )

    def add_chunks(self, chunks: list[Any]) -> None:
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                **chunk.metadata,
                "embedding_model": self.embedding_model.name,
            }
            for chunk in chunks
        ]
        ids = [chunk.chunk_id for chunk in chunks]
        embeddings = self.embedding_model.embed_documents(documents)

        self.text_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def add_image_chunks(self, chunks: list[Any]) -> None:
        documents = [chunk.text for chunk in chunks]
        metadatas = [
            {
                **chunk.metadata,
                "embedding_model": self.image_embedding_model.name,
            }
            for chunk in chunks
        ]
        ids = [chunk.chunk_id for chunk in chunks]
        if hasattr(self.image_embedding_model, "embed_image_paths") and all(chunk.image_path for chunk in chunks):
            embeddings = self.image_embedding_model.embed_image_paths([chunk.image_path for chunk in chunks])
        else:
            embeddings = self.image_embedding_model.embed_documents(documents)

        text_embeddings = self.embedding_model.embed_documents(documents)
        self.text_collection.add(
            ids=[f"{chunk_id}-caption" for chunk_id in ids],
            documents=documents,
            metadatas=metadatas,
            embeddings=text_embeddings,
        )
        self.image_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(
        self,
        query_text: str,
        top_k: int = 5,
        include_visual_embeddings: bool = False,
    ) -> list[dict[str, Any]]:
        matches = []
        if self.text_collection.count() > 0:
            matches.extend(
                self._query_collection(
                    self.text_collection,
                    self.embedding_model.embed_text(query_text),
                    max(top_k * 6, top_k),
                    query_text,
                )
            )
        if include_visual_embeddings and self.image_collection.count() > 0:
            matches.extend(
                self._query_collection(
                    self.image_collection,
                    self.image_embedding_model.embed_text(query_text),
                    max(top_k * 3, top_k),
                    query_text,
                )
            )

        matches.sort(key=lambda item: item["combined_score"], reverse=True)
        return matches[:top_k]

    def query_images(self, query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
        if self.image_collection.count() == 0:
            return []

        return self._query_collection(
            self.image_collection,
            self.image_embedding_model.embed_text(query_text),
            top_k,
            query_text,
        )

    def get_all(self) -> dict[str, Any]:
        return self.text_collection.get(include=["documents", "metadatas"])

    def get_all_images(self) -> dict[str, Any]:
        return self.image_collection.get(include=["documents", "metadatas"])

    def _query_collection(
        self,
        collection: Any,
        query_embedding: list[float],
        top_k: int,
        query_text: str,
    ) -> list[dict[str, Any]]:
        if collection.count() == 0:
            return []

        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]

        matches = []
        for document, metadata, distance in zip(documents, metadatas, distances, strict=True):
            semantic_score = distance_to_relevance(distance)
            lexical_score = lexical_relevance(query_text, document)
            combined_score = (semantic_score * 0.55) + (lexical_score * 0.45)
            matches.append(
                {
                    "chunk_id": metadata["chunk_id"],
                    "source": metadata["source"],
                    "page": metadata["page"],
                    "chunk_type": metadata["chunk_type"],
                    "section_title": metadata["section_title"],
                    "visual_asset_path": metadata.get("visual_asset_path"),
                    "text": document,
                    "relevance_score": combined_score,
                    "semantic_score": semantic_score,
                    "lexical_score": lexical_score,
                    "combined_score": combined_score,
                    "distance": distance,
                }
            )
        return matches

    def _delete_collection(self, collection_name: str) -> None:
        try:
            self.client.delete_collection(collection_name)
        except Exception:
            pass


def distance_to_relevance(distance: float) -> float:
    return max(0.0, min(1.0, 1.0 / (1.0 + distance)))


def lexical_relevance(query_text: str, document: str) -> float:
    query_tokens = set(TOKEN_PATTERN.findall(query_text.lower()))
    document_tokens = set(TOKEN_PATTERN.findall(document.lower()))
    if not query_tokens:
        return 0.0

    return len(query_tokens & document_tokens) / len(query_tokens)


def build_vector_store(settings: Settings) -> ChromaVectorStore:
    return ChromaVectorStore(
        settings.chroma_path,
        embedding_model=build_text_embedding_model(settings),
        image_embedding_model=build_image_embedding_model(settings),
    )
