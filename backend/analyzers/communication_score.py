def analyze(
    speaking_rate_wpm: float,
    vocabulary_diversity: float,
    filler_rate: float,
    confidence_language_score: float,
) -> dict:

    # ── Speaking rate score ───────────────────────────────────────────────────
    # Ideal: 120–170 WPM | Tiered penalties outside that range
    if 120 <= speaking_rate_wpm <= 170:
        speaking_rate_score = 100
    elif 90 <= speaking_rate_wpm < 120:
        speaking_rate_score = max(0, 100 - (120 - speaking_rate_wpm) * 1.0)
    elif speaking_rate_wpm < 90:
        speaking_rate_score = max(0, 70 - (90 - speaking_rate_wpm) * 2.0)
    elif 170 < speaking_rate_wpm <= 200:
        speaking_rate_score = max(0, 100 - (speaking_rate_wpm - 170) * 1.0)
    else:  # > 200 WPM
        speaking_rate_score = max(0, 70 - (speaking_rate_wpm - 200) * 2.0)

    # ── Vocabulary diversity score ────────────────────────────────────────────
    # diversity is 0.0–1.0; ideal >= 0.6
    if vocabulary_diversity >= 0.7:
        vocabulary_score = 100
    elif vocabulary_diversity >= 0.6:
        vocabulary_score = 85
    elif vocabulary_diversity >= 0.5:
        vocabulary_score = 70
    elif vocabulary_diversity >= 0.4:
        vocabulary_score = 50
    else:
        vocabulary_score = max(0, int(vocabulary_diversity * 100))

    # ── Filler rate score ─────────────────────────────────────────────────────
    # filler_rate is % of words that are fillers; ideal < 2%
    if filler_rate <= 2:
        filler_score = 100
    elif filler_rate <= 5:
        filler_score = int(100 - (filler_rate - 2) * 10)
    elif filler_rate <= 10:
        filler_score = int(70 - (filler_rate - 5) * 8)
    else:
        filler_score = max(0, int(30 - (filler_rate - 10) * 3))

    # ── Weighted composite ────────────────────────────────────────────────────
    # rate 30% | vocab 20% | filler 25% | confidence 25%
    raw = (
        speaking_rate_score        * 0.30 +
        vocabulary_score           * 0.20 +
        filler_score               * 0.25 +
        confidence_language_score  * 0.25
    )
    communication_score = min(100, max(0, round(raw)))

    # ── Communication level ───────────────────────────────────────────────────
    if communication_score >= 85:
        communication_level = "Excellent"
    elif communication_score >= 70:
        communication_level = "Good"
    elif communication_score >= 50:
        communication_level = "Average"
    else:
        communication_level = "Needs Improvement"

    # ── Explanation engine ────────────────────────────────────────────────────
    strengths:  list[str] = []
    weaknesses: list[str] = []

    if 120 <= speaking_rate_wpm <= 170:
        strengths.append("Maintained an ideal speaking pace (120–170 WPM)")
    elif speaking_rate_wpm > 200:
        weaknesses.append(f"Speaking pace too fast ({speaking_rate_wpm} WPM) — slow down for clarity")
    elif speaking_rate_wpm > 170:
        weaknesses.append(f"Speaking pace slightly fast ({speaking_rate_wpm} WPM)")
    elif speaking_rate_wpm < 90:
        weaknesses.append(f"Speaking pace too slow ({speaking_rate_wpm} WPM) — aim for more energy")
    else:
        weaknesses.append(f"Speaking pace slightly slow ({speaking_rate_wpm} WPM)")

    if vocabulary_diversity >= 0.65:
        strengths.append("Demonstrated rich and varied vocabulary")
    elif vocabulary_diversity < 0.5:
        weaknesses.append("Vocabulary was repetitive — expand word choice")

    if filler_rate <= 2:
        strengths.append("Minimal filler words — speech was clear and direct")
    elif filler_rate <= 5:
        weaknesses.append(f"Moderate filler word usage ({filler_rate}%) — practice pausing instead")
    else:
        weaknesses.append(f"High filler word usage ({filler_rate}%) — significantly impacts clarity")

    if confidence_language_score >= 70:
        strengths.append("Used confident, action-oriented language effectively")
    elif confidence_language_score < 50:
        weaknesses.append("Language lacked confidence — replace hedging with assertive statements")

    return {
        "communication_score": communication_score,
        "communication_level": communication_level,
        "score_breakdown": {
            "speaking_rate_score": round(speaking_rate_score),
            "vocabulary_score":    vocabulary_score,
            "filler_score":        filler_score,
            "confidence_score":    round(confidence_language_score),
        },
        "strengths":  strengths,
        "weaknesses": weaknesses,
    }
