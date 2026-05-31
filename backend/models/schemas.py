from pydantic import BaseModel, Field
from typing import Optional

# ── Transcript Intelligence ───────────────────────────────────────────────────

class TranscriptAnalysisRequest(BaseModel):
    transcript:       str
    duration_seconds: float = Field(gt=0)

class TranscriptAnalysisResponse(BaseModel):
    word_count:                 int
    sentence_count:             int
    average_words_per_sentence: float
    unique_word_count:          int
    speaking_rate_wpm:          float
    vocabulary_diversity:       float
    filler_word_count:          int
    filler_rate:                float
    filler_breakdown:           dict[str, int]

# ── Confidence Language ───────────────────────────────────────────────────────

class ConfidenceAnalysisRequest(BaseModel):
    transcript: str

class ConfidenceAnalysisResponse(BaseModel):
    confidence_language_score: int
    confident_phrases:         int
    uncertain_phrases:         int
    confidence_ratio:          float
    confidence_level:          str
    score_explanation:         list[str]

# ── Communication Score ───────────────────────────────────────────────────────

class CommunicationScoreRequest(BaseModel):
    speaking_rate_wpm:         float
    vocabulary_diversity:      float
    filler_rate:               float
    confidence_language_score: float

class CommunicationScoreBreakdown(BaseModel):
    speaking_rate_score: int
    vocabulary_score:    int
    filler_score:        int
    confidence_score:    int

class CommunicationScoreResponse(BaseModel):
    communication_score: int
    communication_level: str
    score_breakdown:     CommunicationScoreBreakdown
    strengths:           list[str]
    weaknesses:          list[str]

# ── Fusion ────────────────────────────────────────────────────────────────────

class FusionRequest(BaseModel):
    face_presence_percentage:  float
    eye_contact_percentage:    float
    communication_score:       float
    confidence_language_score: float
    emotion_score:             Optional[float] = None
    voice_confidence_score:    Optional[float] = None
    gesture_score:             Optional[float] = None

class FusionResponse(BaseModel):
    engagement_score:      int
    professionalism_score: int
    confidence_score:      int
    overall_score:         int
    rating:                str
    analysis_summary:      list[str]
    strengths:             list[str]
    improvements:          list[str]
    weights_used:          dict[str, float]

# ── Feedback ──────────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    eye_contact_percentage:    Optional[float] = 0
    face_presence_percentage:  Optional[float] = 0
    speaking_rate_wpm:         Optional[float] = 0
    filler_rate:               Optional[float] = 0
    filler_word_count:         Optional[int]   = 0
    vocabulary_diversity:      Optional[float] = 0
    confidence_language_score: Optional[float] = 0
    communication_score:       Optional[float] = 0
    engagement_score:          Optional[float] = 0
    overall_score:             Optional[float] = 0
    emotion_score:             Optional[float] = None
    voice_confidence_score:    Optional[float] = None
    gesture_score:             Optional[float] = None

class FeedbackResponse(BaseModel):
    strengths:                 list[str]
    improvements:              list[str]
    coaching_tips:             list[str]
    interview_readiness_score: int
    readiness_level:           str
    hr_feedback:               str
