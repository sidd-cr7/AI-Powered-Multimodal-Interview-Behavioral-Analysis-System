export type UploadStatus = "idle" | "uploading" | "success" | "error";

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
