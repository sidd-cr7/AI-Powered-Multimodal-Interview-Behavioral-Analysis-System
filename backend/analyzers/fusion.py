from typing import Optional

# ── Configurable weights ──────────────────────────────────────────────────────
# Adjust these values to rebalance the fusion engine.
# Future modules (emotion, voice, gesture) can be added here.
WEIGHTS = {
    "face_presence":        0.20,
    "eye_contact":          0.25,
    "communication":        0.35,
    "confidence_language":  0.20,
    # "emotion":            0.00,   # plug in when ready
    # "voice_confidence":   0.00,
    # "gesture":            0.00,
}


def _rating(score: int) -> str:
    if score >= 90: return "Outstanding"
    if score >= 80: return "Excellent"
    if score >= 70: return "Good"
    if score >= 60: return "Average"
    return "Needs Improvement"


def analyze(
    face_presence_percentage:  float,
    eye_contact_percentage:    float,
    communication_score:       float,
    confidence_language_score: float,
    # Future optional signals — default to None (excluded from scoring)
    emotion_score:             Optional[float] = None,
    voice_confidence_score:    Optional[float] = None,
    gesture_score:             Optional[float] = None,
) -> dict:

    # ── Engagement score ──────────────────────────────────────────────────────
    # How present, attentive, and energetic the candidate appears
    engagement_score = min(100, max(0, round(
        face_presence_percentage * 0.30 +
        eye_contact_percentage   * 0.45 +
        communication_score      * 0.25
    )))

    # ── Professionalism score ─────────────────────────────────────────────────
    # Language quality, composure, and on-camera presence
    professionalism_score = min(100, max(0, round(
        face_presence_percentage   * 0.20 +
        eye_contact_percentage     * 0.25 +
        confidence_language_score  * 0.30 +
        communication_score        * 0.25
    )))

    # ── Confidence score ──────────────────────────────────────────────────────
    # Language confidence weighted with eye contact and communication
    confidence_score = min(100, max(0, round(
        confidence_language_score * 0.50 +
        eye_contact_percentage    * 0.30 +
        communication_score       * 0.20
    )))

    # ── Overall score — weighted composite of all signals ─────────────────────
    active_weights = dict(WEIGHTS)

    # If future signals are provided, redistribute weights proportionally
    future = {
        "emotion":          emotion_score,
        "voice_confidence": voice_confidence_score,
        "gesture":          gesture_score,
    }
    extra_signals = {k: v for k, v in future.items() if v is not None}

    if extra_signals:
        # Shrink existing weights by 10% per extra signal to make room
        shrink = 0.10 * len(extra_signals)
        active_weights = {k: v * (1 - shrink) for k, v in active_weights.items()}
        per_extra = shrink / len(extra_signals)
        for k in extra_signals:
            active_weights[k] = per_extra

    base_inputs = {
        "face_presence":       face_presence_percentage,
        "eye_contact":         eye_contact_percentage,
        "communication":       communication_score,
        "confidence_language": confidence_language_score,
        **extra_signals,
    }

    overall_raw = sum(base_inputs[k] * active_weights[k] for k in active_weights if k in base_inputs)
    overall_score = min(100, max(0, round(overall_raw)))

    # ── Analysis summary ──────────────────────────────────────────────────────
    summary: list[str] = []
    if eye_contact_percentage >= 70:
        summary.append("Strong eye contact maintained throughout the interview")
    elif eye_contact_percentage >= 50:
        summary.append("Moderate eye contact — room for improvement")
    else:
        summary.append("Low eye contact detected — needs significant improvement")

    if face_presence_percentage >= 90:
        summary.append("Consistent on-camera presence detected")
    elif face_presence_percentage < 70:
        summary.append("Candidate was frequently off-camera")

    if communication_score >= 80:
        summary.append("Communication score was above average")
    elif communication_score >= 60:
        summary.append("Communication was adequate but could be stronger")
    else:
        summary.append("Communication quality needs improvement")

    if confidence_language_score >= 70:
        summary.append("Professional and confident language used throughout")
    else:
        summary.append("Language lacked confidence — more assertive phrasing recommended")

    # ── Strengths ─────────────────────────────────────────────────────────────
    strengths: list[str] = []
    if eye_contact_percentage >= 70:
        strengths.append("Maintained strong eye contact")
    if face_presence_percentage >= 90:
        strengths.append("Consistent and professional on-camera presence")
    if communication_score >= 80:
        strengths.append("Communicated at an effective pace with clear language")
    if confidence_language_score >= 70:
        strengths.append("Used confident, action-oriented language")
    if overall_score >= 80:
        strengths.append("Strong overall interview performance")

    # ── Improvements ─────────────────────────────────────────────────────────
    improvements: list[str] = []
    if eye_contact_percentage < 70:
        improvements.append("Maintain more consistent eye contact with the camera")
    if face_presence_percentage < 80:
        improvements.append("Ensure face is clearly visible and well-framed on camera")
    if communication_score < 70:
        improvements.append("Work on speaking pace, vocabulary, and reducing filler words")
    if confidence_language_score < 60:
        improvements.append("Replace uncertain phrases with confident action statements")

    return {
        "engagement_score":      engagement_score,
        "professionalism_score": professionalism_score,
        "confidence_score":      confidence_score,
        "overall_score":         overall_score,
        "rating":                _rating(overall_score),
        "analysis_summary":      summary,
        "strengths":             strengths,
        "improvements":          improvements,
        "weights_used":          {k: round(v, 3) for k, v in active_weights.items()},
    }
