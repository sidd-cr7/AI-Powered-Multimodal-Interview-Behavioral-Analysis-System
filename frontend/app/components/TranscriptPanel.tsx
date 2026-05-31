"use client";

import { TranscriptResult } from "../types/analysis";

type Props = {
  result: TranscriptResult | null;
  loading: boolean;
  error: string | null;
  onFetch: () => void;
};

export default function TranscriptPanel({ result, loading, error, onFetch }: Props) {
  return (
    <section style={section}>
      <h2 style={heading}>🎙 Transcript Analysis</h2>

      <button style={btn} onClick={onFetch} disabled={loading}>
        {loading ? "Transcribing…" : "Generate Transcript"}
      </button>

      {error && <p style={{ color: "red", marginTop: "0.5rem" }}>{error}</p>}

      {result && (
        <>
          <div style={grid}>
            <Stat label="Word Count"    value={result.word_count} />
            <Stat label="Duration"      value={`${result.duration_seconds}s`} />
            <Stat label="Speaking Rate" value={`${result.speaking_rate_wpm} wpm`} />
            <Stat label="Confidence"    value={`${result.confidence_score}%`} color={qualityColor(result.transcript_quality)} />
            <Stat label="Quality"       value={result.transcript_quality.toUpperCase()} color={qualityColor(result.transcript_quality)} />
          </div>

          {result.status === "silent_audio" && (
            <p style={{ color: "orange", marginTop: "0.5rem" }}>⚠ Silent or no speech detected.</p>
          )}

          <div style={transcriptBox}>
            <strong>Transcript:</strong>
            <p style={{ marginTop: "0.4rem", lineHeight: 1.6 }}>{result.transcript}</p>
          </div>
        </>
      )}
    </section>
  );
}

function qualityColor(q: string) {
  return q === "excellent" ? "#28a745" : q === "good" ? "#5ba85b" : q === "fair" ? "#fd7e14" : "#dc3545";
}

function Stat({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div style={statCard}>
      <div style={{ fontSize: "0.75rem", color: "#666" }}>{label}</div>
      <div style={{ fontSize: "1.3rem", fontWeight: 700, color: color ?? "#111" }}>{value}</div>
    </div>
  );
}

const section: React.CSSProperties = { marginTop: "2rem", borderTop: "1px solid #eee", paddingTop: "1.5rem" };
const heading: React.CSSProperties = { fontSize: "1rem", marginBottom: "0.75rem" };
const btn: React.CSSProperties     = { padding: "0.45rem 1rem", borderRadius: 6, border: "1px solid #ccc", cursor: "pointer" };
const grid: React.CSSProperties    = { display: "flex", gap: "1rem", flexWrap: "wrap", margin: "1rem 0" };
const statCard: React.CSSProperties = { background: "#f9f9f9", border: "1px solid #e0e0e0", borderRadius: 8, padding: "0.75rem 1.25rem", minWidth: 120 };
const transcriptBox: React.CSSProperties = { background: "#f4f4f4", borderRadius: 8, padding: "1rem", fontSize: "0.95rem" };
