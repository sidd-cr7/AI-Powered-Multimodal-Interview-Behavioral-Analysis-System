import os
import json
import uuid
import logging
from datetime import datetime, timezone
from backend.models.report import SessionReport, ProgressComparison


log = logging.getLogger("history")

HISTORY_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "sessions")
os.makedirs(HISTORY_DIR, exist_ok=True)


def _path(session_id: str) -> str:
    return os.path.join(HISTORY_DIR, f"{session_id}.json")


def save_session(report: SessionReport) -> str:
    path = _path(report.session_id)
    with open(path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))
    log.info("Session saved: %s", report.session_id)
    return report.session_id


def load_session(session_id: str) -> SessionReport | None:
    path = _path(session_id)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return SessionReport.model_validate_json(f.read())


def list_sessions() -> list[dict]:
    sessions = []
    for fname in sorted(os.listdir(HISTORY_DIR), reverse=True):
        if not fname.endswith(".json"):
            continue
        sid = fname[:-5]
        try:
            s = load_session(sid)
            if s:
                sessions.append({
                    "session_id":   s.session_id,
                    "timestamp":    s.timestamp.isoformat(),
                    "filename":     s.filename,
                    "role":         s.role,
                    "overall_score": s.metrics.overall_score,
                    "rating":       s.metrics.rating,
                    "readiness_level": s.metrics.readiness_level,
                })
        except Exception as e:
            log.warning("Could not load session %s: %s", sid, e)
    return sessions


def compare_sessions(id_a: str, id_b: str) -> ProgressComparison | None:
    a = load_session(id_a)
    b = load_session(id_b)
    if not a or not b:
        return None

    def diff(new: int | float, old: int | float) -> int:
        return round(float(new) - float(old))

    overall_imp = diff(b.metrics.overall_score,           a.metrics.overall_score)
    comm_imp    = diff(b.metrics.communication_score,     a.metrics.communication_score)
    eye_imp     = diff(b.metrics.eye_contact_percentage,  a.metrics.eye_contact_percentage)
    voice_imp   = diff(b.metrics.voice_confidence_score,  a.metrics.voice_confidence_score)
    ready_imp   = diff(b.metrics.interview_readiness_score, a.metrics.interview_readiness_score)

    if overall_imp > 5:
        summary = f"Strong improvement of {overall_imp} points overall between sessions."
    elif overall_imp > 0:
        summary = f"Modest improvement of {overall_imp} points. Keep practising consistently."
    elif overall_imp == 0:
        summary = "Performance was consistent across both sessions."
    else:
        summary = f"Score decreased by {abs(overall_imp)} points. Review coaching tips and retry."

    return ProgressComparison(
        session_a_id                 = id_a,
        session_b_id                 = id_b,
        overall_improvement          = overall_imp,
        communication_improvement    = comm_imp,
        eye_contact_improvement      = eye_imp,
        voice_confidence_improvement = voice_imp,
        readiness_improvement        = ready_imp,
        summary                      = summary,
    )


def new_session_id() -> str:
    return str(uuid.uuid4())[:8].upper()
