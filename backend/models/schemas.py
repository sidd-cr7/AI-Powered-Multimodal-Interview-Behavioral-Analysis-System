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

# ── Voice Intelligence ────────────────────────────────────────────────────────

class VoiceAnalysisResponse(BaseModel):
    speech_rate_wpm:          float
    pause_count:              int
    average_pause_seconds:    float
    volume_stability:         int
    speaking_consistency:     int
    hesitation_count:         int
    hesitation_rate:          float
    voice_confidence_score:   int
    confidence_level:         str
    clarity_score:            int
    fluency_score:            int
    articulation_score:       int
    clarity_explanation:      str
    fluency_explanation:      str
    articulation_explanation: str
    coaching_insights:        list[str]

# ── Behavioral Intelligence ───────────────────────────────────────────────────

class BehavioralAnalysisResponse(BaseModel):
    head_stability_score:        int
    movement_events:             int
    face_visibility_score:       int
    face_loss_events:            int
    attention_score:             int
    attention_level:             str
    gaze_shifts:                 int
    posture_score:               int
    posture_level:               str
    leaning_events:              int
    restlessness_score:          int
    restlessness_level:          str
    professional_presence_score: int
    presence_level:              str
    coaching_insights:           list[str]

# ── Fusion ────────────────────────────────────────────────────────────────────

class FusionRequest(BaseModel):
    face_presence_percentage:    float
    eye_contact_percentage:      float
    communication_score:         float
    confidence_language_score:   float
    voice_confidence_score:      Optional[float] = None
    speech_clarity_score:        Optional[float] = None
    fluency_score:               Optional[float] = None
    attention_score:             Optional[float] = None
    posture_score:               Optional[float] = None
    professional_presence_score: Optional[float] = None
    emotion_score:               Optional[float] = None
    gesture_score:               Optional[float] = None

class FusionResponse(BaseModel):
    engagement_score:            int
    professionalism_score:       int
    confidence_score:            int
    communication_mastery_score: int
    overall_score:               int
    rating:                      str
    analysis_summary:            list[str]
    strengths:                   list[str]
    improvements:                list[str]
    weights_used:                dict[str, float]

# ── Feedback ──────────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    eye_contact_percentage:      Optional[float] = 0
    face_presence_percentage:    Optional[float] = 0
    speaking_rate_wpm:           Optional[float] = 0
    filler_rate:                 Optional[float] = 0
    filler_word_count:           Optional[int]   = 0
    vocabulary_diversity:        Optional[float] = 0
    confidence_language_score:   Optional[float] = 0
    communication_score:         Optional[float] = 0
    engagement_score:            Optional[float] = 0
    overall_score:               Optional[float] = 0
    voice_confidence_score:      Optional[float] = None
    speech_clarity_score:        Optional[float] = None
    fluency_score:               Optional[float] = None
    hesitation_rate:             Optional[float] = None
    pause_count:                 Optional[int]   = None
    attention_score:             Optional[float] = None
    posture_score:               Optional[float] = None
    professional_presence_score: Optional[float] = None
    emotion_score:               Optional[float] = None
    gesture_score:               Optional[float] = None

class FeedbackResponse(BaseModel):
    strengths:                 list[str]
    improvements:              list[str]
    coaching_tips:             list[str]
    interview_readiness_score: int
    readiness_level:           str
    hr_feedback:               str

# ── Interview Coach ───────────────────────────────────────────────────────────

class CoachingStrength(BaseModel):
    title:       str
    description: str
    metric:      str

class CoachingImprovement(BaseModel):
    title:       str
    description: str
    metric:      str
    priority:    int

class CoachingPlanItem(BaseModel):
    priority:        int
    area:            str
    action:          str
    expected_impact: str
    timeframe:       str

class CoachingReportResponse(BaseModel):
    executive_summary:   str
    candidate_profile:   str
    overall_assessment:  str
    strengths:           list[CoachingStrength]
    improvements:        list[CoachingImprovement]
    coaching_plan:       list[CoachingPlanItem]
    response_quality:    dict
    interview_readiness: dict
    hr_perspective:      str
    role_coaching:       dict
    llm_enhanced:        bool
