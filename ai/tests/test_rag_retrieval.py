from pathlib import Path

import pymupdf

from ai.rag.ingest import ingest_pdfs
from ai.rag.vectorstore import ChromaVectorStore


def create_fixture_pdf(path: Path) -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_textbox(
        pymupdf.Rect(72, 72, 520, 220),
        "Respiratory IMCI guidance. A child aged 12 months up to 5 years "
        "has fast breathing at 40 breaths per minute or more.",
    )
    page = doc.new_page()
    page.insert_textbox(
        pymupdf.Rect(72, 72, 520, 220),
        "Diarrhoea IMCI guidance. Severe dehydration includes lethargic or "
        "unconscious, sunken eyes, and skin pinch goes back very slowly.",
    )
    doc.save(path)
    doc.close()


def test_retrieval_returns_expected_source_page_and_chunk(tmp_path):
    pdf_path = tmp_path / "fixture-imci.pdf"
    create_fixture_pdf(pdf_path)
    store = ChromaVectorStore(tmp_path / "chroma")
    ingest_pdfs([pdf_path], store)

    results = store.query("fast breathing 40 breaths per minute", top_k=2)

    assert results
    top = results[0]
    assert top["source"] == "fixture-imci.pdf"
    assert top["page"] == 1
    assert top["chunk_id"]
    assert "40 breaths per minute" in top["text"]
    assert 0 <= top["relevance_score"] <= 1


def test_retrieval_can_find_dehydration_context(tmp_path):
    pdf_path = tmp_path / "fixture-imci.pdf"
    create_fixture_pdf(pdf_path)
    store = ChromaVectorStore(tmp_path / "chroma")
    ingest_pdfs([pdf_path], store)

    results = store.query("severe dehydration sunken eyes skin pinch", top_k=2)

    assert results[0]["page"] == 2
    assert "Severe dehydration" in results[0]["text"]
