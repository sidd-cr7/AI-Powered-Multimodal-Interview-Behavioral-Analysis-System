from typing import Optional


def generate(data: dict) -> dict:
    eye        = data.get("eye_contact_percentage",    0)
    face       = data.get("face_presence_percentage",  0)
    wpm        = data.get("speaking_rate_wpm",         0)
    filler_r   = data.get("filler_rate",               0)
    filler_n   = data.get("filler_word_count",         0)
    vocab      = data.get("vocabulary_diversity",      0)
    conf       = data.get("confidence_language_score", 0)
    comm       = data.get("communication_score",       0)
    engagement = data.get("engagement_score",          0)
    overall    = data.get("overall_score",             0)

    # Future signals (no-op until modules are built)
    emotion        = data.get("emotion_score")
    voice_conf     = data.get("voice_confidence_score")
    gesture        = data.get("gesture_score")

    strengths:     list[str] = []
    improvements:  list[str] = []
    coaching_tips: list[str] = []

    # ── Strengths ─────────────────────────────────────────────────────────────
    if eye >= 70:
        strengths.append("Maintained consistent eye contact throughout the interview")
    if face >= 90:
        strengths.append("Consistent and professional on-camera presence")
    if 120 <= wpm <= 170:
        strengths.append("Spoke at an ideal, easy-to-follow pace")
    if filler_r <= 2:
        strengths.append("Minimal filler words — speech was clear and direct")
    if vocab >= 0.65:
        strengths.append("Demonstrated strong and varied vocabulary")
    if conf >= 70:
        strengths.append("Used confident, action-oriented language effectively")
    if comm >= 80:
        strengths.append("Demonstrated strong communication skills")
    if engagement >= 75:
        strengths.append("Maintained high engagement throughout the session")

    # Future module strengths
    if emotion is not None and emotion >= 70:
        strengths.append("Facial expressions conveyed positive engagement")
    if voice_conf is not None and voice_conf >= 70:
        strengths.append("Voice tone projected confidence and authority")
    if gesture is not None and gesture >= 70:
        strengths.append("Body language and gestures were professional and controlled")

    # ── Improvements ──────────────────────────────────────────────────────────
    if eye < 50:
        improvements.append("Eye contact was low — look directly at the camera more consistently")
    elif eye < 70:
        improvements.append("Eye contact could be more consistent, especially during key answers")
    if face < 80:
        improvements.append("Ensure your face is clearly visible and well-lit on camera")
    if wpm > 200:
        improvements.append(f"Speaking pace was too fast ({wpm} WPM) — slow down significantly for clarity")
    elif wpm > 170:
        improvements.append(f"Speaking pace was slightly fast ({wpm} WPM) — aim for 120–170 WPM")
    elif 0 < wpm < 100:
        improvements.append(f"Speaking pace was too slow ({wpm} WPM) — aim for a more energetic delivery")
    if filler_n > 0:
        improvements.append(f"Reduce filler words — {filler_n} detected (e.g. 'um', 'uh', 'like', 'you know')")
    if vocab < 0.5:
        improvements.append("Vocabulary was repetitive — expand word choice for a more polished impression")
    if conf < 50:
        improvements.append("Language lacked confidence — replace hedging phrases with assertive statements")
    elif conf < 70:
        improvements.append("Use more confident language — reduce phrases like 'I think' and 'maybe'")

    # Future module improvements
    if emotion is not None and emotion < 50:
        improvements.append("Facial expressions appeared flat — work on projecting enthusiasm")
    if voice_conf is not None and voice_conf < 50:
        improvements.append("Voice confidence was below average — practice projecting with a steady tone")
    if gesture is not None and gesture < 50:
        improvements.append("Frequent nervous gestures were detected — practice controlled body language")

    # ── Coaching tips ─────────────────────────────────────────────────────────
    if filler_r > 2:
        coaching_tips.append("Pause briefly instead of using filler words — silence signals confidence")
        coaching_tips.append("Record mock answers and count fillers per minute to track improvement")
    if conf < 70:
        coaching_tips.append("Reframe answers using action verbs: 'I built', 'I led', 'I delivered'")
        coaching_tips.append("Replace uncertain phrases with direct statements — own your achievements")
    if eye < 70:
        coaching_tips.append("Place a sticky note near your webcam as a visual reminder to maintain eye contact")
    if wpm > 170 or (0 < wpm < 120):
        coaching_tips.append("Practice with a pacing app to consistently hit the 120–170 WPM sweet spot")
    if overall < 80:
        coaching_tips.append("Practice STAR-method answers (Situation, Task, Action, Result) for structured responses")
    if vocab < 0.6:
        coaching_tips.append("Read industry-relevant articles daily to naturally expand your professional vocabulary")
    if comm < 70:
        coaching_tips.append("Record yourself answering common interview questions and review for clarity and pace")

    # Always include at least one universal tip
    coaching_tips.append("Conduct at least 3 full mock interviews before your next real interview")

    # ── Interview readiness score ─────────────────────────────────────────────
    # Weighted blend of overall performance signals
    readiness_raw = (
        overall * 0.40 +
        comm    * 0.25 +
        conf    * 0.20 +
        eye     * 0.15
    )
    interview_readiness_score = min(100, max(0, round(readiness_raw)))

    if interview_readiness_score >= 90:
        readiness_level = "Highly Prepared"
    elif interview_readiness_score >= 80:
        readiness_level = "Ready"
    elif interview_readiness_score >= 70:
        readiness_level = "Needs More Practice"
    else:
        readiness_level = "Requires Significant Improvement"

    # ── HR feedback (recruiter-style narrative) ───────────────────────────────
    hr_parts: list[str] = []

    if overall >= 80:
        hr_parts.append("The candidate performed well overall and demonstrated a solid interview presence.")
    elif overall >= 65:
        hr_parts.append("The candidate showed reasonable interview skills with some areas to develop.")
    else:
        hr_parts.append("The candidate's interview performance needs improvement across several areas.")

    if comm >= 75:
        hr_parts.append("Communication was clear and effective.")
    else:
        hr_parts.append("Communication clarity could be improved.")

    if eye >= 70:
        hr_parts.append("Good eye contact was maintained throughout.")
    else:
        hr_parts.append("Eye contact was inconsistent and should be improved.")

    if conf >= 70:
        hr_parts.append("The candidate projected confidence through their language choices.")
    else:
        hr_parts.append("Confidence could be improved by using more assertive language and reducing uncertainty phrases.")

    if filler_n > 5:
        hr_parts.append(f"Filler word usage was notable ({filler_n} instances) and detracted from overall delivery.")

    hr_feedback = " ".join(hr_parts)

    # ── Fallback guards ───────────────────────────────────────────────────────
    if not strengths:
        strengths.append("Completed the interview — a solid foundation to build on")
    if not improvements:
        improvements.append("Continue refining your delivery for an even stronger performance")

    return {
        "strengths":                 strengths,
        "improvements":              improvements,
        "coaching_tips":             coaching_tips,
        "interview_readiness_score": interview_readiness_score,
        "readiness_level":           readiness_level,
        "hr_feedback":               hr_feedback,
    }
