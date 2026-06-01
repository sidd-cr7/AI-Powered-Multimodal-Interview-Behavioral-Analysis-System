"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import RealtimeDashboard from "../components/RealtimeDashboard";

const WS_URL  = "ws://192.168.1.3:8000/ws/realtime";
const FPS     = 1;          // frames per second sent to backend
const SESSION = () => `rt_${Date.now()}`;

type Metrics = {
  face_detected:          boolean;
  face_count:             number;
  current_gaze:           string;
  eye_contact_percentage: number;
  words_spoken:           number;
  current_wpm:            number;
  filler_words:           number;
  session_duration:       string;
  transcript:             string;
};

export default function RealtimePage() {
  const videoRef   = useRef<HTMLVideoElement>(null);
  const canvasRef  = useRef<HTMLCanvasElement>(null);
  const wsRef      = useRef<WebSocket | null>(null);
  const timerRef   = useRef<ReturnType<typeof setInterval> | null>(null);
  const speechRef  = useRef<SpeechRecognition | null>(null);
  const streamRef  = useRef<MediaStream | null>(null);

  const [active,    setActive]    = useState(false);
  const [connected, setConnected] = useState(false);
  const [metrics,   setMetrics]   = useState<Metrics | null>(null);
  const [error,     setError]     = useState<string | null>(null);

  // ── Capture one JPEG frame and send over WebSocket ────────────────────────
  const sendFrame = useCallback(() => {
    const ws     = wsRef.current;
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !video || !canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width  = 320;
    canvas.height = 240;
    ctx.drawImage(video, 0, 0, 320, 240);

    // Extract base64 JPEG (quality 0.6 — good enough for CV, low bandwidth)
    const b64 = canvas.toDataURL("image/jpeg", 0.6).split(",")[1];
    ws.send(JSON.stringify({ type: "frame", data: b64 }));
  }, []);

  // ── Web Speech API — continuous live transcript ───────────────────────────
  const startSpeech = useCallback(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;

    const rec = new SR() as SpeechRecognition;
    rec.continuous      = true;
    rec.interimResults  = true;
    rec.lang            = "en-US";

    let fullText = "";

    rec.onresult = (e: SpeechRecognitionEvent) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) fullText += t + " ";
        else interim = t;
      }
      const combined = (fullText + interim).trim();
      wsRef.current?.send(JSON.stringify({ type: "transcript", text: combined }));
    };

    rec.onerror = (e: SpeechRecognitionErrorEvent) => {
      if (e.error !== "no-speech") console.warn("Speech error:", e.error);
    };

    // Auto-restart on end (browser stops after silence)
    rec.onend = () => { if (wsRef.current?.readyState === WebSocket.OPEN) rec.start(); };

    rec.start();
    speechRef.current = rec;
  }, []);

  // ── Start real-time session ───────────────────────────────────────────────
  const start = async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;

      const sessionId = SESSION();
      const ws = new WebSocket(`${WS_URL}/${sessionId}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        // Start sending frames at FPS rate
        timerRef.current = setInterval(sendFrame, 1000 / FPS);
        startSpeech();
      };

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === "metrics") setMetrics(msg.payload);
      };

      ws.onerror = () => setError("WebSocket connection failed.");
      ws.onclose = () => { setConnected(false); };

      setActive(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Camera access denied.");
    }
  };

  // ── Stop real-time session ────────────────────────────────────────────────
  const stop = () => {
    if (timerRef.current)  clearInterval(timerRef.current);
    if (speechRef.current) speechRef.current.stop();
    if (wsRef.current)     wsRef.current.close();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    setActive(false);
    setConnected(false);
  };

  // Cleanup on unmount
  useEffect(() => () => stop(), []);

  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif", maxWidth: 780 }}>
      {/* Header + nav */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.25rem" }}>
        <h1 style={{ fontSize: "1.1rem", margin: 0 }}>🎙 Real-Time Interview Coach</h1>
        <a href="/" style={{ fontSize: "0.85rem", color: "#457b9d" }}>← Offline Assessment</a>
      </div>

      {/* Controls */}
      <div style={{ display: "flex", gap: "0.75rem" }}>
        <button onClick={start} disabled={active} style={active ? btnDisabled : btnStart}>
          ▶ Start Session
        </button>
        <button onClick={stop} disabled={!active} style={!active ? btnDisabled : btnStop}>
          ■ Stop Session
        </button>
      </div>

      {error && <p style={{ color: "red", marginTop: "0.5rem", fontSize: "0.9rem" }}>{error}</p>}

      {/* Video + hidden canvas */}
      {active && (
        <div style={{ marginTop: "1rem" }}>
          <video ref={videoRef} autoPlay playsInline muted width={480} height={360}
            style={{ borderRadius: 8, background: "#000", display: "block" }} />
        </div>
      )}
      <canvas ref={canvasRef} style={{ display: "none" }} />

      {/* Live dashboard */}
      {active && (
        <RealtimeDashboard metrics={metrics} connected={connected} />
      )}

      {!active && !error && (
        <p style={{ marginTop: "1.5rem", color: "#888", fontSize: "0.9rem" }}>
          Click "Start Session" to begin real-time interview coaching.
          Your webcam feed will be analyzed live for face presence, eye contact, and speech metrics.
        </p>
      )}
    </main>
  );
}

const base: React.CSSProperties = {
  padding: "0.5rem 1.2rem", borderRadius: 6, border: "none",
  cursor: "pointer", fontWeight: 600, fontSize: "0.9rem",
};
const btnStart:   React.CSSProperties = { ...base, background: "#28a745", color: "#fff" };
const btnStop:    React.CSSProperties = { ...base, background: "#dc3545", color: "#fff" };
const btnDisabled: React.CSSProperties = { ...base, background: "#eee", color: "#aaa", cursor: "not-allowed" };
