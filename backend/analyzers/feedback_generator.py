"""
Feedback Generator
──────────────────
Rule-based engine that converts all analysis scores into
human-readable strengths, improvements, and a summary.

Each rule is a (condition_fn, message, category) tuple.
category: "strength" | "improvement"

Designed to be extended — add rules without touching existing logic.
"""

from dataclasses import dataclass
from typing import Callable


@dataclass
class FeedbackRule:
    condition: Callable[..., bool]
    message: str
    category: str  # "strength" or "improvement"


# ── Rule definitions ──────────────────────────────────────────────────────────
def _build_rules() -> list[FeedbackRule]:
    return [
        # Eye contact
        FeedbackRule(lambda d: d["eye_contact_percentage"] >= 75,
                     "Maintained strong eye contact throughout the interview.", "strength"),
        FeedbackRule(lambda d: 50 <= d["eye_contact_percentage"] < 75,
                     "Eye contact was adequate but could be more consistent.", "improvement"),
        FeedbackRule(lambda d: d["eye_contact_percentage"] < 50,
                     "Eye contact was low — practice looking directly at the camera.", "improvement"),

        # Face presence
        FeedbackRule(lambda d: d["face_presence_percentage"] >= 90,
                     "Stayed consistently visible and well-framed on camera.", "strength"),
        FeedbackRule(lambda d: d["face_presence_percentage"] < 70,
                     "Face was not always visible — ensure proper camera positioning.", "improvement"),

        # Speaking rate
        FeedbackRule(lambda d: 120 <= d["speaking_rate_wpm"] <= 170,
                     "Spoke at a clear and effective pace (ideal 120–170 WPM).", "strength"),
        FeedbackRule(lambda d: d["speaking_rate_wpm"] > 170,
                     "Speaking pace was too fast — slow down to improve clarity.", "improvement"),
        FeedbackRule(lambda d: 0 < d["speaking_rate_wpm"] < 120,
                     "Speaking pace was too slow — aim for a more energetic delivery.", "improvement"),

        # Filler words
        FeedbackRule(lambda d: d["filler_word_count"] == 0,
                     "Used no filler words — speech was clean and professional.", "strength"),
        FeedbackRule(lambda d: 1 <= d["filler_rate"] <= 3,
                     "Filler word usage was minimal and within acceptable range.", "strength"),
        FeedbackRule(lambda d: 3 < d["filler_rate"] <= 7,
                     "Moderate filler word usage detected — practice pausing instead of filling silence.", "improvement"),
        FeedbackRule(lambda d: d["filler_rate"] > 7,
                     "High filler word usage — significantly reduces perceived confidence.", "improvement"),

        # Confidence language
        FeedbackRule(lambda d: d["confidence_language_score"] >= 75,
                     "Used strong, action-oriented language demonstrating ownership and impact.", "strength"),
        FeedbackRule(lambda d: 50 <= d["confidence_language_score"] < 75,
                     "Language was mostly confident but could include more achievement-focused phrases.", "improvement"),
        FeedbackRule(lambda d: d["confidence_language_score"] < 50,
                     "Language was frequently uncertain — replace hedging phrases with direct, confident statements.", "improvement"),

        # Communication score
        FeedbackRule(lambda d: d["communication_score"] >= 80,
                     "Overall communication quality was strong and professional.", "strength"),
        FeedbackRule(lambda d: d["communication_score"] < 60,
                     "Overall communication needs improvement across pace, clarity, and language.", "improvement"),

        # Engagement
        FeedbackRule(lambda d: d["engagement_score"] >= 80,
                     "Demonstrated high visual engagement and presence.", "strength"),
        FeedbackRule(lambda d: d["engagement_score"] < 55,
                     "Visual engagement was low — focus on camera presence and eye contact.", "improvement"),

        # Gaze stability
        FeedbackRule(lambda d: d["gaze_stability"] == "good",
                     "Gaze was stable and focused, projecting confidence.", "strength"),
        FeedbackRule(lambda d: d["gaze_stability"] == "poor",
                     "Frequent gaze shifts detected — practice maintaining a steady focus.", "improvement"),
    ]


RULES = _build_rules()


# ── Summary templates ─────────────────────────────────────────────────────────
def _overall_summary(overall_score: float) -> str:
    if overall_score >= 85:
        return (f"Excellent performance with an overall score of {overall_score}. "
                "You demonstrated strong communication, confidence, and visual presence.")
    if overall_score >= 70:
        return (f"Good performance with an overall score of {overall_score}. "
                "A few targeted improvements will significantly strengthen your interview presence.")
    if overall_score >= 55:
        return (f"Moderate performance with an overall score of {overall_score}. "
                "Focus on the improvement areas below to build a more compelling interview presence.")
    return (f"Your overall score was {overall_score}. "
            "Significant practice is recommended across communication, confidence, and visual engagement.")


# ── Main function ─────────────────────────────────────────────────────────────
def generate(data: dict) -> dict:
    strengths:    list[str] = []
    improvements: list[str] = []

    for rule in RULES:
        try:
            if rule.condition(data):
                if rule.category == "strength":
                    strengths.append(rule.message)
                else:
                    improvements.append(rule.message)
        except KeyError:
            continue  # skip rules that reference missing keys

    return {
        "strengths":       strengths,
        "improvements":    improvements,
        "overall_summary": _overall_summary(data.get("overall_score", 0)),
    }
