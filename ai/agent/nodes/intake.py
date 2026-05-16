from ai.agent.state import SUPPORTED_LANGUAGES, TriageInput, TriageState


LANGUAGE_ALIASES = {
    "english": "en",
    "anglais": "en",
    "french": "fr",
    "français": "fr",
    "francais": "fr",
    "arabic": "ar-SD",
    "sudanese arabic": "ar-SD",
    "arabe soudanais": "ar-SD",
}


def run_intake(request: TriageInput) -> TriageState:
    transcript = request.transcript.strip()
    if not transcript:
        raise ValueError("transcript is required.")

    source_language = normalize_language(request.source_language)
    target_language = normalize_language(request.target_language)
    if source_language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported source_language: {request.source_language}")
    if target_language not in SUPPORTED_LANGUAGES - {"auto"}:
        raise ValueError(f"Unsupported target_language: {request.target_language}")

    missing_information = []
    if request.patient.get("age_months") is None:
        missing_information.append("patient.age_months")

    return TriageState(
        transcript=transcript,
        source_language=source_language,
        target_language=target_language,
        patient=request.patient,
        measurements=request.measurements,
        context=request.context,
        missing_information=missing_information,
    )


def normalize_language(language: str) -> str:
    normalized = language.strip()
    return LANGUAGE_ALIASES.get(normalized.lower(), normalized)
