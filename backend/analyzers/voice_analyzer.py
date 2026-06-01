import subprocess
import numpy as np
import re
import logging

log = logging.getLogger("voice_analyzer")

# ── Configurable thresholds ───────────────────────────────────────────────────
SAMPLE_RATE       = 16000
SILENCE_DB        = -40.0      # dB below which a frame is considered silent
PAUSE_MIN_SECS    = 0.3        # minimum gap to count as a pause
FRAME_MS          = 20         # RMS frame size in milliseconds
IDEAL_WPM_LOW     = 120
IDEAL_WPM_HIGH    = 170

_HESITATION_RE = re.compile(r"\b(um+|uh+|er+|ah+|hmm+)\b", re.IGNORECASE)


# ── Audio extraction ──────────────────────────────────────────────────────────

def _extract_pcm(video_path: str) -> np.ndarray | None:
    """Decode audio to mono 16-bit PCM at 16 kHz using ffmpeg."""
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le",
        "-ar", str(SAMPLE_RATE), "-ac", "1",
        "-f", "s16le", "pipe:1",
    ]
    try:
        raw = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        if len(raw) < 2:
            return None
        return np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    except Exception as e:
        log.warning("PCM extraction failed: %s", e)
        return None


# ── Frame-level RMS energy ────────────────────────────────────────────────────

def _frame_rms(audio: np.ndarray, frame_samples: int) -> np.ndarray:
    """Split audio into frames and compute RMS energy per frame."""
    n_frames = len(audio) // frame_samples
    frames   = audio[:n_frames * frame_samples].reshape(n_frames, frame_samples)
    rms      = np.sqrt(np.mean(frames ** 2, axis=1))
    return rms


def _rms_to_db(rms: np.ndarray) -> np.ndarray:
    safe = np.where(rms > 1e-10, rms, 1e-10)
    return 20 * np.log10(safe)


# ── Pause detection ───────────────────────────────────────────────────────────

def _detect_pauses(db_frames: np.ndarray, frame_secs: float) -> tuple[int, float, list[float]]:
    """
    Returns (pause_count, avg_pause_secs, pause_durations).
    A pause is a contiguous run of silent frames >= PAUSE_MIN_SECS.
    """
    silent      = db_frames < SILENCE_DB
    pauses:     list[float] = []
    in_pause    = False
    pause_len   = 0

    for s in silent:
        if s:
            in_pause = True
            pause_len += 1
        else:
            if in_pause:
                duration = pause_len * frame_secs
                if duration >= PAUSE_MIN_SECS:
                    pauses.append(round(duration, 2))
                in_pause  = False
                pause_len = 0

    # Catch trailing pause
    if in_pause:
        duration = pause_len * frame_secs
        if duration >= PAUSE_MIN_SECS:
            pauses.append(round(duration, 2))

    avg = round(float(np.mean(pauses)), 2) if pauses else 0.0
    return len(pauses), avg, pauses


# ── Volume stability ──────────────────────────────────────────────────────────

def _volume_stability(db_frames: np.ndarray) -> int:
    """
    Measures how consistent the speaking volume is.
    Low std-dev of speech frames → high stability.
    """
    speech_frames = db_frames[db_frames >= SILENCE_DB]
    if len(speech_frames) < 10:
        return 0
    std = float(np.std(speech_frames))
    # std of ~3 dB = very stable (100), ~15 dB = very unstable (0)
    score = max(0, min(100, round(100 - (std - 3) * (100 / 12))))
    return score


# ── Speaking consistency ──────────────────────────────────────────────────────

def _speaking_consistency(db_frames: np.ndarray, frame_secs: float) -> int:
    """
    Measures ratio of speech frames to total duration.
    High ratio = consistent speaker, low ratio = lots of silence/pauses.
    """
    total   = len(db_frames)
    if total == 0:
        return 0
    speech  = int(np.sum(db_frames >= SILENCE_DB))
    ratio   = speech / total
    return min(100, max(0, round(ratio * 100)))


# ── Clarity, fluency, articulation ───────────────────────────────────────────

def _communication_quality(
    volume_stability:     int,
    speaking_consistency: int,
    pause_count:          int,
    avg_pause_secs:       float,
    speech_rate_wpm:      float,
    hesitation_rate:      float,
) -> dict:
    # Clarity: how clean and stable the audio signal is
    clarity_score = round(
        volume_stability     * 0.50 +
        speaking_consistency * 0.50
    )

    # Fluency: penalise excessive pauses and hesitations
    pause_penalty      = min(40, pause_count * 2)
    hesitation_penalty = min(30, hesitation_rate * 3)
    fluency_score      = max(0, min(100, round(
        100 - pause_penalty - hesitation_penalty
    )))

    # Articulation: speaking rate proximity to ideal range
    if IDEAL_WPM_LOW <= speech_rate_wpm <= IDEAL_WPM_HIGH:
        articulation_score = 100
    elif speech_rate_wpm < IDEAL_WPM_LOW:
        articulation_score = max(0, round(100 - (IDEAL_WPM_LOW - speech_rate_wpm) * 1.2))
    else:
        articulation_score = max(0, round(100 - (speech_rate_wpm - IDEAL_WPM_HIGH) * 1.2))

    def _explain(score: int, label: str) -> str:
        if score >= 85: return f"Excellent {label}"
        if score >= 70: return f"Good {label}"
        if score >= 50: return f"Average {label} — room for improvement"
        return f"Poor {label} — needs significant work"

    return {
        "clarity_score":       clarity_score,
        "fluency_score":       fluency_score,
        "articulation_score":  articulation_score,
        "clarity_explanation":       _explain(clarity_score,      "vocal clarity"),
        "fluency_explanation":       _explain(fluency_score,       "speech fluency"),
        "articulation_explanation":  _explain(articulation_score,  "articulation and pacing"),
    }


# ── Voice confidence score ────────────────────────────────────────────────────

def _voice_confidence(
    volume_stability:     int,
    speaking_consistency: int,
    avg_pause_secs:       float,
    hesitation_rate:      float,
    fluency_score:        int,
) -> tuple[int, str]:
    score = round(
        volume_stability     * 0.25 +
        speaking_consistency * 0.25 +
        fluency_score        * 0.30 +
        max(0, 100 - hesitation_rate * 5) * 0.10 +
        max(0, 100 - avg_pause_secs  * 20) * 0.10
    )
    score = min(100, max(0, score))

    if score >= 80: level = "High"
    elif score >= 65: level = "Moderate"
    elif score >= 45: level = "Low"
    else: level = "Very Low"

    return score, level


# ── Coaching insights ─────────────────────────────────────────────────────────

def _coaching(
    pause_count:          int,
    avg_pause_secs:       float,
    hesitation_rate:      float,
    volume_stability:     int,
    speaking_consistency: int,
    voice_confidence:     int,
    speech_rate_wpm:      float,
) -> list[str]:
    tips: list[str] = []

    if avg_pause_secs > 2.0:
        tips.append("Reduce long pauses during technical explanations — aim for pauses under 1.5 seconds.")
    elif pause_count > 10:
        tips.append("Frequent short pauses detected — practice smoother transitions between thoughts.")

    if hesitation_rate > 5:
        tips.append("High hesitation rate detected — replace 'um', 'uh', 'er' with a brief confident pause.")
    elif hesitation_rate > 2:
        tips.append("Occasional hesitations detected — practice your answers to reduce verbal fillers.")

    if volume_stability < 60:
        tips.append("Voice volume was inconsistent — practice projecting with a steady, controlled tone.")
    elif volume_stability >= 85:
        tips.append("Excellent vocal stability — your voice projected confidence and control.")

    if speaking_consistency < 60:
        tips.append("Maintain a more consistent speaking pace — avoid long stretches of silence.")

    if voice_confidence >= 80:
        tips.append("Excellent vocal confidence — your delivery was strong and authoritative.")
    elif voice_confidence < 50:
        tips.append("Work on vocal confidence — speak with more energy and reduce hesitation.")

    if speech_rate_wpm > IDEAL_WPM_HIGH:
        tips.append(f"Speaking pace was fast ({speech_rate_wpm} WPM) — slow down slightly for clarity.")
    elif 0 < speech_rate_wpm < IDEAL_WPM_LOW:
        tips.append(f"Speaking pace was slow ({speech_rate_wpm} WPM) — aim for a more energetic delivery.")

    if not tips:
        tips.append("Strong vocal delivery overall — maintain this level of consistency.")

    return tips


# ── Main entry point ──────────────────────────────────────────────────────────

def analyze(video_path: str, transcript: str = "", speech_rate_wpm: float = 0) -> dict:
    """
    Analyze vocal characteristics from a video file.

    Args:
        video_path:      Path to the video/audio file.
        transcript:      Optional transcript text for hesitation detection.
        speech_rate_wpm: WPM from transcript analyzer (single source of truth).
    """
    audio = _extract_pcm(video_path)

    if audio is None or len(audio) < SAMPLE_RATE:
        return _silent_result()

    frame_samples = int(SAMPLE_RATE * FRAME_MS / 1000)
    frame_secs    = FRAME_MS / 1000

    rms_frames = _frame_rms(audio, frame_samples)
    db_frames  = _rms_to_db(rms_frames)

    pause_count, avg_pause_secs, pause_durations = _detect_pauses(db_frames, frame_secs)
    vol_stability   = _volume_stability(db_frames)
    speak_consist   = _speaking_consistency(db_frames, frame_secs)

    # Hesitation detection from transcript
    hesitation_count = len(_HESITATION_RE.findall(transcript)) if transcript else 0
    words            = len(transcript.split()) if transcript else 1
    hesitation_rate  = round(hesitation_count / words * 100, 1) if words > 0 else 0.0

    quality = _communication_quality(
        vol_stability, speak_consist,
        pause_count, avg_pause_secs,
        speech_rate_wpm, hesitation_rate,
    )

    voice_conf_score, voice_conf_level = _voice_confidence(
        vol_stability, speak_consist,
        avg_pause_secs, hesitation_rate,
        quality["fluency_score"],
    )

    coaching = _coaching(
        pause_count, avg_pause_secs, hesitation_rate,
        vol_stability, speak_consist,
        voice_conf_score, speech_rate_wpm,
    )

    return {
        # Audio features
        "speech_rate_wpm":       speech_rate_wpm,
        "pause_count":           pause_count,
        "average_pause_seconds": avg_pause_secs,
        "volume_stability":      vol_stability,
        "speaking_consistency":  speak_consist,
        # Hesitation
        "hesitation_count":      hesitation_count,
        "hesitation_rate":       hesitation_rate,
        # Voice confidence
        "voice_confidence_score": voice_conf_score,
        "confidence_level":       voice_conf_level,
        # Communication quality
        "clarity_score":          quality["clarity_score"],
        "fluency_score":          quality["fluency_score"],
        "articulation_score":     quality["articulation_score"],
        "clarity_explanation":    quality["clarity_explanation"],
        "fluency_explanation":    quality["fluency_explanation"],
        "articulation_explanation": quality["articulation_explanation"],
        # Coaching
        "coaching_insights":      coaching,
    }


def _silent_result() -> dict:
    return {
        "speech_rate_wpm":        0,
        "pause_count":            0,
        "average_pause_seconds":  0.0,
        "volume_stability":       0,
        "speaking_consistency":   0,
        "hesitation_count":       0,
        "hesitation_rate":        0.0,
        "voice_confidence_score": 0,
        "confidence_level":       "Very Low",
        "clarity_score":          0,
        "fluency_score":          0,
        "articulation_score":     0,
        "clarity_explanation":    "No audio detected",
        "fluency_explanation":    "No audio detected",
        "articulation_explanation": "No audio detected",
        "coaching_insights":      ["No audio was detected — ensure your microphone is working."],
    }
