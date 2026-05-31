import re

# ── Phrase lists ──────────────────────────────────────────────────────────────
CONFIDENT_PHRASES: list[str] = [
    "i built", "i developed", "i implemented", "i designed",
    "i created", "i led", "i managed", "i architected",
    "i delivered", "i launched", "i established", "i drove",
    "i owned", "i spearheaded", "i achieved", "i solved",
    "i improved", "i optimized", "i deployed", "i trained",
]

UNCERTAIN_PHRASES: list[str] = [
    "i think", "i guess", "i feel like", "i believe maybe",
    "maybe", "probably", "perhaps", "not sure",
    "kind of", "sort of", "i'm not certain", "i don't know",
    "might be", "could be", "i suppose",
]


def _find_phrases(text_lower: str, phrases: list[str]) -> list[str]:
    found = []
    for phrase in phrases:
        pattern = r"\b" + re.escape(phrase) + r"\b"
        matches = re.findall(pattern, text_lower)
        found.extend(matches)
    return found


def analyze(transcript: str) -> dict:
    if not transcript.strip():
        return {
            "confidence_language_score": 0.0,
            "confident_phrase_count": 0,
            "uncertain_phrase_count": 0,
            "confident_phrases_found": [],
            "uncertain_phrases_found": [],
        }

    text_lower = transcript.lower()

    confident_found  = _find_phrases(text_lower, CONFIDENT_PHRASES)
    uncertain_found  = _find_phrases(text_lower, UNCERTAIN_PHRASES)

    confident_count  = len(confident_found)
    uncertain_count  = len(uncertain_found)
    total            = confident_count + uncertain_count

    # Score: 100 if all phrases are confident, 0 if all uncertain
    # Baseline 50 when no phrases detected (neutral)
    if total == 0:
        score = 50.0
    else:
        score = round((confident_count / total) * 100, 1)

    # Bonus for high absolute confident phrase count (shows active language use)
    if confident_count >= 5:
        score = min(100.0, score + 10)

    return {
        "confidence_language_score": score,
        "confident_phrase_count": confident_count,
        "uncertain_phrase_count": uncertain_count,
        "confident_phrases_found": list(set(confident_found)),
        "uncertain_phrases_found": list(set(uncertain_found)),
    }
