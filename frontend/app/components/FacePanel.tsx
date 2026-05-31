"use client";

import { FaceResult } from "../types/analysis";

type Props = {
  result: FaceResult | null;
  loading: boolean;
  onFetch: () => void;
};

export default function FacePanel({ result, loading, onFetch }: Props) {
  return (
    <section style={section}>
      <h2 style={heading}>👤 Face Detection</h2>

      <button style={btn} onClick={onFetch} disabled={loading}>
        {loading ? "Analyzing…" : "Run Face Detection"}
      </button>

      {result && (
        <div style={grid}>
          <Stat label="Face Detected"    value={result.face_detected ? "Yes ✔" : "No ✖"} />
          <Stat label="Max Faces"        value={result.face_count} />
          <Stat label="Frames Processed" value={result.frames_processed} />
          <Stat label="Face Presence"    value={`${result.face_presence_percentage}%`} />
        </div>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={statCard}>
      <div style={{ fontSize: "0.75rem", color: "#666" }}>{label}</div>
      <div style={{ fontSize: "1.3rem", fontWeight: 700 }}>{value}</div>
    </div>
  );
}

const section: React.CSSProperties  = { marginTop: "2rem", borderTop: "1px solid #eee", paddingTop: "1.5rem" };
const heading: React.CSSProperties  = { fontSize: "1rem", marginBottom: "0.75rem" };
const btn: React.CSSProperties      = { padding: "0.45rem 1rem", borderRadius: 6, border: "1px solid #ccc", cursor: "pointer" };
const grid: React.CSSProperties     = { display: "flex", gap: "1rem", flexWrap: "wrap", marginTop: "1rem" };
const statCard: React.CSSProperties = { background: "#f9f9f9", border: "1px solid #e0e0e0", borderRadius: 8, padding: "0.75rem 1.25rem", minWidth: 140 };
