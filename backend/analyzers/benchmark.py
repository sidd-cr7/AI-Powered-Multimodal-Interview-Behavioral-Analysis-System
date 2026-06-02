BENCHMARKS = {
    "beginner": {
        "overall_score":               50,
        "communication_score":         50,
        "eye_contact_percentage":      45,
        "voice_confidence_score":      45,
        "interview_readiness_score":   45,
        "professional_presence_score": 45,
    },
    "intermediate": {
        "overall_score":               68,
        "communication_score":         68,
        "eye_contact_percentage":      65,
        "voice_confidence_score":      63,
        "interview_readiness_score":   65,
        "professional_presence_score": 65,
    },
    "advanced": {
        "overall_score":               82,
        "communication_score":         82,
        "eye_contact_percentage":      78,
        "voice_confidence_score":      78,
        "interview_readiness_score":   80,
        "professional_presence_score": 80,
    },
}

_METRICS = list(BENCHMARKS["beginner"].keys())


def benchmark(data: dict) -> dict:
    scores = {k: float(data.get(k, 0)) for k in _METRICS}
    avg    = sum(scores.values()) / len(scores)

    adv_avg  = sum(BENCHMARKS["advanced"].values())  / len(_METRICS)
    int_avg  = sum(BENCHMARKS["intermediate"].values()) / len(_METRICS)

    if avg >= adv_avg:
        level = "Advanced"
    elif avg >= int_avg:
        level = "Intermediate"
    else:
        level = "Beginner"

    comparison: dict[str, dict] = {}
    for metric in _METRICS:
        candidate_val = scores[metric]
        comparison[metric] = {
            "candidate":    round(candidate_val, 1),
            "beginner":     BENCHMARKS["beginner"][metric],
            "intermediate": BENCHMARKS["intermediate"][metric],
            "advanced":     BENCHMARKS["advanced"][metric],
            "vs_advanced":  round(candidate_val - BENCHMARKS["advanced"][metric], 1),
        }

    return {
        "candidate_level": level,
        "candidate_avg":   round(avg, 1),
        "benchmark_comparison": comparison,
    }
