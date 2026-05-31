import re

UNCERTAIN_PHRASES = [
    "i think", "maybe", "probably", "perhaps",
    "kind of", "sort of", "not sure", "i guess",
    "might", "possibly", "hopefully",
]

CONFIDENT_PHRASES = [
    "i built", "i developed", "i implemented", "i designed",
    "i created", "i led", "i managed", "i optimized",
    "i delivered", "i achieved", "i launched", "i established",
    "i solved", "i improved", "i engineered",
]


def _find_phrases(lower: str, phrases: list[str]) -> dict[str, int]:
    found: dict[str, int] = {}
    for phrase in phrases:
        count = len(re.findall(r"\b" + re.escape(phrase) + r"\b", lower))
        if count:
            found[phrase] = count
    return found


def analyze(transcript: str) -> dict:
    lower = transcript.lower()

    confident_matches = _find_phrases(lower, CONFIDENT_PHRASES)
    uncertain_matches = _find_phrases(lower, UNCERTAIN_PHRASES)

    confident_count = sum(confident_matches.values())
    uncertain_count = sum(uncertain_matches.values())

    # ── Score: start at 50, +5 per confident phrase, -7 per uncertain phrase ──
    score = 50
    score += confident_count * 5
    score -= uncertain_count * 7
    score = max(0, min(100, score))

    # ── Confidence ratio ──────────────────────────────────────────────────────
    if uncertain_count == 0:
        confidence_ratio = float(confident_count) if confident_count > 0 else 1.0
    else:
        confidence_ratio = round(confident_count / uncertain_count, 2)

    # ── Confidence level ──────────────────────────────────────────────────────
    if score >= 80:
        confidence_level = "Very High"
    elif score >= 65:
        confidence_level = "High"
    elif score >= 45:
        confidence_level = "Moderate"
    else:
        confidence_level = "Low"

    # ── Score explanation ─────────────────────────────────────────────────────
    explanation: list[str] = []
    if confident_count:
        phrases_str = ", ".join(f'"{p}"' for p in confident_matches)
        explanation.append(f"Detected {confident_count} confident phrase(s): {phrases_str}")
    else:
        explanation.append("No confident action phrases detected — score starts at 50")
    if uncertain_count:
        phrases_str = ", ".join(f'"{p}"' for p in uncertain_matches)
        explanation.append(f"Detected {uncertain_count} uncertainty phrase(s): {phrases_str}")
    else:
        explanation.append("No uncertain phrases detected")

    return {
        "confidence_language_score": score,
        "confident_phrases":         confident_count,
        "uncertain_phrases":         uncertain_count,
        "confidence_ratio":          confidence_ratio,
        "confidence_level":          confidence_level,
        "score_explanation":         explanation,
    }
