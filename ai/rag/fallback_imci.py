from dataclasses import dataclass
import re
import unicodedata
from typing import Any


TOKEN_PATTERN = re.compile(r"[a-z0-9_]+")


@dataclass(frozen=True)
class EvidenceCard:
    chunk_id: str
    source: str
    page: int
    section_title: str
    text: str
    keywords: tuple[str, ...]


FALLBACK_EVIDENCE: tuple[EvidenceCard, ...] = (
    EvidenceCard(
        chunk_id="fallback-imci-general-danger-signs",
        source="imci-chart-booklet.pdf",
        page=5,
        section_title="General danger signs",
        text=(
            "General danger signs include poor drinking or breastfeeding, repeated vomiting, "
            "convulsions, lethargy, unconsciousness, or current convulsions."
        ),
        keywords=(
            "general_danger_sign",
            "unable_to_drink_or_breastfeed",
            "refuse",
            "drink",
            "boire",
            "breastfeed",
            "vomits_everything",
            "convulsions",
            "lethargic_or_unconscious",
        ),
    ),
    EvidenceCard(
        chunk_id="fallback-imci-cough-difficult-breathing",
        source="imci-chart-booklet.pdf",
        page=6,
        section_title="Cough or difficult breathing",
        text=(
            "For cough or difficult breathing, IMCI checks duration, respiratory rate, chest "
            "indrawing, stridor, wheeze, and whether the child is calm."
        ),
        keywords=(
            "cough_or_difficult_breathing",
            "cough",
            "difficult_breathing",
            "respiratory_rate_bpm",
            "chest_indrawing",
            "stridor_in_calm_child",
            "fast_breathing",
        ),
    ),
    EvidenceCard(
        chunk_id="fallback-imci-diarrhea-dehydration",
        source="imci-chart-booklet.pdf",
        page=7,
        section_title="Diarrhoea and dehydration",
        text=(
            "For diarrhoea, IMCI checks duration, blood in stool, general condition, sunken "
            "eyes, ability to drink, thirst, and skin pinch."
        ),
        keywords=(
            "diarrhea_dehydration",
            "diarrhea",
            "diarrhoea",
            "sunken_eyes",
            "restless_or_irritable",
            "drinks_eagerly_or_thirsty",
            "skin_pinch_slow",
            "skin_pinch_very_slow",
            "vomit",
        ),
    ),
    EvidenceCard(
        chunk_id="fallback-imci-fever",
        source="imci-chart-booklet.pdf",
        page=8,
        section_title="Fever",
        text=(
            "For fever, IMCI asks about duration, daily fever beyond seven days, recent "
            "measles, stiff neck, malaria risk, and visible measles signs."
        ),
        keywords=(
            "fever",
            "fievre",
            "temperature_celsius",
            "high_fever",
            "prolonged_fever",
            "malaria",
            "measles",
            "stiff_neck",
        ),
    ),
)


def fallback_evidence_available() -> bool:
    return bool(FALLBACK_EVIDENCE)


def query_fallback_evidence(query_text: str, top_k: int = 5) -> list[dict[str, Any]]:
    query_tokens = set(TOKEN_PATTERN.findall(normalize(query_text)))
    if not query_tokens:
        return []

    matches = []
    for card in FALLBACK_EVIDENCE:
        keyword_tokens = {normalize(keyword) for keyword in card.keywords}
        text_tokens = set(TOKEN_PATTERN.findall(normalize(card.text)))
        overlap = query_tokens & (keyword_tokens | text_tokens)
        if not overlap:
            continue

        score = min(1.0, len(overlap) / max(3, len(query_tokens & keyword_tokens) + 3))
        matches.append(
            {
                "chunk_id": card.chunk_id,
                "source": card.source,
                "page": card.page,
                "chunk_type": "fallback_evidence",
                "section_title": card.section_title,
                "visual_asset_path": None,
                "text": card.text,
                "relevance_score": score,
                "semantic_score": 0.0,
                "lexical_score": score,
                "combined_score": score,
                "distance": 1.0 - score,
            }
        )

    matches.sort(key=lambda item: item["combined_score"], reverse=True)
    return matches[:top_k]


def normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))
