import time
import re
from collections import deque
from dataclasses import dataclass, field

FILLER_WORDS = [
    "um", "uh", "like", "actually", "basically",
    "literally", "you know", "sort of", "kind of",
]

_FILLER_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(f) for f in FILLER_WORDS) + r")\b",
    re.IGNORECASE,
)

# ── Gaze smoothing window (frames) ────────────────────────────────────────────
_SMOOTH_WINDOW  = 5   # majority-vote over last N gaze labels
_HISTORY_LEN    = 120 # rolling eye-contact history (confidence-weighted)


@dataclass
class RealtimeSession:
    session_id:    str
    started_at:    float = field(default_factory=time.time)

    # Vision metrics (updated per frame)
    face_detected: bool  = False
    face_count:    int   = 0
    current_gaze:  str   = "UNKNOWN"
    gaze_confidence: float = 0.0

    # Head pose
    head_yaw:   float = 0.0
    head_pitch: float = 0.0
    head_roll:  float = 0.0

    # Smoothing buffer: (gaze_label, confidence) pairs
    _gaze_buffer:  deque = field(default_factory=lambda: deque(maxlen=_SMOOTH_WINDOW))

    # Eye-contact history: confidence-weighted
    _ec_history:   deque = field(default_factory=lambda: deque(maxlen=_HISTORY_LEN))

    # Speech metrics
    transcript:    str   = ""
    word_count:    int   = 0
    filler_count:  int   = 0

    def update_gaze(self, gaze: str, confidence: float) -> None:
        """
        Add a new gaze sample.  confidence ∈ [0,1].
        Low-confidence frames are stored as TRACKING_LOST and excluded
        from eye-contact scoring.
        """
        if confidence < 0.4:
            gaze = "TRACKING_LOST"

        self._gaze_buffer.append((gaze.upper(), confidence))

        # Majority vote over smoothing window (skip TRACKING_LOST)
        valid = [(g, c) for g, c in self._gaze_buffer if g != "TRACKING_LOST"]
        if valid:
            counts: dict[str, float] = {}
            for g, c in valid:
                counts[g] = counts.get(g, 0) + c
            self.current_gaze    = max(counts, key=lambda k: counts[k])
            self.gaze_confidence = round(counts[self.current_gaze] / sum(counts.values()), 2)
        else:
            self.current_gaze    = "TRACKING_LOST"
            self.gaze_confidence = 0.0

        # Eye-contact history — only record valid frames
        if gaze != "TRACKING_LOST":
            self._ec_history.append((gaze.upper(), confidence))

    @property
    def eye_contact_percentage(self) -> float:
        if not self._ec_history:
            return 0.0
        total_w   = sum(c for _, c in self._ec_history)
        center_w  = sum(c for g, c in self._ec_history if g == "CENTER")
        if total_w == 0:
            return 0.0
        return round(center_w / total_w * 100, 1)

    @property
    def duration_seconds(self) -> float:
        return round(time.time() - self.started_at, 1)

    @property
    def current_wpm(self) -> float:
        mins = self.duration_seconds / 60
        if mins < 0.05 or self.word_count == 0:
            return 0.0
        return round(self.word_count / mins, 1)

    def update_transcript(self, text: str) -> None:
        self.transcript   = text
        self.word_count   = len(text.split())
        self.filler_count = len(_FILLER_PATTERN.findall(text))

    def to_metrics(self) -> dict:
        d    = self.duration_seconds
        mins = int(d) // 60
        secs = int(d) % 60
        return {
            "face_detected":          self.face_detected,
            "face_count":             self.face_count,
            "current_gaze":           self.current_gaze,
            "gaze_confidence":        self.gaze_confidence,
            "eye_contact_percentage": self.eye_contact_percentage,
            "head_orientation": {
                "yaw":   round(self.head_yaw,   1),
                "pitch": round(self.head_pitch, 1),
                "roll":  round(self.head_roll,  1),
            },
            "words_spoken":   self.word_count,
            "current_wpm":    self.current_wpm,
            "filler_words":   self.filler_count,
            "session_duration": f"{mins:02d}:{secs:02d}",
            "transcript":     self.transcript,
        }


# ── In-memory session store ───────────────────────────────────────────────────
_sessions: dict[str, RealtimeSession] = {}


def create_session(session_id: str) -> RealtimeSession:
    s = RealtimeSession(session_id=session_id)
    _sessions[session_id] = s
    return s


def get_session(session_id: str) -> RealtimeSession | None:
    return _sessions.get(session_id)


def delete_session(session_id: str) -> None:
    _sessions.pop(session_id, None)
