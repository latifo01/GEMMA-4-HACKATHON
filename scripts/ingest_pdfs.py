import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ai.rag.ingest import ingest_pdfs
from ai.rag.vectorstore import build_vector_store
from apps.backend.config import get_settings


IMCI_PDFS = [
    "imci-chart-booklet.pdf",
    "whoyoungchildimci.pdf",
    "9789241506823_Intro_self-study_eng.pdf",
]


def main() -> None:
    settings = get_settings()
    dataset_dir = ROOT_DIR / "dataset"
    pdf_paths = [dataset_dir / filename for filename in IMCI_PDFS]
    missing = [path.name for path in pdf_paths if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required IMCI PDFs: {', '.join(missing)}")

    store = build_vector_store(settings)
    result = ingest_pdfs(pdf_paths, store, settings.rag_visual_assets_path)
    print(f"Indexed {result['indexed_chunks']} chunks into {settings.chroma_path}")
    print(f"Indexed {result['indexed_page_images']} rendered page images into {settings.rag_visual_assets_path}")
    print("Sources: " + ", ".join(result["sources"]))


if __name__ == "__main__":
    main()
