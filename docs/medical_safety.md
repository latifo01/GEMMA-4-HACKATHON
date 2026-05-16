# Medical Safety

## Safety Position

ImciFlow is a clinical decision-support system. It does not replace clinical judgment, does not
produce autonomous diagnoses, and must always require human review.

## Required Output Safety Fields

Every triage result must include:

- `human_review_required`
- `missing_information`
- `safety_flags`
- `citations`
- `tool_results`
- `model.mode`
- `model.name`

## Deterministic Rule Priority

Safety-critical classifications must prioritize deterministic tools over generated text.

Examples:

- A general danger sign must trigger a high-risk safety flag.
- Chest indrawing must not be downgraded by LLM-generated reasoning.
- Missing age must prevent definitive age-based respiratory interpretation.
- Missing or weak retrieval must produce an evidence warning.

## Clinical Grounding Requirements

The backend must:

- retrieve relevant IMCI context before clinical reasoning;
- include source, page, and chunk ID for citations;
- refuse unsupported clinical claims;
- separate extracted symptoms from recommendations;
- store retrieval context in the session audit record.

## Verification Node Responsibilities

The verification node checks:

- final color is consistent with deterministic tool outputs;
- high-risk signs are reflected in recommendations;
- citations exist for clinical guidance;
- missing information is not hidden;
- generated translation does not remove safety-critical instructions.

## Logging Restrictions

Production logs must not contain:

- API keys;
- raw audio files;
- full caregiver transcripts;
- personally identifying information.

Debug mode may store expanded traces only when explicitly enabled by settings.

## Acceptance Criteria

- Unit tests cover danger sign handling.
- Unit tests cover respiratory thresholds.
- Triage API returns `human_review_required: true`.
- Triage API returns citations for recommendations.
- Contradictory LLM output is rejected or corrected by verification.

