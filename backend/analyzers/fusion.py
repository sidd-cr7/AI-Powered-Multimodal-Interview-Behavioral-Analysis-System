"""
Multimodal Fusion Weights
─────────────────────────
Engagement Score  (visual presence signals)
  face_presence_percentage   : 30%
  eye_contact_percentage     : 70%

Overall Score  (full multimodal)
  engagement_score           : 35%
  communication_score        : 40%
  confidence_language_score  : 25%

Weights are designed to be easily tunable.
Future modules (emotion, voice, gesture) plug in here.
"""

ENGAGEMENT_WEIGHTS: dict[str, float] = {
    "face_presence_percentage": 0.30,
    "eye_contact_percentage":   0.70,
}

OVERALL_WEIGHTS: dict[str, float] = {
    "engagement_score":          0.35,
    "communication_score":       0.40,
    "confidence_language_score": 0.25,
}


def _weighted(values: dict[str, float], weights: dict[str, float]) -> float:
    return round(sum(values[k] * weights[k] for k in weights), 1)


def analyze(
    face_presence_percentage: float,
    eye_contact_percentage: float,
    communication_score: float,
    confidence_language_score: float,
) -> dict:
    engagement_score = _weighted(
        {
            "face_presence_percentage": face_presence_percentage,
            "eye_contact_percentage":   eye_contact_percentage,
        },
        ENGAGEMENT_WEIGHTS,
    )

    overall_score = _weighted(
        {
            "engagement_score":          engagement_score,
            "communication_score":       communication_score,
            "confidence_language_score": confidence_language_score,
        },
        OVERALL_WEIGHTS,
    )

    return {
        "engagement_score": engagement_score,
        "overall_score": overall_score,
        "component_scores": {
            "face_presence":   round(face_presence_percentage, 1),
            "eye_contact":     round(eye_contact_percentage, 1),
            "communication":   round(communication_score, 1),
            "confidence":      round(confidence_language_score, 1),
        },
    }
