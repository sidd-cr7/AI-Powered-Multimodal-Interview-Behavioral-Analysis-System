from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ReportMetrics(BaseModel):
    overall_score:               int
    engagement_score:            int
    professionalism_score:       int
    confidence_score:            int
    communication_mastery_score: int
    communication_score:         int
    eye_contact_percentage:      float
    face_presence_percentage:    float
    speaking_rate_wpm:           float
    vocabulary_diversity:        float
    filler_word_count:           int
    filler_rate:                 float
    voice_confidence_score:      int
    clarity_score:               int
    fluency_score:               int
    attention_score:             int
    posture_score:               int
    professional_presence_score: int
    restlessness_score:          int
    interview_readiness_score:   int
    response_quality_score:      int
    rating:                      str
    readiness_level:             str


class SessionReport(BaseModel):
    session_id:   str
    timestamp:    datetime = Field(default_factory=datetime.utcnow)
    filename:     str
    role:         str
    metrics:      ReportMetrics
    transcript:   str
    strengths:    list[str]
    improvements: list[str]
    coaching_plan: list[dict]
    hr_perspective: str
    executive_summary: str
    raw_data:     Optional[dict] = None   # full pipeline output


class ProgressComparison(BaseModel):
    session_a_id:                str
    session_b_id:                str
    overall_improvement:         int
    communication_improvement:   int
    eye_contact_improvement:     int
    voice_confidence_improvement: int
    readiness_improvement:       int
    summary:                     str
