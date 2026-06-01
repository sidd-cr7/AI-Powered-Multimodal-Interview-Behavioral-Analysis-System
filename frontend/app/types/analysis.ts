export type UploadStatus = "idle" | "uploading" | "success" | "error";

export type AssessmentResult = {
  transcript_analysis: {
    word_count: number;
    sentence_count: number;
    speaking_rate_wpm: number;
    vocabulary_diversity: number;
    filler_word_count: number;
    filler_rate: number;
    filler_breakdown: Record<string, number>;
  };
  confidence_analysis: {
    confidence_language_score: number;
    confident_phrases: number;
    uncertain_phrases: number;
    confidence_level: string;
  };
  communication_analysis: {
    communication_score: number;
    communication_level: string;
  };
  face_analysis: {
    face_presence_percentage: number;
    face_detected: boolean;
  };
  eye_contact_analysis: {
    eye_contact_percentage: number;
    gaze_stability: string;
  };
  fusion_analysis: {
    overall_score: number;
    engagement_score: number;
    professionalism_score: number;
    confidence_score: number;
    rating: string;
  };
  feedback: {
    strengths: string[];
    improvements: string[];
    coaching_tips: string[];
    interview_readiness_score: number;
    readiness_level: string;
    hr_feedback: string;
  };
};

export type TranscriptResult = {
  filename: string;
  transcript: string;
  word_count: number;
  duration_seconds: number;
  speaking_rate_wpm: number;
  confidence_score: number;
  transcript_quality: "excellent" | "good" | "fair" | "poor";
  status: "ok" | "silent_audio";
};

export type FaceResult = {
  face_detected: boolean;
  face_count: number;
  frames_processed: number;
  frames_with_face: number;
  face_presence_percentage: number;
};

export type EyeResult = {
  eye_contact_percentage: number;
  looking_away_events: number;
  gaze_stability: "good" | "moderate" | "poor";
  frames_processed: number;
  gaze_distribution: {
    center: number;
    left: number;
    right: number;
    down: number;
  };
};
