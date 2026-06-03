"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import RealtimeDashboard from "../components/RealtimeDashboard";

const WS_BASE      = "ws://localhost:8000/ws/realtime";
const FPS          = 3;    // 3fps — backend MediaPipe needs ~300ms per frame
const RECONNECT_MS = 3000;
const MAX_RETRIES  = 5;

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

type ConnState = "idle" | "connecting" | "connected" | "reconnecting" | "failed" | "stopped";

export default function RealtimePage() {
  const videoRef    = useRef<HTMLVideoElement>(null);
  const canvasRef   = useRef<HTMLCanvasElement>(null);
  const wsRef       = useRef<WebSocket | null>(null);
  const frameTimer  = useRef<ReturnType<typeof setInterval> | null>(null);
  const speechRef   = useRef<SpeechRecognition | null>(null);
  const streamRef   = useRef<MediaStream | null>(null);
  const retriesRef  = useRef(0);
  const sessionId   = useRef(`rt_${Date.now()}`);
  const activeRef   = useRef(false);   // track inside callbacks without stale closure

  const [active,      setActive]     = useState(false);
  const [connState,   setConnState]  = useState<ConnState>("idle");
  const [metrics,     setMetrics]    = useState<Metrics | null>(null);
  const [error,       setError]      = useState<string | null>(null);
  const [frameCount,  setFrameCount] = useState(0);
  const [closeInfo,   setCloseInfo]  = useState<string | null>(null);

  // ── Attach stream to video element after it mounts ────────────────────────
  useEffect(() => {
    if (active && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current;
    }
  }, [active]);

  // ── Send one JPEG frame ───────────────────────────────────────────────────
  const sendFrame = useCallback(() => {
    const ws     = wsRef.current;
    const video  = videoRef.current;
    const canvas = canvasRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN || !video || !canvas) return;
    if (video.readyState < 2) return;   // video not ready yet

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    canvas.width  = 320;
    canvas.height = 240;
    ctx.drawImage(video, 0, 0, 320, 240);
    const b64 = canvas.toDataURL("image/jpeg", 0.6).split(",")[1];
    ws.send(JSON.stringify({ type: "frame", data: b64 }));
    setFrameCount(n => n + 1);
  }, []);

  // ── Web Speech API ────────────────────────────────────────────────────────
  const startSpeech = useCallback(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { console.warn("Web Speech API not available in this browser"); return; }

    const rec = new SR() as SpeechRecognition;
    rec.continuous     = true;
    rec.interimResults = true;
    rec.lang           = "en-US";

    let final = "";
    rec.onresult = (e: SpeechRecognitionEvent) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) final += t + " ";
        else interim = t;
      }
      wsRef.current?.send(JSON.stringify({ type: "transcript", text: (final + interim).trim() }));
    };
    rec.onerror = (e: SpeechRecognitionErrorEvent) => {
      if (e.error !== "no-speech") console.warn("Speech error:", e.error);
    };
    rec.onend = () => {
      if (wsRef.current?.readyState === WebSocket.OPEN) rec.start();
    };
    rec.start();
    speechRef.current = rec;
  }, []);

  // ── Open WebSocket (called on start + each reconnect) ─────────────────────
  const openWS = useCallback(() => {
    if (!activeRef.current) return;

    const ws = new WebSocket(`${WS_BASE}/${sessionId.current}`);
    wsRef.current = ws;
    setConnState("connecting");
    console.log("[WS] Connecting to", `${WS_BASE}/${sessionId.current}`);

    ws.onopen = () => {
      console.log("[WS] Connected");
      retriesRef.current = 0;
      setConnState("connected");
      setError(null);
      frameTimer.current = setInterval(sendFrame, 1000 / FPS);
      startSpeech();
      // keepalive ping every 20s
      const ping = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "ping" }));
        else clearInterval(ping);
      }, 20_000);
    };

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "metrics") setMetrics(msg.payload);
      } catch { /* ignore malformed */ }
    };

    ws.onerror = (e) => {
      console.error("[WS] Error event", e);
    };

    ws.onclose = (e) => {
      const info = `code=${e.code} reason=${e.reason || "none"} clean=${e.wasClean}`;
      console.log("[WS] Closed —", info);
      setCloseInfo(info);
      if (frameTimer.current) { clearInterval(frameTimer.current); frameTimer.current = null; }

      if (!activeRef.current) { setConnState("stopped"); return; }

      setConnState("reconnecting");
      if (retriesRef.current < MAX_RETRIES) {
        retriesRef.current++;
        console.log(`[WS] Reconnect ${retriesRef.current}/${MAX_RETRIES} in ${RECONNECT_MS}ms`);
        setTimeout(openWS, RECONNECT_MS);
      } else {
        setConnState("failed");
        setError(`WebSocket failed after ${MAX_RETRIES} attempts. Last close: ${info}`);
      }
    };
  }, [sendFrame, startSpeech]);

  // ── Start session ─────────────────────────────────────────────────────────
  const start = async () => {
    setError(null);
    setFrameCount(0);
    retriesRef.current = 0;
    sessionId.current  = `rt_${Date.now()}`;
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

  // ── Stop session ──────────────────────────────────────────────────────────
  const stop = () => {
    activeRef.current = false;
    if (frameTimer.current) { clearInterval(frameTimer.current); frameTimer.current = null; }
    if (speechRef.current)  { speechRef.current.stop(); speechRef.current = null; }
    if (wsRef.current)      { wsRef.current.close(1000, "user stopped"); wsRef.current = null; }
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    setActive(false);
    setConnState("stopped");
    setMetrics(null);
  };

  useEffect(() => () => stop(), []);

  const stateLabel: Record<ConnState, string> = {
    idle:         "● Idle",
    connecting:   "◌ Connecting…",
    connected:    "● LIVE",
    reconnecting: "◌ Reconnecting…",
    failed:       "✖ Connection Failed",
    stopped:      "■ Stopped",
  };
  const stateColor: Record<ConnState, string> = {
    idle: "#888", connecting: "#fd7e14", connected: "#28a745",
    reconnecting: "#fd7e14", failed: "#dc3545", stopped: "#888",
  };

  return (
    <main style={{ padding: "2rem", fontFamily: "sans-serif", maxWidth: 780 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "1.25rem" }}>
        <h1 style={{ fontSize: "1.1rem", margin: 0 }}>🎙 Real-Time Interview Coach</h1>
        <a href="/" style={{ fontSize: "0.85rem", color: "#457b9d" }}>← Offline Assessment</a>
      </div>

      {/* Controls */}
      <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
        <button onClick={start} disabled={active} style={active ? btnDisabled : btnStart}>
          ▶ Start Session
        </button>
        <button onClick={stop} disabled={!active} style={!active ? btnDisabled : btnStop}>
          ■ Stop Session
        </button>
        <span style={{ fontSize: "0.85rem", fontWeight: 700, color: stateColor[connState] }}>
          {stateLabel[connState]}
        </span>
        {connState === "connected" && (
          <span style={{ fontSize: "0.75rem", color: "#888" }}>
            {frameCount} frames sent
          </span>
        )}
      </div>

      {error && (
        <div style={{ marginTop: "0.75rem", background: "#fff3cd", border: "1px solid #ffc107", borderRadius: 6, padding: "0.75rem 1rem", fontSize: "0.9rem" }}>
          ⚠ {error}
          {closeInfo && <div style={{ marginTop: "0.3rem", fontSize: "0.75rem", color: "#888", fontFamily: "monospace" }}>{closeInfo}</div>}
          <div style={{ marginTop: "0.4rem", fontSize: "0.8rem", color: "#555" }}>
            Run: <code>uvicorn main:app --host 0.0.0.0 --port 8000 --reload</code>
          </div>
        </div>
      )}
      {closeInfo && connState === "reconnecting" && (
        <div style={{ marginTop: "0.5rem", fontSize: "0.75rem", color: "#888", fontFamily: "monospace" }}>Last close: {closeInfo}</div>
      )}

      {/* Video + hidden canvas */}
      {active && (
        <div style={{ marginTop: "1rem" }}>
          <video ref={videoRef} autoPlay playsInline muted width={480} height={360}
            style={{ borderRadius: 8, background: "#000", display: "block" }} />
        </div>
      )}
      <canvas ref={canvasRef} style={{ display: "none" }} />

      {/* Live dashboard */}
      {active && <RealtimeDashboard metrics={metrics} connected={connState === "connected"} />}

      {!active && connState === "idle" && (
        <p style={{ marginTop: "1.5rem", color: "#888", fontSize: "0.9rem" }}>
          Click <strong>Start Session</strong> to begin real-time coaching.
          Face detection, eye contact, and live transcript update continuously while you speak.
        </p>
      )}
    </main>
  );
}

const base: React.CSSProperties = { padding: "0.5rem 1.2rem", borderRadius: 6, border: "none", cursor: "pointer", fontWeight: 600, fontSize: "0.9rem" };
const btnStart:    React.CSSProperties = { ...base, background: "#28a745", color: "#fff" };
const btnStop:     React.CSSProperties = { ...base, background: "#dc3545", color: "#fff" };
const btnDisabled: React.CSSProperties = { ...base, background: "#eee", color: "#aaa", cursor: "not-allowed" };
