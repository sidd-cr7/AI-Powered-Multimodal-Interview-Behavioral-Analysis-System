"use client";

import { EyeResult } from "../types/analysis";

type Props = {
  result: EyeResult | null;
  loading: boolean;
  onFetch: () => void;
};

const STABILITY_COLOR: Record<string, string> = {
  good: "#28a745",
  moderate: "#fd7e14",
  poor: "#dc3545",
};

export default function EyeContactPanel({ result, loading, onFetch }: Props) {
  return (
    <section style={section}>
      <h2 style={heading}>👁 Eye Contact Analysis</h2>

      <button style={btn} onClick={onFetch} disabled={loading}>
        {loading ? "Analyzing…" : "Run Eye Contact Analysis"}
      </button>

      {result && (
        <>
          {/* Summary stats */}
          <div style={grid}>
            <Stat label="Eye Contact"       value={`${result.eye_contact_percentage}%`} />
            <Stat label="Looking-Away Events" value={result.looking_away_events} />
            <Stat
              label="Gaze Stability"
              value={result.gaze_stability.toUpperCase()}
              color={STABILITY_COLOR[result.gaze_stability]}
            />
            <Stat label="Frames Processed" value={result.frames_processed} />
          </div>

          {/* Gaze distribution bar chart */}
          <div style={{ marginTop: "1.25rem" }}>
            <strong style={{ fontSize: "0.85rem" }}>Gaze Distribution</strong>
            <div style={{ marginTop: "0.5rem", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
              {Object.entries(result.gaze_distribution).map(([dir, pct]) => (
                <GazeBar key={dir} label={dir} pct={pct} />
              ))}
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function Stat({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div style={statCard}>
      <div style={{ fontSize: "0.75rem", color: "#666" }}>{label}</div>
      <div style={{ fontSize: "1.3rem", fontWeight: 700, color: color ?? "#111" }}>{value}</div>
    </div>
  );
}

function GazeBar({ label, pct }: { label: string; pct: number }) {
  const colors: Record<string, string> = { center: "#28a745", left: "#fd7e14", right: "#fd7e14", down: "#dc3545" };
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
      <span style={{ width: 60, fontSize: "0.8rem", textTransform: "capitalize" }}>{label}</span>
      <div style={{ flex: 1, background: "#e9ecef", borderRadius: 4, height: 14 }}>
        <div style={{ width: `${pct}%`, background: colors[label] ?? "#6c757d", height: "100%", borderRadius: 4, transition: "width 0.4s" }} />
      </div>
      <span style={{ width: 40, fontSize: "0.8rem", textAlign: "right" }}>{pct}%</span>
    </div>
  );
}

const section: React.CSSProperties  = { marginTop: "2rem", borderTop: "1px solid #eee", paddingTop: "1.5rem" };
const heading: React.CSSProperties  = { fontSize: "1rem", marginBottom: "0.75rem" };
const btn: React.CSSProperties      = { padding: "0.45rem 1rem", borderRadius: 6, border: "1px solid #ccc", cursor: "pointer" };
const grid: React.CSSProperties     = { display: "flex", gap: "1rem", flexWrap: "wrap", marginTop: "1rem" };
const statCard: React.CSSProperties = { background: "#f9f9f9", border: "1px solid #e0e0e0", borderRadius: 8, padding: "0.75rem 1.25rem", minWidth: 140 };
