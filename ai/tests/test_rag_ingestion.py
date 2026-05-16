from pathlib import Path

import pymupdf

from ai.rag.ingest import ingest_pdfs
from ai.rag.vectorstore import ChromaVectorStore


def create_fixture_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(
        pymupdf.Rect(72, 72, 520, 220),
        "IMCI cough or difficult breathing. Fast breathing means pneumonia. "
        "Chest indrawing is a serious respiratory sign.",
    )
    doc.save(path)
    doc.close()


def test_ingest_pdf_creates_citation_ready_chunks(tmp_path):
    pdf_path = tmp_path / "fixture-imci.pdf"
    create_fixture_pdf(pdf_path)
    store = ChromaVectorStore(tmp_path / "chroma")

    result = ingest_pdfs([pdf_path], store, tmp_path / "page_images")

    assert result["indexed_chunks"] >= 1
    assert result["indexed_page_images"] == 1
    assert result["sources"] == ["fixture-imci.pdf"]

    records = store.get_all()
    assert records["ids"]
    text_index = next(
        index for index, metadata in enumerate(records["metadatas"]) if metadata["chunk_type"] == "text"
    )
    assert records["metadatas"][text_index]["source"] == "fixture-imci.pdf"
    assert records["metadatas"][text_index]["page"] == 1
    assert records["metadatas"][text_index]["chunk_id"] == records["ids"][text_index]
    assert "Fast breathing" in records["documents"][text_index]

    image_records = store.get_all_images()
    assert image_records["ids"]
    assert image_records["metadatas"][0]["chunk_type"] == "page_image"
    assert Path(image_records["metadatas"][0]["visual_asset_path"]).exists()
