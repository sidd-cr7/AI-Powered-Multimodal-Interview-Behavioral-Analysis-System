import os
import whisper

_model = None

def get_model() -> whisper.Whisper:
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model

def transcribe(video_path: str, transcript_dir: str) -> dict:
    model = get_model()
    result = model.transcribe(video_path)
    text = result["text"].strip()

    # Duration from last segment timestamp
    segments = result.get("segments", [])
    duration = round(segments[-1]["end"], 1) if segments else 0.0

    words = text.split()
    word_count = len(words)
    speaking_rate_wpm = round(word_count / (duration / 60), 1) if duration > 0 else 0

    os.makedirs(transcript_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(video_path))[0]
    with open(os.path.join(transcript_dir, f"{base}.txt"), "w", encoding="utf-8") as f:
        f.write(text)

    return {
        "transcript": text,
        "word_count": word_count,
        "duration_seconds": duration,
        "speaking_rate_wpm": speaking_rate_wpm,
    }
