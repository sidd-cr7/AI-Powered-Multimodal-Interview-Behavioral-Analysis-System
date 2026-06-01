"use client";

import { AssessmentResult } from "../types/analysis";

type Props = {
  result: AssessmentResult | null;
  loading: boolean;
  error: string | null;
  onFetch: () => void;
};

export default function AssessmentPanel({ result, loading, error, onFetch }: Props) {
  return (
    <section style={section}>
      <h2 style={heading}>🧠 Interview Assessment</h2>

      <button style={{ ...btn, background: loading ? "#eee" : "#1a1a2e", color: loading ? "#333" : "#fff" }}
        onClick={onFetch} disabled={loading}>
        {loading ? "Analyzing… (this may take a minute)" : "Generate Interview Assessment"}
      </button>

      {error && <p style={{ color: "red", marginTop: "0.75rem" }}>{error}</p>}

      {result && (
        <>
          {/* ── Score Overview ── */}
          <div style={{ marginTop: "1.5rem", borderTop: "2px solid #1a1a2e", paddingTop: "1rem" }}>
            <p style={{ fontWeight: 700, fontSize: "1rem", marginBottom: "0.75rem" }}>INTERVIEW ASSESSMENT</p>
            <div style={grid}>
              <ScoreCard label="Overall Score"        value={result.fusion_analysis.overall_score}        color="#1a1a2e" />
              <ScoreCard label="Professionalism"      value={result.fusion_analysis.professionalism_score} color="#2d6a4f" />
              <ScoreCard label="Engagement"           value={result.fusion_analysis.engagement_score}      color="#2d6a4f" />
              <ScoreCard label="Communication"        value={result.communication_analysis.communication_score} color="#457b9d" />
              <ScoreCard label="Confidence"           value={result.fusion_analysis.confidence_score}      color="#457b9d" />
              <ScoreCard label="Readiness"            value={result.feedback.interview_readiness_score}    color="#6d4c41" />
            </div>
            <p style={{ marginTop: "0.75rem", fontSize: "0.9rem" }}>
              <strong>Rating:</strong> {result.fusion_analysis.rating} &nbsp;|&nbsp;
              <strong>Level:</strong> {result.feedback.readiness_level} &nbsp;|&nbsp;
              <strong>Communication:</strong> {result.communication_analysis.communication_level}
            </p>
          </div>

          {/* ── Strengths ── */}
          <div style={block}>
            <p style={blockHeading}>✓ Strengths</p>
            <ul style={list}>
              {result.feedback.strengths.map((s, i) => (
                <li key={i} style={{ color: "#2d6a4f" }}>✓ {s}</li>
              ))}
            </ul>
          </div>

          {/* ── Improvements ── */}
          <div style={block}>
            <p style={blockHeading}>• Areas for Improvement</p>
            <ul style={list}>
              {result.feedback.improvements.map((s, i) => (
                <li key={i}>• {s}</li>
              ))}
            </ul>
          </div>

          {/* ── Coaching Tips ── */}
          <div style={block}>
            <p style={blockHeading}>💡 Coaching Recommendations</p>
            <ul style={list}>
              {result.feedback.coaching_tips.map((s, i) => (
                <li key={i}>• {s}</li>
              ))}
            </ul>
          </div>

          {/* ── HR Feedback ── */}
          <div style={{ ...block, background: "#f0f4ff", borderLeft: "4px solid #457b9d" }}>
            <p style={blockHeading}>🧑‍💼 HR Feedback</p>
            <p style={{ fontSize: "0.95rem", lineHeight: 1.6, fontStyle: "italic" }}>
              "{result.feedback.hr_feedback}"
            </p>
          </div>

          {/* ── Transcript Stats ── */}
          <div style={block}>
            <p style={blockHeading}>📊 Transcript Stats</p>
            <div style={grid}>
              <MiniStat label="Words"        value={result.transcript_analysis.word_count} />
              <MiniStat label="Sentences"    value={result.transcript_analysis.sentence_count} />
              <MiniStat label="WPM"          value={result.transcript_analysis.speaking_rate_wpm} />
              <MiniStat label="Fillers"      value={result.transcript_analysis.filler_word_count} />
              <MiniStat label="Vocab Div."   value={result.transcript_analysis.vocabulary_diversity} />
              <MiniStat label="Eye Contact"  value={`${result.eye_contact_analysis.eye_contact_percentage}%`} />
              <MiniStat label="Face Present" value={`${result.face_analysis.face_presence_percentage}%`} />
            </div>
          </div>
        </>
      )}
    </section>
  );
}

function ScoreCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ background: color, color: "#fff", borderRadius: 10, padding: "0.75rem 1rem", minWidth: 110, textAlign: "center" }}>
      <div style={{ fontSize: "0.7rem", opacity: 0.85, marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: "1.6rem", fontWeight: 800 }}>{value}</div>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ background: "#f9f9f9", border: "1px solid #e0e0e0", borderRadius: 8, padding: "0.6rem 1rem", minWidth: 100 }}>
      <div style={{ fontSize: "0.7rem", color: "#666" }}>{label}</div>
      <div style={{ fontSize: "1.1rem", fontWeight: 700 }}>{value}</div>
    </div>
  );
}

const section: React.CSSProperties    = { marginTop: "2rem", borderTop: "1px solid #eee", paddingTop: "1.5rem" };
const heading: React.CSSProperties    = { fontSize: "1rem", marginBottom: "0.75rem" };
const btn: React.CSSProperties        = { padding: "0.6rem 1.4rem", borderRadius: 6, border: "none", cursor: "pointer", fontWeight: 600, fontSize: "0.95rem" };
const grid: React.CSSProperties       = { display: "flex", gap: "0.75rem", flexWrap: "wrap" };
const block: React.CSSProperties      = { marginTop: "1.25rem", background: "#fafafa", borderRadius: 8, padding: "1rem" };
const blockHeading: React.CSSProperties = { fontWeight: 700, fontSize: "0.9rem", marginBottom: "0.5rem" };
const list: React.CSSProperties       = { margin: 0, paddingLeft: "0.5rem", listStyle: "none", display: "flex", flexDirection: "column", gap: "0.3rem", fontSize: "0.9rem" };
