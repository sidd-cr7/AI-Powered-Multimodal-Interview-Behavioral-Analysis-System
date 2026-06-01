import logging
from analyzers.behavioral import head_movement, face_visibility, attention, posture, restlessness

log = logging.getLogger("behavioral")


def analyze(video_path: str) -> dict:
    """
    Run all behavioral sub-analyzers and return a unified behavioral assessment.
    Each sub-analyzer is independent — a failure in one does not block others.
    """
    log.info("Behavioral analysis started: %s", video_path)

    # ── Sub-analyzers ─────────────────────────────────────────────────────────
    head   = _safe(head_movement.analyze,   video_path, head_movement._default())
    vis    = _safe(face_visibility.analyze, video_path, face_visibility._default())
    attn   = _safe(attention.analyze,       video_path, attention._default())
    post   = _safe(posture.analyze,         video_path, posture._default())

    rest = restlessness.analyze(
        movement_events = head["movement_events"],
        gaze_shifts     = attn["gaze_shifts"],
        leaning_events  = post["leaning_events"],
        frames_analyzed = max(head["frames_analyzed"], attn["frames_analyzed"], 1),
    )

    log.info(
        "Behavioral: head=%d vis=%d attn=%d posture=%d rest=%d",
        head["head_stability_score"], vis["face_visibility_score"],
        attn["attention_score"], post["posture_score"], rest["restlessness_score"],
    )

    # ── Professional presence score ───────────────────────────────────────────
    professional_presence_score = min(100, max(0, round(
        attn["attention_score"]        * 0.30 +
        post["posture_score"]          * 0.25 +
        vis["face_visibility_score"]   * 0.25 +
        head["head_stability_score"]   * 0.20
    )))

    if professional_presence_score >= 85:   presence_level = "Excellent"
    elif professional_presence_score >= 70: presence_level = "Good"
    elif professional_presence_score >= 50: presence_level = "Fair"
    else:                                   presence_level = "Poor"

    # ── Coaching insights ─────────────────────────────────────────────────────
    coaching: list[str] = []

    if head["head_stability_score"] < 60:
        coaching.append("Reduce head movement — keep your head steady during responses.")
    elif head["head_stability_score"] >= 85:
        coaching.append("Excellent head stability — your composure projected confidence.")

    if vis["face_loss_events"] > 3:
        coaching.append("Ensure your face stays fully visible — avoid leaning out of frame.")

    if attn["attention_score"] < 60:
        coaching.append("Improve eye contact — look directly at the camera more consistently.")
    elif attn["gaze_shifts"] > 15:
        coaching.append("Reduce frequent gaze shifts — steady eye contact signals confidence.")

    if post["posture_score"] < 60:
        coaching.append("Maintain a more stable posture — sit upright and avoid leaning.")
    elif post["posture_score"] >= 85:
        coaching.append("Professional presence remained consistently strong.")

    if rest["restlessness_score"] < 50:
        coaching.append("Reduce restless movements — stillness projects calm and confidence.")

    if professional_presence_score >= 85:
        coaching.append("Outstanding professional presence throughout the interview.")

    if not coaching:
        coaching.append("Behavioral presence was solid — maintain this level of composure.")

    return {
        # Sub-scores
        "head_stability_score":       head["head_stability_score"],
        "movement_events":            head["movement_events"],
        "face_visibility_score":      vis["face_visibility_score"],
        "face_loss_events":           vis["face_loss_events"],
        "attention_score":            attn["attention_score"],
        "attention_level":            attn["attention_level"],
        "gaze_shifts":                attn["gaze_shifts"],
        "posture_score":              post["posture_score"],
        "posture_level":              post["posture_level"],
        "leaning_events":             post["leaning_events"],
        "restlessness_score":         rest["restlessness_score"],
        "restlessness_level":         rest["restlessness_level"],
        # Composite
        "professional_presence_score": professional_presence_score,
        "presence_level":              presence_level,
        "coaching_insights":           coaching,
    }


def _safe(fn, video_path: str, default: dict) -> dict:
    try:
        return fn(video_path)
    except Exception as e:
        log.warning("Behavioral sub-analyzer %s failed: %s", fn.__name__, e)
        return default
