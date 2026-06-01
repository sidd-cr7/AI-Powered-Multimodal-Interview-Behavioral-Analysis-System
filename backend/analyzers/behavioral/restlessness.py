def analyze(
    movement_events: int,
    gaze_shifts:     int,
    leaning_events:  int,
    frames_analyzed: int,
) -> dict:
    if frames_analyzed == 0:
        return _default()

    # Normalise events per 100 frames
    norm = 100 / frames_analyzed
    head_rate   = movement_events * norm
    gaze_rate   = gaze_shifts     * norm
    lean_rate   = leaning_events  * norm

    # Restlessness = weighted sum of normalised event rates
    raw = head_rate * 0.40 + gaze_rate * 0.40 + lean_rate * 0.20

    # Map: 0 events → score 100, raw ≥ 20 → score 0
    restlessness_score = min(100, max(0, round(100 - raw * 5)))

    if restlessness_score >= 80:   level = "Calm"
    elif restlessness_score >= 60: level = "Moderate"
    elif restlessness_score >= 40: level = "Restless"
    else:                          level = "Very Restless"

    return {
        "restlessness_score": restlessness_score,
        "restlessness_level": level,
        "head_movement_rate": round(head_rate, 1),
        "gaze_shift_rate":    round(gaze_rate, 1),
    }


def _default() -> dict:
    return {
        "restlessness_score": 0, "restlessness_level": "Very Restless",
        "head_movement_rate": 0.0, "gaze_shift_rate": 0.0,
    }
