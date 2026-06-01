import time
import re
from dataclasses import dataclass, field

FILLER_WORDS = [
    "um", "uh", "like", "actually", "basically",
    "literally", "you know", "sort of", "kind of",
]

_FILLER_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(f) for f in FILLER_WORDS) + r")\b",
    re.IGNORECASE,
)


@dataclass
class RealtimeSession:
    session_id:    str
    started_at:    float = field(default_factory=time.time)

    # Vision metrics (updated per frame)
    face_detected: bool  = False
    face_count:    int   = 0
    current_gaze:  str   = "UNKNOWN"

    # Rolling eye contact (last 60 gaze samples)
    _gaze_history: list[str] = field(default_factory=list)
    _MAX_HISTORY:  int       = 60

    # Speech metrics (updated from frontend Web Speech API)
    transcript:    str   = ""
    word_count:    int   = 0
    filler_count:  int   = 0

    def update_gaze(self, gaze: str) -> None:
        self.current_gaze = gaze.upper()
        self._gaze_history.append(gaze)
        if len(self._gaze_history) > self._MAX_HISTORY:
            self._gaze_history.pop(0)

    @property
    def eye_contact_percentage(self) -> float:
        if not self._gaze_history:
            return 0.0
        center = sum(1 for g in self._gaze_history if g.lower() == "center")
        return round(center / len(self._gaze_history) * 100, 1)

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
        self.transcript = text
        words = text.split()
        self.word_count   = len(words)
        self.filler_count = len(_FILLER_PATTERN.findall(text))

    def to_metrics(self) -> dict:
        d = self.duration_seconds
        mins  = int(d) // 60
        secs  = int(d) % 60
        return {
            "face_detected":          self.face_detected,
            "face_count":             self.face_count,
            "current_gaze":           self.current_gaze,
            "eye_contact_percentage": self.eye_contact_percentage,
            "words_spoken":           self.word_count,
            "current_wpm":            self.current_wpm,
            "filler_words":           self.filler_count,
            "session_duration":       f"{mins:02d}:{secs:02d}",
            "transcript":             self.transcript,
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
