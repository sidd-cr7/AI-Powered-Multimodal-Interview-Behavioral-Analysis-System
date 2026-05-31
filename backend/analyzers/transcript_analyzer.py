import re

# ── Filler word definitions ───────────────────────────────────────────────────
# Multi-word fillers must come before single-word ones so they match first
FILLER_PATTERNS: list[tuple[str, str]] = [
    ("you know",   r"\byou\s+know\b"),
    ("sort of",    r"\bsort\s+of\b"),
    ("kind of",    r"\bkind\s+of\b"),
    ("um",         r"\bum+\b"),
    ("uh",         r"\buh+\b"),
    ("like",       r"\blike\b"),
    ("actually",   r"\bactually\b"),
    ("basically",  r"\bbasically\b"),
    ("literally",  r"\bliterally\b"),
]


def analyze(transcript: str, duration_seconds: float) -> dict:
    if not transcript.strip():
        return {
            "word_count": 0,
            "sentence_count": 0,
            "speaking_rate_wpm": 0.0,
            "filler_word_count": 0,
            "filler_rate": 0.0,
            "filler_breakdown": {k: 0 for k, _ in FILLER_PATTERNS},
        }

    text_lower = transcript.lower()

    # Word and sentence counts
    words = transcript.split()
    word_count = len(words)
    sentence_count = len(re.findall(r"[.!?]+", transcript)) or 1

    # Speaking rate
    speaking_rate_wpm = round((word_count / duration_seconds) * 60, 1) if duration_seconds > 0 else 0.0

    # Filler detection — count each pattern independently
    filler_breakdown: dict[str, int] = {}
    total_fillers = 0
    for label, pattern in FILLER_PATTERNS:
        count = len(re.findall(pattern, text_lower))
        filler_breakdown[label] = count
        total_fillers += count

    # Filler rate = fillers per 100 words
    filler_rate = round((total_fillers / word_count) * 100, 1) if word_count > 0 else 0.0

    # Strip zero-count fillers from breakdown for cleaner output
    filler_breakdown = {k: v for k, v in filler_breakdown.items() if v > 0}

    return {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "speaking_rate_wpm": speaking_rate_wpm,
        "filler_word_count": total_fillers,
        "filler_rate": filler_rate,
        "filler_breakdown": filler_breakdown,
    }
