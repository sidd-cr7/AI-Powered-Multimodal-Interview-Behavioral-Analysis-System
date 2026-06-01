from typing import Optional

WEIGHTS = {
    "face_presence":       0.12,
    "eye_contact":         0.15,
    "communication":       0.18,
    "confidence_language": 0.12,
    "voice_confidence":    0.12,
    "speech_clarity":      0.08,
    "attention":           0.10,
    "posture":             0.08,
    "presence":            0.05,
}


def _rating(score: int) -> str:
    if score >= 90: return "Outstanding"
    if score >= 80: return "Excellent"
    if score >= 70: return "Good"
    if score >= 60: return "Average"
    return "Needs Improvement"


def analyze(
    face_presence_percentage:    float,
    eye_contact_percentage:      float,
    communication_score:         float,
    confidence_language_score:   float,
    voice_confidence_score:      Optional[float] = None,
    speech_clarity_score:        Optional[float] = None,
    fluency_score:               Optional[float] = None,
    attention_score:             Optional[float] = None,
    posture_score:               Optional[float] = None,
    professional_presence_score: Optional[float] = None,
    emotion_score:               Optional[float] = None,
    gesture_score:               Optional[float] = None,
) -> dict:

    vc   = voice_confidence_score      if voice_confidence_score      is not None else 50.0
    sc   = speech_clarity_score        if speech_clarity_score        is not None else 50.0
    flu  = fluency_score               if fluency_score               is not None else 50.0
    attn = attention_score             if attention_score             is not None else eye_contact_percentage
    post = posture_score               if posture_score               is not None else 50.0
    pres = professional_presence_score if professional_presence_score is not None else 50.0

    # ── Engagement ────────────────────────────────────────────────────────────
    engagement_score = min(100, max(0, round(
        face_presence_percentage * 0.20 +
        eye_contact_percentage   * 0.30 +
        communication_score      * 0.20 +
        vc                       * 0.15 +
        attn                     * 0.15
    )))

    # ── Professionalism ───────────────────────────────────────────────────────
    professionalism_score = min(100, max(0, round(
        face_presence_percentage  * 0.10 +
        eye_contact_percentage    * 0.15 +
        confidence_language_score * 0.20 +
        communication_score       * 0.15 +
        vc                        * 0.15 +
        post                      * 0.15 +
        pres                      * 0.10
    )))

    # ── Confidence ────────────────────────────────────────────────────────────
    confidence_score = min(100, max(0, round(
        confidence_language_score * 0.35 +
        vc                        * 0.30 +
        eye_contact_percentage    * 0.20 +
        attn                      * 0.15
    )))

    # ── Communication mastery ─────────────────────────────────────────────────
    communication_mastery_score = min(100, max(0, round(
        communication_score * 0.35 +
        sc                  * 0.25 +
        flu                 * 0.25 +
        vc                  * 0.15
    )))

    # ── Overall score — dynamic weights ───────────────────────────────────────
    active = dict(WEIGHTS)

    # Zero out signals not provided, redistribute to communication
    if voice_confidence_score is None: active["voice_confidence"] = 0.0
    if speech_clarity_score   is None: active["speech_clarity"]   = 0.0
    if attention_score        is None: active["attention"]        = 0.0
    if posture_score          is None: active["posture"]          = 0.0
    if professional_presence_score is None: active["presence"]   = 0.0

    zeroed = sum(v for v in active.values() if v == 0.0)
    if zeroed > 0:
        active["communication"] += zeroed
    active = {k: v for k, v in active.items() if v > 0}

    # Future signals
    extra: dict[str, float] = {}
    if emotion_score is not None: extra["emotion"] = emotion_score
    if gesture_score is not None: extra["gesture"] = gesture_score
    if extra:
        shrink = 0.06 * len(extra)
        active = {k: v * (1 - shrink) for k, v in active.items()}
        per_extra = shrink / len(extra)
        for k in extra:
            active[k] = per_extra

    inputs = {
        "face_presence":       face_presence_percentage,
        "eye_contact":         eye_contact_percentage,
        "communication":       communication_score,
        "confidence_language": confidence_language_score,
        "voice_confidence":    vc,
        "speech_clarity":      sc,
        "attention":           attn,
        "posture":             post,
        "presence":            pres,
        **extra,
    }

    overall_score = min(100, max(0, round(
        sum(inputs[k] * active[k] for k in active if k in inputs)
    )))

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

    if voice_confidence_score is not None:
        if vc >= 75:
            summary.append("Voice projected strong confidence and authority")
        elif vc < 50:
            summary.append("Vocal confidence was low — work on delivery and reducing hesitation")

    if attention_score is not None:
        if attn >= 75:
            summary.append("Sustained attention and focus demonstrated throughout")
        elif attn < 50:
            summary.append("Attention was inconsistent — reduce gaze shifts and distractions")

    if posture_score is not None:
        if post >= 75:
            summary.append("Stable and professional posture maintained")
        elif post < 50:
            summary.append("Posture was unstable — sit upright and reduce leaning")

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
    if vc >= 75 and voice_confidence_score is not None:
        strengths.append("Voice tone projected confidence and authority")
    if sc >= 75 and speech_clarity_score is not None:
        strengths.append("Excellent vocal clarity and articulation")
    if attn >= 75 and attention_score is not None:
        strengths.append("Sustained attention and focus throughout the interview")
    if post >= 75 and posture_score is not None:
        strengths.append("Stable and professional posture maintained")
    if pres >= 80 and professional_presence_score is not None:
        strengths.append("Outstanding professional presence on camera")
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
    if voice_confidence_score is not None and vc < 60:
        improvements.append("Improve vocal confidence — reduce hesitation and speak with more energy")
    if speech_clarity_score is not None and sc < 60:
        improvements.append("Work on vocal clarity — maintain consistent volume and reduce long pauses")
    if attention_score is not None and attn < 60:
        improvements.append("Reduce gaze shifts — maintain steady focus on the camera")
    if posture_score is not None and post < 60:
        improvements.append("Maintain a more stable posture — sit upright and avoid leaning")
    if professional_presence_score is not None and pres < 60:
        improvements.append("Work on overall professional presence — composure and stability matter")

    return {
        "engagement_score":            engagement_score,
        "professionalism_score":       professionalism_score,
        "confidence_score":            confidence_score,
        "communication_mastery_score": communication_mastery_score,
        "overall_score":               overall_score,
        "rating":                      _rating(overall_score),
        "analysis_summary":            summary,
        "strengths":                   strengths,
        "improvements":                improvements,
        "weights_used":                {k: round(v, 3) for k, v in active.items()},
    }
