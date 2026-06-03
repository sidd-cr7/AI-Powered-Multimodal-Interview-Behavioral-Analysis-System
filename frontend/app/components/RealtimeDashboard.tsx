"use client";

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
  frames_received?:       number;
  frames_processed?:      number;
};

type Props = { metrics: Metrics | null; connected: boolean };

const GAZE_COLOR: Record<string, string> = {
  CENTER:  "#28a745",
  LEFT:    "#fd7e14",
  RIGHT:   "#fd7e14",
  DOWN:    "#dc3545",
  UNKNOWN: "#aaa",
};

export default function RealtimeDashboard({ metrics, connected }: Props) {
  const m = metrics;

  return (
    <div style={{ marginTop: "1.5rem" }}>
      {/* Status bar */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1rem" }}>
        <span style={{
          width: 10, height: 10, borderRadius: "50%",
          background: connected ? "#28a745" : "#dc3545",
          display: "inline-block",
        }} />
        <span style={{ fontSize: "0.85rem", color: connected ? "#28a745" : "#dc3545", fontWeight: 600 }}>
          {connected ? "LIVE" : "DISCONNECTED"}
        </span>
        {m && (
          <span style={{ marginLeft: "auto", fontSize: "0.85rem", color: "#555", fontFamily: "monospace" }}>
            ⏱ {m.session_duration}
          </span>
        )}
      </div>

      {/* Metric cards grid */}
      <div style={grid}>
        <Card label="Face Detected"
          value={m ? (m.face_detected ? "YES ✔" : "NO ✖") : "—"}
          color={m ? (m.face_detected ? "#28a745" : "#dc3545") : "#aaa"} />
        <Card label="Faces" value={m ? String(m.face_count) : "—"} />
        <Card label="Current Gaze"
          value={m ? m.current_gaze : "—"}
          color={m ? (GAZE_COLOR[m.current_gaze] ?? "#aaa") : "#aaa"} />
        <Card label="Gaze Conf."
          value={m ? `${Math.round(m.gaze_confidence * 100)}%` : "—"}
          color={m && m.gaze_confidence >= 0.7 ? "#28a745" : "#fd7e14"} />
        <Card label="Eye Contact" value={m ? `${m.eye_contact_percentage}%` : "—"}
          color={m && m.eye_contact_percentage >= 70 ? "#28a745" : "#fd7e14"} />
        <Card label="Words Spoken" value={m ? String(m.words_spoken) : "—"} />
        <Card label="Current WPM"  value={m ? String(m.current_wpm)  : "—"}
          color={m && m.current_wpm >= 120 && m.current_wpm <= 170 ? "#28a745" : "#fd7e14"} />
        <Card label="Filler Words" value={m ? String(m.filler_words) : "—"}
          color={m && m.filler_words === 0 ? "#28a745" : m && m.filler_words > 5 ? "#dc3545" : "#fd7e14"} />
      </div>

      {/* Head pose */}
      {m?.head_orientation && (
        <div style={{ marginTop: "0.5rem", fontSize: "0.75rem", color: "#888", fontFamily: "monospace" }}>
          Head — yaw: {m.head_orientation.yaw}° &nbsp; pitch: {m.head_orientation.pitch}° &nbsp; roll: {m.head_orientation.roll}°
        </div>
      )}

      {/* Diagnostics */}
      {m && (m.frames_received !== undefined) && (
        <div style={{ marginTop: "0.5rem", fontSize: "0.75rem", color: "#888", fontFamily: "monospace" }}>
          frames rx: {m.frames_received} | processed: {m.frames_processed}
        </div>
      )}

      {/* Live transcript */}
      <div style={transcriptBox}>
        <p style={{ fontSize: "0.75rem", color: "#888", marginBottom: "0.4rem", fontWeight: 600 }}>
          LIVE TRANSCRIPT
        </p>
        <p style={{ fontSize: "0.9rem", lineHeight: 1.6, minHeight: 48, color: m?.transcript ? "#111" : "#bbb" }}>
          {m?.transcript || "Start speaking — transcript will appear here…"}
        </p>
      </div>
    </div>
  );
}

function Card({ label, value, color = "#111" }: { label: string; value: string; color?: string }) {
  return (
    <div style={card}>
      <div style={{ fontSize: "0.7rem", color: "#888", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>
        {label}
      </div>
      <div style={{ fontSize: "1.4rem", fontWeight: 800, color }}>{value}</div>
    </div>
  );
}

const grid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))",
  gap: "0.75rem",
};
const card: React.CSSProperties = {
  background: "#f9f9f9",
  border: "1px solid #e0e0e0",
  borderRadius: 10,
  padding: "0.75rem 1rem",
};
const transcriptBox: React.CSSProperties = {
  marginTop: "1rem",
  background: "#f4f4f4",
  borderRadius: 10,
  padding: "1rem",
};
