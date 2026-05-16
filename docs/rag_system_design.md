# RAG System Design

## Objective

Design a production-ready RAG system for IMCI clinical decision support that supports text,
tables, charts, diagrams, and mixed text-image documents.

## Explicit Assumptions

- The source documents are local PDFs stored in `dataset/`.
- The first validated corpus is the IMCI document set already present in the workspace.
- The demo must run locally without requiring a managed vector database.
- The architecture must allow migration to Qdrant, Weaviate, or Vertex AI Vector Search later.

## Source Types

| Source Type | Examples | Processing Strategy |
|---|---|---|
| Plain text | Paragraphs, instructions | Extract with PyMuPDF, normalize, chunk semantically |
| Tables | IMCI thresholds, age bands | Extract as structured markdown plus page coordinates |
| Charts | Decision flowcharts | Render page image, create image embedding, attach OCR text |
| Diagrams | Clinical flow diagrams | Render page image, embed visually, preserve page metadata |
| Mixed pages | Text plus table or chart | Store both text chunks and page-image chunks linked by page ID |

## Models

Initial local demo models:

| Purpose | Model | Reason |
|---|---|---|
| Text embeddings | `fastembed` with `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` ONNX | Local CPU inference without PyTorch, supports English, French, and Arabic retrieval queries |
| Image embeddings | `fastembed` with `Qdrant/clip-ViT-B-32-vision` and `Qdrant/clip-ViT-B-32-text` | Local CLIP-style visual embeddings for rendered PDF pages |
| Fallback embeddings | `lexical-hashing-v1` | Deterministic fallback for fast tests and offline reproducibility |
| Reranking | `BAAI/bge-reranker-base` | Improves retrieval precision after vector search |

Production preferred models:

| Purpose | Model Option | Reason |
|---|---|---|
| Text embeddings | Google text embedding model or multilingual E5 | Better multilingual semantic quality |
| Multimodal embeddings | SigLIP or Gemini embedding if available through approved API | Strong mixed visual-text alignment |
| Reranking | Cross-encoder reranker | Reduces hallucination by improving context relevance |

The implementation must isolate model choices behind `ai/rag/embeddings.py` so models can be
changed without modifying ingestion or retrieval logic.

## Chunking Strategy

Text chunks:

- Target size: 400 to 700 tokens.
- Overlap: 80 to 120 tokens.
- Split priority:
  1. heading boundaries;
  2. table boundaries;
  3. bullet lists;
  4. paragraph boundaries;
  5. token fallback.

Table chunks:

- Store one table as one chunk when possible.
- Preserve row and column headers.
- Convert to markdown and structured JSON.
- Add metadata `chunk_type: table`.

Visual chunks:

- Render each PDF page to an image at 150 to 200 DPI.
- Store page-level image embeddings.
- Link visual page chunks to text chunks from the same page.
- Add metadata `chunk_type: page_image`.

## Metadata Schema

Each indexed item must include:

```json
{
  "chunk_id": "imci-chart-booklet-p012-c003",
  "source": "imci-chart-booklet.pdf",
  "source_type": "pdf",
  "page": 12,
  "chunk_index": 3,
  "chunk_type": "text|table|page_image",
  "language": "en",
  "section_title": "Cough or difficult breathing",
  "token_count": 520,
  "content_hash": "sha256",
  "ingested_at": "iso-datetime",
  "embedding_model": "model-name",
  "visual_asset_path": "optional-local-path"
}
```

## Indexing Strategy

Use separate collections for clear retrieval control:

- `imci_text_chunks`
- `imci_table_chunks`
- `imci_page_images`

Query-time retrieval:

1. Build a structured query from symptoms, age, and suspected module.
2. Search text chunks with multilingual text embedding.
3. Search table chunks with text embedding.
4. Search page images with image-aware or text-image embedding.
5. Merge candidates by normalized score.
6. Deduplicate by `source`, `page`, and `section_title`.
7. Rerank top 30 candidates.
8. Return top 5 to 8 context items.

## Reranking Strategy

Reranking input:

- user transcript summary;
- extracted symptoms;
- clinical module hint;
- candidate chunk text or OCR caption.

Reranking output:

- relevance score;
- reason for relevance;
- grounding risk flag.

The agent must not receive low-confidence context unless no better context exists. In that case,
the response must include a retrieval warning.

## Context Injection

The final reasoning prompt receives:

- patient age;
- extracted symptoms JSON;
- deterministic tool outputs;
- top retrieved context items;
- compact citations;
- missing information;
- explicit instruction to answer only from context and tools.

Context budget:

- Maximum 8 chunks.
- Maximum 4,000 tokens of retrieved context for the first demo.
- Prefer high-confidence table or chart chunks when thresholds are needed.

## Hallucination Reduction

Required mechanisms:

- Strict JSON schemas for symptom extraction and final output.
- Citations required for recommendations.
- Deterministic tools override LLM claims.
- Verification node checks contradictions.
- Empty or weak retrieval produces `insufficient_evidence` instead of fabricated guidance.
- Prompt requires explicit `missing_information`.
- Session record stores retrieved chunks for audit.

## Latency Strategy

Ingestion:

- Precompute all embeddings before demo.
- Store content hashes to skip unchanged files.

Retrieval:

- Cache query embeddings by normalized query hash.
- Cache top-k retrieval results for repeated demo cases.
- Keep local ChromaDB persistent collection warm.
- Rerank only top 30 candidates.

Target latency:

| Step | Target |
|---|---:|
| Query embedding | < 300 ms CPU |
| Vector search | < 200 ms local |
| Reranking | < 1,500 ms CPU |
| Context assembly | < 100 ms |

## Evaluation

Create a small retrieval evaluation set in `tests/fixtures/rag_eval_cases.json`.

Each case contains:

- clinical question;
- expected source document;
- expected page or section;
- expected key phrase;
- allowed alternative pages.

Metrics:

- Recall@5.
- MRR@10.
- citation accuracy.
- table retrieval hit rate.
- no-answer behavior for unsupported queries.

Minimum acceptance for demo:

- Recall@5 >= 0.80 on curated IMCI cases.
- No unsupported query returns fabricated clinical guidance.
- Pneumonia threshold queries retrieve the correct IMCI respiratory guidance.

## Vector Store Decision

Selected for MVP:

- ChromaDB persistent local storage.

Alternatives:

- FAISS: very fast, but metadata handling and persistence are less convenient.
- Qdrant: stronger production service, but adds deployment complexity.
- Weaviate: feature-rich, but heavier for a hackathon local demo.

Migration path:

- Keep vector operations behind `ai/rag/vectorstore.py`.
- Keep metadata schema stable.
- Add Qdrant adapter later without changing agent nodes.
