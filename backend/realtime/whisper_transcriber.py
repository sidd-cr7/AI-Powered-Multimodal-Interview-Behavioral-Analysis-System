"""
Faster-Whisper transcriber for realtime session audio.

Two modes:
  transcribe_chunk(chunks)   — fast, runs every ~15s mid-session for live corrections
  transcribe_session(chunks) — high quality, runs at session end with full context
"""
import logging
import os
import subprocess
import tempfile

import numpy as np
from faster_whisper import WhisperModel

log = logging.getLogger("whisper_rt")

_model: WhisperModel | None = None

# Cache location can be configured; default is HuggingFace cache.
# This module must never download during active transcription.
WHISPER_MODEL_SIZE = "base"
INTERVIEW_PROMPT   = (

    "Job interview. Candidate answering behavioral and technical questions "
    "about their professional experience and skills."
)
_HALLUCINATIONS = [
    "thank you for watching", "thanks for watching", "please subscribe",
    "subtitles by", "transcribed by", "www.", ".com", "like and subscribe",
]


def _get_model() -> WhisperModel:
    """Load Whisper model exactly once and reuse it.

    IMPORTANT: This function must not trigger downloads during active
    realtime transcription.
    """
    global _model
    if _model is not None:
        log.info("[Whisper] Reusing cached model")
        return _model

    log.info("[Whisper] Loading model...")

    # If you want strict offline behavior, download the model once during setup
    # so it exists in the local HuggingFace cache.
    # Setting local_files_only=True prevents runtime downloads.
    try:
        _model = WhisperModel(
            WHISPER_MODEL_SIZE,
            device="cpu",
            compute_type="int8",
            local_files_only=True,
        )
    except Exception as e:
        # If the model isn't present locally, we avoid downloading during
        # realtime transcription and fail fast with a clear error.
        log.error("[Whisper] Local model load failed: %s", e)
        raise

    log.info("[Whisper] Model loaded successfully")
    return _model




def _chunks_to_pcm(chunks: list[bytes]) -> np.ndarray | None:
    raw = b"".join(chunks)
    if len(raw) < 512:
        return None
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
        f.write(raw)
        tmp = f.name
    try:
        out = subprocess.check_output([
            "ffmpeg", "-y", "-i", tmp,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            "-f", "s16le", "pipe:1",
        ], stderr=subprocess.DEVNULL)
        if len(out) < 2:
            return None
        return np.frombuffer(out, dtype=np.int16).astype(np.float32) / 32768.0
    except Exception as e:
        log.warning("[Whisper] ffmpeg failed: %s", e)
        return None
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _run_whisper(audio: np.ndarray, beam_size: int = 3, prev_text: str = "") -> dict:
    # Model must already be cached by _get_model(); never reload.
    model = _get_model()

    prompt = INTERVIEW_PROMPT
    if prev_text:
        # Feed last 200 chars of previous transcript as context
        prompt = INTERVIEW_PROMPT + " " + prev_text[-200:]

    audio_duration = round(audio.shape[0] / 16000.0, 1)
    log.info("[Whisper] transcribing %.1fs audio with beam=%d prev_text_chars=%d", audio_duration, beam_size, len(prev_text))

    segments_gen, info = model.transcribe(
        audio,
        language="en",
        initial_prompt=prompt,
        beam_size=beam_size,
        best_of=beam_size,
        temperature=0.0,
        condition_on_previous_text=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 400},
        no_speech_threshold=0.55,
        log_prob_threshold=-1.0,
        compression_ratio_threshold=2.4,
        word_timestamps=False,
    )

    parts, logprobs = [], []
    for seg in segments_gen:
        t = seg.text.strip()
        if not t:
            continue
        if any(h in t.lower() for h in _HALLUCINATIONS):
            continue
        if seg.no_speech_prob > 0.75:
            continue
        parts.append(t)
        logprobs.append(seg.avg_logprob)

    transcript = " ".join(parts).strip()
    words      = transcript.split()
    duration   = float(info.duration or 1.0)
    conf, qual = _score(logprobs, len(words), duration)

    return {
        "transcript":         transcript,
        "word_count":         len(words),
        "duration_seconds":   round(duration, 1),
        "speaking_rate_wpm":  round(len(words) / (duration / 60), 1) if duration > 0 else 0,
        "confidence_score":   conf,
        "transcript_quality": qual,
        "source":             "faster-whisper",
    }


def transcribe_chunk(chunks: list[bytes], prev_text: str = "") -> dict:
    """
    Fast mid-session transcription — higher beam_size for better accuracy.
    Called every ~10s to progressively correct the live transcript.
    """
    if not chunks:
        return _empty()
    audio = _chunks_to_pcm(chunks)
    if audio is None or len(audio) < 16000 * 1.0:   # need at least 1 second
        return _empty()
    try:
        return _run_whisper(audio, beam_size=3, prev_text=prev_text)
    except Exception as e:
        log.error("[Whisper] Chunk transcription failed: %s", e)
        return _empty()


def transcribe_session(chunks: list[bytes]) -> dict:
    """
    High-quality full-session transcription — beam_size=5, run at end_session.
    """
    if not chunks:
        return _empty()
    audio = _chunks_to_pcm(chunks)
    if audio is None or len(audio) < 16000 * 0.5:
        return _empty()
    try:
        return _run_whisper(audio, beam_size=5)
    except Exception as e:
        log.error("[Whisper] Session transcription failed: %s", e)
        return _empty()


def _score(logprobs: list[float], word_count: int, duration: float) -> tuple[int, str]:
    if not logprobs:
        return 0, "poor"
    avg_lp = sum(logprobs) / len(logprobs)
    score  = int(max(0, min(100, round((avg_lp + 1.5) / 1.5 * 100))))
    if duration > 5 and word_count > 0 and (word_count / duration) < 0.33:
        score = max(0, score - 15)
    quality = (
        "excellent" if score >= 85 else
        "good"      if score >= 65 else
        "fair"      if score >= 40 else
        "poor"
    )
    return score, quality


def _empty() -> dict:
    return {
        "transcript": "", "word_count": 0, "duration_seconds": 0.0,
        "speaking_rate_wpm": 0, "confidence_score": 0,
        "transcript_quality": "poor", "source": "faster-whisper",
    }
