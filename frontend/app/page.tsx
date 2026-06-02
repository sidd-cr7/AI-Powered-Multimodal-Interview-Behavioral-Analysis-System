"use client";

import { useRef, useEffect, useState } from "react";
import Controls       from "./components/Controls";
import TranscriptPanel from "./components/TranscriptPanel";
import FacePanel      from "./components/FacePanel";
import EyeContactPanel from "./components/EyeContactPanel";
import AssessmentPanel from "./components/AssessmentPanel";
import ReportPanel    from "./components/ReportPanel";
import {
  UploadStatus, TranscriptResult, FaceResult, EyeResult, AssessmentResult,
} from "./types/analysis";

const API      = "http://localhost:8000";
const FILENAME = "interview.webm";

export default function Home() {
  const videoRef         = useRef<HTMLVideoElement>(null);
  const streamRef        = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef        = useRef<Blob[]>([]);

  const [active,      setActive]      = useState(false);
  const [recording,   setRecording]   = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [recordedUrl, setRecordedUrl] = useState<string | null>(null);

  const [uploadStatus,      setUploadStatus]      = useState<UploadStatus>("idle");
  const [transcript,        setTranscript]        = useState<TranscriptResult | null>(null);
  const [transcriptLoading, setTranscriptLoading] = useState(false);
  const [transcriptError,   setTranscriptError]   = useState<string | null>(null);
  const [faceResult,        setFaceResult]        = useState<FaceResult | null>(null);
  const [faceLoading,       setFaceLoading]       = useState(false);
  const [eyeResult,         setEyeResult]         = useState<EyeResult | null>(null);
  const [eyeLoading,        setEyeLoading]        = useState(false);
  const [assessment,        setAssessment]        = useState<AssessmentResult | null>(null);
  const [assessLoading,     setAssessLoading]     = useState(false);
  const [assessError,       setAssessError]       = useState<string | null>(null);

  // ── Camera ──────────────────────────────────────────────────────────────────
  const startCamera = async () => {
    setCameraError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      setActive(true);
    } catch (err) {
      setCameraError(err instanceof Error ? err.message : "Camera access denied.");
    }
  };

  useEffect(() => {
    return () => streamRef.current?.getTracks().forEach(t => t.stop());
  }, []);

  // ── Recording ───────────────────────────────────────────────────────────────
  const startRecording = () => {
    if (!streamRef.current) return;
    chunksRef.current = [];
    const recorder = new MediaRecorder(streamRef.current);
    recorder.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "video/webm" });
      setRecordedUrl(URL.createObjectURL(blob));
      uploadRecording(blob);
    };
    mediaRecorderRef.current = recorder;
    recorder.start();
    setRecording(true);
  };

  const stopRecording = () => { mediaRecorderRef.current?.stop(); setRecording(false); };

  // ── Upload ──────────────────────────────────────────────────────────────────
  const uploadRecording = async (blob: Blob) => {
    setUploadStatus("uploading");
    const form = new FormData();
    form.append("file", blob, FILENAME);
    try {
      const res = await fetch(`${API}/upload`, { method: "POST", body: form });
      if (!res.ok) throw new Error();
      setUploadStatus("success");
    } catch {
      setUploadStatus("error");
    }
  };

  // ── Transcript ──────────────────────────────────────────────────────────────
  const fetchTranscript = async () => {
    setTranscriptLoading(true); setTranscriptError(null);
    try {
      const res = await fetch(`${API}/transcribe/${FILENAME}`, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setTranscript(await res.json());
    } catch (e) {
      setTranscriptError(e instanceof Error ? e.message : "Transcription failed.");
    } finally {
      setTranscriptLoading(false);
    }
  };

  // ── Face ────────────────────────────────────────────────────────────────────
  const fetchFaceAnalysis = async () => {
    setFaceLoading(true);
    try {
      const res = await fetch(`${API}/analyze/face/${FILENAME}`, { method: "POST" });
      setFaceResult(await res.json());
    } finally {
      setFaceLoading(false);
    }
  };

  // ── Eye contact ─────────────────────────────────────────────────────────────
  const fetchEyeContact = async () => {
    setEyeLoading(true);
    try {
      const res = await fetch(`${API}/analyze/eye-contact/${FILENAME}`, { method: "POST" });
      setEyeResult(await res.json());
    } finally {
      setEyeLoading(false);
    }
  };

  // ── Full assessment ─────────────────────────────────────────────────────────
  const fetchAssessment = async () => {
    setAssessLoading(true); setAssessError(null);
    try {
      const res = await fetch(`${API}/analyze/interview/${FILENAME}`, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setAssessment(await res.json());
    } catch (e) {
      setAssessError(e instanceof Error ? e.message : "Assessment failed.");
    } finally {
      setAssessLoading(false);
    }
  };

  const uploaded = uploadStatus === "success";

  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif", maxWidth: 780 }}>
      <h1 style={{ fontSize: "1.15rem", marginBottom: "0.25rem" }}>
        AI-Powered Multimodal Interview Behavioral Analysis System
      </h1>
      <p style={{ fontSize: "0.8rem", color: "#888", marginBottom: "1.5rem" }}>
        Professional Interview Assessment Platform
      </p>

      <Controls
        active={active}
        recording={recording}
        uploadStatus={uploadStatus}
        onStartCamera={startCamera}
        onStartRecording={startRecording}
        onStopRecording={stopRecording}
      />

      {cameraError && <p style={{ color: "red", marginTop: "0.5rem" }}>{cameraError}</p>}

      {active && (
        <div style={{ marginTop: "1rem" }}>
          <video ref={videoRef} autoPlay playsInline muted width="640" height="480"
            style={{ borderRadius: 8, background: "#000", display: "block" }} />
        </div>
      )}

      {recordedUrl && (
        <section style={{ marginTop: "1.5rem" }}>
          <h2 style={{ fontSize: "1rem" }}>Recorded Preview</h2>
          <video src={recordedUrl} controls width="640" height="480"
            style={{ borderRadius: 8, display: "block" }} />
          <a href={recordedUrl} download="interview.webm"
            style={{ display: "inline-block", marginTop: "0.5rem", fontSize: "0.9rem" }}>
            ⬇ Download Recording
          </a>
        </section>
      )}

      {uploaded && (
        <>
          <TranscriptPanel
            result={transcript}
            loading={transcriptLoading}
            error={transcriptError}
            onFetch={fetchTranscript}
          />
          <FacePanel
            result={faceResult}
            loading={faceLoading}
            onFetch={fetchFaceAnalysis}
          />
          <EyeContactPanel
            result={eyeResult}
            loading={eyeLoading}
            onFetch={fetchEyeContact}
          />
          <AssessmentPanel
            result={assessment}
            loading={assessLoading}
            error={assessError}
            onFetch={fetchAssessment}
          />
          <ReportPanel
            api={API}
            filename={FILENAME}
          />
        </>
      )}
    </main>
  );
}
