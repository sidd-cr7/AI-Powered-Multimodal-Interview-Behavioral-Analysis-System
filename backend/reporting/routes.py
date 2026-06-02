"""
Report, History, Benchmark, and Export endpoints.
Included into main.py via app.include_router(report_router).
"""
import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from analyzers.transcriber          import transcribe, get_duration
from analyzers.face_detector        import analyze as analyze_faces
from analyzers.eye_contact          import analyze as analyze_eyes
from analyzers.transcript_analyzer  import analyze as analyze_transcript
from analyzers.confidence_analyzer  import analyze as analyze_confidence
from analyzers.communication_score  import analyze as score_communication
from analyzers.fusion               import analyze as fuse
from analyzers.voice_analyzer       import analyze as analyze_voice
from analyzers.behavioral.engine    import analyze as analyze_behavior
from analyzers.interview_coach      import generate_report as generate_coaching
from analyzers.benchmark            import benchmark
from history.store                  import (
    save_session, load_session, list_sessions,
    compare_sessions, new_session_id,
)
from reporting.pdf_generator        import generate_pdf
from models.report                  import SessionReport, ReportMetrics

log = logging.getLogger("report_router")

UPLOAD_DIR     = "uploads"
TRANSCRIPT_DIR = "transcripts"

router = APIRouter()


def _full_pipeline(video_path: str, filename: str, role: str) -> tuple[dict, dict, dict, dict, dict, dict, dict, dict]:
    tr = transcribe(video_path, TRANSCRIPT_DIR)
    if tr.get("status") == "silent_audio":
        raise HTTPException(status_code=422, detail="No speech detected in recording")

    transcript = tr["transcript"]
    duration   = tr["duration_seconds"]

    t        = analyze_transcript(transcript, duration)
    c        = analyze_confidence(transcript)
    comm     = score_communication(t["speaking_rate_wpm"], t["vocabulary_diversity"],
                                   t["filler_rate"], c["confidence_language_score"])
    voice    = analyze_voice(video_path, transcript, t["speaking_rate_wpm"])
    face     = analyze_faces(video_path)
    eye      = analyze_eyes(video_path)
    behavior = analyze_behavior(video_path)
    fusion   = fuse(
        face_presence_percentage    = face["face_presence_percentage"],
        eye_contact_percentage      = eye["eye_contact_percentage"],
        communication_score         = comm["communication_score"],
        confidence_language_score   = c["confidence_language_score"],
        voice_confidence_score      = voice["voice_confidence_score"],
        speech_clarity_score        = voice["clarity_score"],
        fluency_score               = voice["fluency_score"],
        attention_score             = behavior["attention_score"],
        posture_score               = behavior["posture_score"],
        professional_presence_score = behavior["professional_presence_score"],
    )

    merged = {
        **t, **c, **comm, **voice, **face, **eye, **behavior, **fusion,
        "eye_contact_percentage":      eye["eye_contact_percentage"],
        "face_presence_percentage":    face["face_presence_percentage"],
        "communication_score":         comm["communication_score"],
        "voice_confidence_score":      voice["voice_confidence_score"],
        "professional_presence_score": behavior["professional_presence_score"],
    }

    coaching = generate_coaching(merged, role=role)
    bench    = benchmark({
        **merged,
        "interview_readiness_score": coaching["interview_readiness"]["interview_readiness_score"],
    })

    metrics = ReportMetrics(
        overall_score               = fusion["overall_score"],
        engagement_score            = fusion["engagement_score"],
        professionalism_score       = fusion["professionalism_score"],
        confidence_score            = fusion["confidence_score"],
        communication_mastery_score = fusion["communication_mastery_score"],
        communication_score         = comm["communication_score"],
        eye_contact_percentage      = eye["eye_contact_percentage"],
        face_presence_percentage    = face["face_presence_percentage"],
        speaking_rate_wpm           = t["speaking_rate_wpm"],
        vocabulary_diversity        = t["vocabulary_diversity"],
        filler_word_count           = t["filler_word_count"],
        filler_rate                 = t["filler_rate"],
        voice_confidence_score      = voice["voice_confidence_score"],
        clarity_score               = voice["clarity_score"],
        fluency_score               = voice["fluency_score"],
        attention_score             = behavior["attention_score"],
        posture_score               = behavior["posture_score"],
        professional_presence_score = behavior["professional_presence_score"],
        restlessness_score          = behavior["restlessness_score"],
        interview_readiness_score   = coaching["interview_readiness"]["interview_readiness_score"],
        response_quality_score      = coaching["response_quality"]["response_quality_score"],
        rating                      = fusion["rating"],
        readiness_level             = coaching["interview_readiness"]["readiness_level"],
    )

    session_id = new_session_id()
    report = SessionReport(
        session_id        = session_id,
        filename          = filename,
        role              = role,
        metrics           = metrics,
        transcript        = tr["transcript"],
        strengths         = [s["title"] + " — " + s["description"] for s in coaching["strengths"]],
        improvements      = [i["title"] + " — " + i["description"] for i in coaching["improvements"]],
        coaching_plan     = coaching["coaching_plan"],
        hr_perspective    = coaching["hr_perspective"],
        executive_summary = coaching["executive_summary"],
        raw_data          = merged,
    )
    save_session(report)
    log.info("Report generated: session=%s overall=%d", session_id, fusion["overall_score"])

    return report, coaching, bench


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/report/generate/{filename}")
def generate_report(filename: str, role: str = "software_engineer"):
    video_path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    report, coaching, bench = _full_pipeline(video_path, filename, role)

    return {
        "session_id": report.session_id,
        "metrics":    report.metrics.model_dump(),
        "coaching":   coaching,
        "benchmark":  bench,
        "report_url": f"/report/download/{report.session_id}",
        "csv_url":    f"/report/export/{report.session_id}/csv",
        "json_url":   f"/report/export/{report.session_id}/json",
    }


@router.get("/report/download/{session_id}")
def download_pdf(session_id: str):
    report = load_session(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Session not found")
    pdf_bytes = generate_pdf(report)
    return Response(
        content    = pdf_bytes,
        media_type = "application/pdf",
        headers    = {"Content-Disposition": f'attachment; filename="report_{session_id}.pdf"'},
    )


@router.get("/report/export/{session_id}/json")
def export_json(session_id: str):
    report = load_session(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Session not found")
    return report.model_dump()


@router.get("/report/export/{session_id}/csv")
def export_csv(session_id: str):
    report = load_session(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Session not found")
    m = report.metrics
    rows = [
        ("session_id",                  report.session_id),
        ("timestamp",                   report.timestamp.isoformat()),
        ("role",                        report.role),
        ("overall_score",               m.overall_score),
        ("engagement_score",            m.engagement_score),
        ("professionalism_score",       m.professionalism_score),
        ("communication_score",         m.communication_score),
        ("eye_contact_percentage",      m.eye_contact_percentage),
        ("voice_confidence_score",      m.voice_confidence_score),
        ("interview_readiness_score",   m.interview_readiness_score),
        ("speaking_rate_wpm",           m.speaking_rate_wpm),
        ("filler_word_count",           m.filler_word_count),
        ("vocabulary_diversity",        m.vocabulary_diversity),
        ("attention_score",             m.attention_score),
        ("posture_score",               m.posture_score),
        ("professional_presence_score", m.professional_presence_score),
        ("rating",                      m.rating),
        ("readiness_level",             m.readiness_level),
    ]
    csv_content = "metric,value\n" + "\n".join(f"{k},{v}" for k, v in rows)
    return Response(
        content    = csv_content,
        media_type = "text/csv",
        headers    = {"Content-Disposition": f'attachment; filename="report_{session_id}.csv"'},
    )


@router.get("/history/list")
def history_list():
    return {"sessions": list_sessions()}


@router.get("/history/compare")
def history_compare(session_a: str, session_b: str):
    result = compare_sessions(session_a, session_b)
    if not result:
        raise HTTPException(status_code=404, detail="One or both sessions not found")
    return result.model_dump()


@router.get("/history/{session_id}")
def history_get(session_id: str):
    report = load_session(session_id)
    if not report:
        raise HTTPException(status_code=404, detail="Session not found")
    return report.model_dump()
