from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import pymupdf

from ai.rag.vectorstore import ChromaVectorStore


@dataclass(frozen=True)
class RagChunk:
    chunk_id: str
    text: str
    metadata: dict[str, Any]
    image_path: Path | None = None


def ingest_pdfs(
    pdf_paths: list[Path],
    store: ChromaVectorStore,
    visual_assets_path: Path | None = None,
) -> dict[str, Any]:
    chunks: list[RagChunk] = []
    image_chunks: list[RagChunk] = []
    for pdf_path in pdf_paths:
        extracted_chunks, extracted_image_chunks = extract_pdf_chunks(pdf_path, visual_assets_path)
        chunks.extend(extracted_chunks)
        image_chunks.extend(extracted_image_chunks)

    store.reset()
    if chunks:
        store.add_chunks(chunks)
    if image_chunks:
        store.add_image_chunks(image_chunks)

    return {
        "indexed_chunks": len(chunks),
        "indexed_page_images": len(image_chunks),
        "sources": sorted({chunk.metadata["source"] for chunk in chunks}),
        "text_collection": store.text_collection_name,
        "image_collection": store.image_collection_name,
    }


def extract_pdf_chunks(pdf_path: Path, visual_assets_path: Path | None = None) -> tuple[list[RagChunk], list[RagChunk]]:
    source = pdf_path.name
    chunks: list[RagChunk] = []
    image_chunks: list[RagChunk] = []

    with pymupdf.open(pdf_path) as document:
        for page_index, page in enumerate(document):
            page_number = page_index + 1
            text = normalize_text(page.get_text("text"))
            for chunk_index, chunk_text in enumerate(split_text(text)):
                chunk_id = build_chunk_id(source, page_number, chunk_index, chunk_text)
                metadata = {
                    "chunk_id": chunk_id,
                    "source": source,
                    "source_type": "pdf",
                    "page": page_number,
                    "chunk_index": chunk_index,
                    "chunk_type": "text",
                    "language": "en",
                    "section_title": infer_section_title(chunk_text),
                    "token_count": len(chunk_text.split()),
                    "content_hash": sha256(chunk_text.encode("utf-8")).hexdigest(),
                    "ingested_at": datetime.now(UTC).isoformat(),
                }
                chunks.append(RagChunk(chunk_id=chunk_id, text=chunk_text, metadata=metadata))

            if visual_assets_path is not None:
                image_chunks.append(build_page_image_chunk(page, source, page_number, text, visual_assets_path))

    return chunks, image_chunks


def normalize_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def split_text(text: str, max_words: int = 220, overlap_words: int = 40) -> list[str]:
    words = text.split()
    if not words:
        return []
    if len(words) <= max_words:
        return [" ".join(words)]

    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_words, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = max(0, end - overlap_words)
    return chunks


def build_chunk_id(source: str, page_number: int, chunk_index: int, text: str) -> str:
    stem = Path(source).stem.lower().replace(" ", "-")
    digest = sha256(text.encode("utf-8")).hexdigest()[:10]
    return f"{stem}-p{page_number:03d}-c{chunk_index:03d}-{digest}"


def build_page_image_chunk(
    page: pymupdf.Page,
    source: str,
    page_number: int,
    page_text: str,
    visual_assets_path: Path,
) -> RagChunk:
    visual_assets_path.mkdir(parents=True, exist_ok=True)
    stem = Path(source).stem.lower().replace(" ", "-")
    image_path = visual_assets_path / f"{stem}-p{page_number:03d}.png"
    pixmap = page.get_pixmap(dpi=120, alpha=False)
    pixmap.save(image_path)

    caption = (
        f"Rendered page image from {source} page {page_number}. "
        f"Extracted page text for grounding: {page_text[:1500]}"
    )
    chunk_id = build_chunk_id(source, page_number, 0, f"page-image:{page_text}")
    metadata = {
        "chunk_id": chunk_id,
        "source": source,
        "source_type": "pdf",
        "page": page_number,
        "chunk_index": 0,
        "chunk_type": "page_image",
        "language": "en",
        "section_title": infer_section_title(page_text),
        "token_count": len(caption.split()),
        "content_hash": sha256((page_text + str(image_path)).encode("utf-8")).hexdigest(),
        "ingested_at": datetime.now(UTC).isoformat(),
        "visual_asset_path": str(image_path),
    }
    return RagChunk(chunk_id=chunk_id, text=caption, metadata=metadata, image_path=image_path)


def infer_section_title(text: str) -> str:
    first_sentence = text.split(".")[0].strip()
    if not first_sentence:
        return "unknown"
    return first_sentence[:120]
