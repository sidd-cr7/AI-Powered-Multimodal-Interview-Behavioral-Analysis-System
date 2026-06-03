"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import RealtimeDashboard from "../components/RealtimeDashboard";
import AssessmentPanel from "../components/AssessmentPanel";
import { AssessmentResult } from "../types/analysis";

const WS_BASE      = "ws://localhost:8000/ws/realtime";
const API_BASE     = "http://localhost:8000";
const FPS          = 3;
const RECONNECT_MS = 3000;
const MAX_RETRIES  = 999;

type Metrics = {
  face_detected:          boolean;
  face_count:             number;
  current_gaze:           string;
  gaze_confidence:        number;
  eye_contact_percentage: number;
  head_orientation:       { yaw: number; pitch: number; roll: number };
  words_spoken:           number;
  current_wpm:            number;
  filler_words:           number;
  session_duration:       string;
  transcript:             string;
  whisper_ready:          boolean;
  whisper_transcript:     string | null;
  whisper_confidence:     number | null;
  whisper_quality:        string | null;
  frames_received?:       number;
  frames_processed?:      number;
};

type WhisperResult = { transcript: string; quality: string; confidence: number; duration: number };
type ConnState = "idle" | "connecting" | "connected" | "reconnecting" | "failed" | "stopped";

export default function RealtimePage() {
  const videoRef     = useRef<HTMLVideoElement>(null);
  const canvasRef    = useRef<HTMLCanvasElement>(null);
  const wsRef        = useRef<WebSocket | null>(null);
  const frameTimer   = useRef<ReturnType<typeof setInterval> | null>(null);
  const speechRef    = useRef<SpeechRecognition | null>(null);
  const finalTextRef = useRef("");
  const sendTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const audioRecRef  = useRef<MediaRecorder | null>(null);
  const streamRef    = useRef<MediaStream | null>(null);
  const retriesRef   = useRef(0);
  const sessionId    = useRef(`rt_${Date.now()}`);
  const activeRef    = useRef(false);

  const [active,         setActive]         = useState(false);
  const [connState,      setConnState]      = useState<ConnState>("idle");
  const [metrics,        setMetrics]        = useState<Metrics | null>(null);
  const [liveTranscript,   setLiveTranscript]   = useState("");
  const [transcriptSource, setTranscriptSource] = useState<"speech"|"whisper">("speech");
  const [transcriptConf,   setTranscriptConf]   = useState<number|null>(null);
  const [whisperResult,    setWhisperResult]     = useState<WhisperResult | null>(null);
  const [whisperPending, setWhisperPending] = useState(false);
  const [assessment,     setAssessment]     = useState<AssessmentResult | null>(null);
  const [assessLoading,  setAssessLoading]  = useState(false);
  const [assessError,    setAssessError]    = useState<string | null>(null);
  const [error,          setError]          = useState<string | null>(null);
  const [frameCount,     setFrameCount]     = useState(0);
  const [closeInfo,      setCloseInfo]      = useState<string | null>(null);

  // ── Attach stream after video element mounts ──────────────────────────────
  useEffect(() => {
    if (active && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [active]);

  // ── Send JPEG frame ───────────────────────────────────────────────────────
  const sendFrame = useCallback(() => {
    const ws = wsRef.current;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !video || !canvas) return;
    if (video.readyState < 2) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width = 320;
    canvas.height = 240;
    ctx.drawImage(video, 0, 0, 320, 240);
    const b64 = canvas.toDataURL("image/jpeg", 0.6).split(",")[1];
    ws.send(JSON.stringify({ type: "frame", data: b64 }));
    setFrameCount(n => n + 1);
  }, []);

  // ── Web Speech API ────────────────────────────────────────────────────────
  const startSpeech = useCallback(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      console.warn("[Speech] Not available in this browser — use Chrome or Edge");
      return;
    }

    const rec = new SR() as SpeechRecognition;
    rec.continuous     = true;
    rec.interimResults = true;
    rec.lang           = "en-US";
    speechRef.current  = rec;  // assign BEFORE start

    rec.onstart = () => {
      console.log("[Speech] recognition started");
    };

    rec.onaudiostart = () => {
      console.log("[Speech] audio capture started");
    };

    rec.onspeechstart = () => {
      console.log("[Speech] speech start");
    };

    rec.onspeechend = () => {
      console.log("[Speech] speech end");
    };

    rec.onresult = (e: SpeechRecognitionEvent) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const result = e.results[i];
        const t = result[0].transcript.trim();
        const confidence = result[0].confidence ?? 0;
        if (result.isFinal) {
          if (t) finalTextRef.current = `${finalTextRef.current}${t} `;
          console.log("[Speech] final result", { index: i, transcript: t, confidence });
        } else {
          interim = t;
          console.log("[Speech] interim result", { index: i, transcript: t, confidence });
        }
      }
      const combined = (finalTextRef.current + interim).trim();
      setLiveTranscript(combined);
      console.log("[Speech] transcript update", { transcript: combined });

      if (sendTimerRef.current) clearTimeout(sendTimerRef.current);
      sendTimerRef.current = setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({
            type: "transcript",
            text: combined,
          }));
        }
      }, 300);
    };

    rec.onerror = (e: SpeechRecognitionErrorEvent) => {
      if (e.error === "not-allowed") {
        console.error("[Speech] Microphone permission denied");
      } else if (e.error !== "no-speech" && e.error !== "network") {
        console.warn("[Speech] Error:", e.error);
      }
    };

    rec.onend = () => {
      console.log("[Speech] recognition ended");
      if (!activeRef.current) return;
      // Must delay — browser throws if start() called synchronously in onend
      setTimeout(() => {
        if (!activeRef.current || speechRef.current !== rec) return;
        try {
          rec.start();
        } catch (err) {
          console.warn("[Speech] Restart failed:", err);
        }
      }, 300);
    };

    try {
      rec.start();
      console.log("[Speech] Started");
    } catch (e) {
      console.error("[Speech] Failed to start:", e);
    }
  }, []);

  // ── Audio recorder (Whisper chunks) ──────────────────────────────────────
  const startAudioRecorder = useCallback((stream: MediaStream) => {
    const audioStream = new MediaStream(stream.getAudioTracks());
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";
    const recorder = new MediaRecorder(audioStream, { mimeType });

    recorder.ondataavailable = (e) => {
      // Keep even tiny chunks — first chunk is the WebM container header
      if (e.data.size < 10 || wsRef.current?.readyState !== WebSocket.OPEN) return;
      const reader = new FileReader();
      reader.onloadend = () => {
        const b64 = (reader.result as string).split(",")[1];
        if (b64) wsRef.current?.send(JSON.stringify({ type: "audio_chunk", data: b64 }));
      };
      reader.readAsDataURL(e.data);
    };

    recorder.start(3000);
    audioRecRef.current = recorder;
  }, []);

  const stopAudioRecorder = useCallback(() => {
    const rec = audioRecRef.current;
    if (!rec) return;
    if (rec.state === "recording") {
      rec.requestData();
      rec.stop();
    }
    audioRecRef.current = null;
  }, []);

  // ── Open WebSocket ────────────────────────────────────────────────────────
  const openWS = useCallback(() => {
    if (!activeRef.current) return;
    const ws = new WebSocket(`${WS_BASE}/${sessionId.current}`);
    wsRef.current = ws;
    setConnState("connecting");

    ws.onopen = () => {
      retriesRef.current = 0;
      setConnState("connected");
      setError(null);
      frameTimer.current = setInterval(sendFrame, 1000 / FPS);
      startSpeech();
      startAudioRecorder(streamRef.current!);
      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "ping" }));
        else clearInterval(ping);
      }, 20_000);
      ws.addEventListener("close", () => clearInterval(ping), { once: true });
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "metrics") setMetrics(msg.payload);
        if (msg.type === "whisper_partial") {
          // Mid-session Whisper correction — replaces low-accuracy Web Speech text
          const t: string = msg.payload.transcript;
          const c: number = msg.payload.confidence_score;
          console.log("[WS] whisper_partial received", { transcript: t, confidence: c });
          if (t) {
            const trimmed = t.trim();
            setLiveTranscript(trimmed);
            setTranscriptSource("whisper");
            setTranscriptConf(c);
            finalTextRef.current = `${trimmed} `;
          }
        }
        if (msg.type === "whisper_result") {
          const wr: WhisperResult = {
            transcript: msg.payload.transcript,
            quality:    msg.payload.transcript_quality,
            confidence: msg.payload.confidence_score,
            duration:   msg.payload.duration_seconds,
          };
          console.log("[WS] whisper_result received", { quality: msg.payload.transcript_quality, confidence: msg.payload.confidence_score });
          setWhisperResult(wr);
          setWhisperPending(false);
          generateAssessment(wr);
        }
      } catch { /* ignore malformed */ }
    };

    ws.onerror = () => { /* handled in onclose */ };

    ws.onclose = (e) => {
      const info = `code=${e.code} reason=${e.reason || "none"} clean=${e.wasClean}`;
      setCloseInfo(info);
      if (frameTimer.current) { clearInterval(frameTimer.current); frameTimer.current = null; }
      if (!activeRef.current) { setConnState("stopped"); return; }
      setConnState("reconnecting");
      if (retriesRef.current < MAX_RETRIES) {
        retriesRef.current++;
        setTimeout(openWS, RECONNECT_MS);
      } else {
        setConnState("failed");
        setError(`WebSocket failed. Last close: ${info}`);
      }
    };
  }, [sendFrame, startSpeech, startAudioRecorder]);

  // ── Start ─────────────────────────────────────────────────────────────────
  const start = async () => {
    setError(null);
    setFrameCount(0);
    setWhisperResult(null);
    setAssessment(null);
    setAssessError(null);
    setWhisperPending(false);
    setLiveTranscript("");
    finalTextRef.current = "";
    retriesRef.current   = 0;
    sessionId.current    = `rt_${Date.now()}`;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      streamRef.current = stream;
      activeRef.current = true;
      setActive(true);
      openWS();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Camera/mic access denied.");
    }
  };

  // ── Stop ──────────────────────────────────────────────────────────────────
  const stop = () => {
    activeRef.current = false;
    if (sendTimerRef.current) { clearTimeout(sendTimerRef.current); sendTimerRef.current = null; }
    if (frameTimer.current)   { clearInterval(frameTimer.current);  frameTimer.current = null; }
    if (speechRef.current)    { speechRef.current.stop(); speechRef.current = null; }
    finalTextRef.current = "";

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "end_session" }));
      setWhisperPending(true);
    }
    stopAudioRecorder();

    setTimeout(() => {
      wsRef.current?.close(1000, "user stopped");
      wsRef.current = null;
    }, 800);

    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    setActive(false);
    setConnState("stopped");
    setMetrics(null);
  };

  // ── Assessment ────────────────────────────────────────────────────────────
  const generateAssessment = async (result: WhisperResult) => {
    setAssessLoading(true);
    setAssessError(null);
    try {
      const res = await fetch(`${API_BASE}/analyze/realtime-assessment`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript:               result.transcript,
          duration_seconds:         result.duration,
          eye_contact_percentage:   metrics?.eye_contact_percentage ?? 0,
          face_presence_percentage: metrics?.face_detected ? 100 : 0,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setAssessment(await res.json());
    } catch (e) {
      setAssessError(e instanceof Error ? e.message : "Assessment failed.");
    } finally {
      setAssessLoading(false);
    }
  };

  useEffect(() => () => stop(), []);

  const stateLabel: Record<ConnState, string> = {
    idle: "● Idle", connecting: "◌ Connecting…", connected: "● LIVE",
    reconnecting: "◌ Reconnecting…", failed: "✖ Failed", stopped: "■ Stopped",
  };
  const stateColor: Record<ConnState, string> = {
    idle: "#888", connecting: "#fd7e14", connected: "#28a745",
    reconnecting: "#fd7e14", failed: "#dc3545", stopped: "#888",
  };

  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif", maxWidth: 780 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.25rem" }}>
        <h1 style={{ fontSize: "1.1rem", margin: 0 }}>🎙 Real-Time Interview Coach</h1>
        <a href="/" style={{ fontSize: "0.85rem", color: "#457b9d" }}>← Offline Assessment</a>
      </div>

      <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
        <button onClick={start} disabled={active} style={active ? btnDisabled : btnStart}>▶ Start Session</button>
        <button onClick={stop} disabled={!active} style={!active ? btnDisabled : btnStop}>■ Stop Session</button>
        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: stateColor[connState] }}>
          {stateLabel[connState]}
        </span>
        {connState === "connected" && (
          <span style={{ fontSize: "0.75rem", color: "#888" }}>{frameCount} frames</span>
        )}
      </div>

      {error && (
        <div style={{ marginTop: "0.75rem", background: "#fff3cd", border: "1px solid #ffc107", borderRadius: 6, padding: "0.75rem 1rem", fontSize: "0.9rem" }}>
          ⚠ {error}
          {closeInfo && <div style={{ marginTop: "0.3rem", fontSize: "0.75rem", color: "#888", fontFamily: "monospace" }}>{closeInfo}</div>}
        </div>
      )}

      {active && (
        <div style={{ marginTop: "1rem" }}>
          <video ref={videoRef} autoPlay playsInline muted width={480} height={360}
            style={{ borderRadius: 8, background: "#000", display: "block" }} />
        </div>
      )}
      <canvas ref={canvasRef} style={{ display: "none" }} />

      {active && (
        <RealtimeDashboard
          metrics={metrics}
          liveTranscript={liveTranscript}
          transcriptSource={transcriptSource}
          transcriptConf={transcriptConf}
          connected={connState === "connected"}
        />
      )}

      {whisperPending && !whisperResult && (
        <div style={{ marginTop: "1.5rem", color: "#fd7e14", fontSize: "0.9rem" }}>
          ⏳ Processing transcript with Faster-Whisper…
        </div>
      )}

      {!active && whisperResult && (
        <section style={{ marginTop: "1.5rem", borderTop: "1px solid #eee", paddingTop: "1.25rem" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
            <span style={{ fontSize: "1rem" }}>🎯 Final Transcript</span>
            <span style={{ fontSize: "0.75rem", background: "#d4edda", color: "#155724", borderRadius: 4, padding: "0.2rem 0.5rem" }}>
              Faster-Whisper · {whisperResult.quality} · {whisperResult.confidence}% confidence
            </span>
          </div>
          <div style={{ background: "#f4f4f4", borderRadius: 8, padding: "1rem", fontSize: "0.95rem", lineHeight: 1.7 }}>
            {whisperResult.transcript || <em style={{ color: "#aaa" }}>No speech detected.</em>}
          </div>
        </section>
      )}

      {!active && (
        <AssessmentPanel
          result={assessment}
          loading={assessLoading}
          error={assessError}
          onFetch={() => whisperResult && generateAssessment(whisperResult)}
        />
      )}

      {!active && connState === "idle" && (
        <p style={{ marginTop: "1.5rem", color: "#888", fontSize: "0.9rem" }}>
          Click <strong>Start Session</strong> to begin. Use <strong>Chrome or Edge</strong> for live transcript support.
        </p>
      )}
    </main>
  );
}

const base: React.CSSProperties = { padding: "0.5rem 1.2rem", borderRadius: 6, border: "none", cursor: "pointer", fontWeight: 600, fontSize: "0.9rem" };
const btnStart:    React.CSSProperties = { ...base, background: "#28a745", color: "#fff" };
const btnStop:     React.CSSProperties = { ...base, background: "#dc3545", color: "#fff" };
const btnDisabled: React.CSSProperties = { ...base, background: "#eee", color: "#aaa", cursor: "not-allowed" };
