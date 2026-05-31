from pydantic import BaseModel
from typing import Optional


# ── Transcript Intelligence ───────────────────────────────────────────────────
class TranscriptAnalysisRequest(BaseModel):
    transcript: str
    duration_seconds: float


class FillerBreakdown(BaseModel):
    um: int = 0
    uh: int = 0
    like: int = 0
    actually: int = 0
    basically: int = 0
    literally: int = 0
    you_know: int = 0
    sort_of: int = 0
    kind_of: int = 0


class TranscriptAnalysisResponse(BaseModel):
    word_count: int
    sentence_count: int
    speaking_rate_wpm: float
    filler_word_count: int
    filler_rate: float
    filler_breakdown: dict[str, int]


# ── Confidence Language ───────────────────────────────────────────────────────
class ConfidenceAnalysisRequest(BaseModel):
    transcript: str


class ConfidenceAnalysisResponse(BaseModel):
    confidence_language_score: float
    confident_phrase_count: int
    uncertain_phrase_count: int
    confident_phrases_found: list[str]
    uncertain_phrases_found: list[str]


# ── Communication Score ───────────────────────────────────────────────────────
class CommunicationScoreRequest(BaseModel):
    speaking_rate_wpm: float
    filler_rate: float
    confidence_language_score: float


class CommunicationScoreResponse(BaseModel):
    communication_score: float
    speaking_rate_score: float
    filler_penalty: float
    confidence_bonus: float


# ── Fusion ────────────────────────────────────────────────────────────────────
class FusionRequest(BaseModel):
    face_presence_percentage: float
    eye_contact_percentage: float
    communication_score: float
    confidence_language_score: float


class FusionResponse(BaseModel):
    engagement_score: float
    overall_score: float
    component_scores: dict[str, float]


# ── Feedback ──────────────────────────────────────────────────────────────────
class FeedbackRequest(BaseModel):
    # Transcript
    word_count: int
    speaking_rate_wpm: float
    filler_word_count: int
    filler_rate: float
    # Confidence
    confidence_language_score: float
    confident_phrase_count: int
    uncertain_phrase_count: int
    # Visual
    face_presence_percentage: float
    eye_contact_percentage: float
    gaze_stability: str
    # Scores
    communication_score: float
    engagement_score: float
    overall_score: float


class FeedbackResponse(BaseModel):
    strengths: list[str]
    improvements: list[str]
    overall_summary: str
