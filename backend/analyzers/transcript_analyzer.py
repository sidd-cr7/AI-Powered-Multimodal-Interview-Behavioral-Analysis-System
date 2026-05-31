import re

FILLER_WORDS = [
    "um", "uh", "like", "actually", "basically",
    "literally", "you know", "sort of", "kind of",
]

def analyze(transcript: str, duration_seconds: float) -> dict:
    text  = transcript.strip()
    lower = text.lower()

    words     = text.split()
    word_count = len(words)
    sentences  = [s.strip() for s in re.split(r"[.!?]+", text) if s.strip()]
    sentence_count = len(sentences) or 1
    avg_words_per_sentence = round(word_count / sentence_count, 1)

    speaking_rate_wpm = round((word_count / duration_seconds) * 60, 1) if duration_seconds > 0 and word_count > 0 else 0

    unique_words       = {w.lower().strip(".,!?;:\"'") for w in words}
    unique_word_count  = len(unique_words)
    vocabulary_diversity = round(unique_word_count / word_count, 3) if word_count > 0 else 0

    filler_breakdown: dict[str, int] = {}
    for filler in FILLER_WORDS:
        pattern = r"\b" + re.escape(filler) + r"\b"
        count   = len(re.findall(pattern, lower))
        if count:
            filler_breakdown[filler] = count

    filler_word_count = sum(filler_breakdown.values())
    filler_rate = round((filler_word_count / word_count) * 100, 1) if word_count > 0 else 0

    return {
        "word_count":               word_count,
        "sentence_count":           sentence_count,
        "average_words_per_sentence": avg_words_per_sentence,
        "unique_word_count":        unique_word_count,
        "speaking_rate_wpm":        speaking_rate_wpm,
        "vocabulary_diversity":     vocabulary_diversity,
        "filler_word_count":        filler_word_count,
        "filler_rate":              filler_rate,
        "filler_breakdown":         filler_breakdown,
    }
