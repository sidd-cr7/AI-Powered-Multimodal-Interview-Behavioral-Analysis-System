"use client";

import { useState } from "react";
import { ReportResult, SessionSummary, CompareResult } from "../types/analysis";

type Props = { api: string; filename: string };

const ROLES = [
  { value: "software_engineer",  label: "Software Engineer" },
  { value: "ai_ml_engineer",     label: "AI/ML Engineer" },
  { value: "data_scientist",     label: "Data Scientist" },
  { value: "product_manager",    label: "Product Manager" },
  { value: "business_analyst",   label: "Business Analyst" },
];

const SCORE_KEYS: { key: keyof import("../types/analysis").ReportMetrics; label: string }[] = [
  { key: "overall_score",             label: "Overall" },
  { key: "communication_score",       label: "Communication" },
  { key: "eye_contact_percentage",    label: "Eye Contact" },
  { key: "voice_confidence_score",    label: "Voice" },
  { key: "interview_readiness_score", label: "Readiness" },
  { key: "professional_presence_score", label: "Presence" },
];

function scoreColor(v: number) {
  if (v >= 80) return "#2d6a4f";
  if (v >= 60) return "#457b9d";
  if (v >= 40) return "#fd7e14";
  return "#dc3545";
}

function ImprovementBadge({ value, label }: { value: number; label: string }) {
  const color = value > 0 ? "#2d6a4f" : value < 0 ? "#dc3545" : "#888";
  const sign  = value > 0 ? "+" : "";
  return (
    <div style={{ ...metricBox, borderTop: `3px solid ${color}` }}>
      <div style={{ fontSize: "0.7rem", color: "#888" }}>{label}</div>
      <div style={{ fontWeight: 800, fontSize: "1.2rem", color }}>{sign}{value}</div>
    </div>
  );
}

export default function ReportPanel({ api, filename }: Props) {
  const [role,           setRole]           = useState("software_engineer");
  const [loading,        setLoading]        = useState(false);
  const [error,          setError]          = useState<string | null>(null);
  const [report,         setReport]         = useState<ReportResult | null>(null);
  const [history,        setHistory]        = useState<SessionSummary[] | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [compareA,       setCompareA]       = useState("");
  const [compareB,       setCompareB]       = useState("");
  const [comparison,     setComparison]     = useState<CompareResult | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError,   setCompareError]   = useState<string | null>(null);

  const generateReport = async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${api}/report/generate/${filename}?role=${role}`, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setReport(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Report generation failed.");
    } finally {
      setLoading(false);
    }
  };

  const loadHistory = async () => {
    setHistoryLoading(true);
    try {
      const res  = await fetch(`${api}/history/list`);
      const data = await res.json();
      setHistory(data.sessions);
    } finally {
      setHistoryLoading(false);
    }
  };

  const compareSessions = async () => {
    if (!compareA || !compareB) return;
    setCompareLoading(true); setCompareError(null);
    try {
      const res = await fetch(`${api}/history/compare?session_a=${compareA}&session_b=${compareB}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setComparison(await res.json());
    } catch (e) {
      setCompareError(e instanceof Error ? e.message : "Comparison failed.");
    } finally {
      setCompareLoading(false);
    }
  };

  return (
    <section style={section}>
      <h2 style={heading}>📄 Professional Assessment Report</h2>

      {/* Generate */}
      <div style={{ display: "flex", gap: "0.75rem", alignItems: "center", flexWrap: "wrap" }}>
        <select value={role} onChange={e => setRole(e.target.value)} style={select}>
          {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
        </select>
        <button onClick={generateReport} disabled={loading} style={loading ? btnDisabled : btnPrimary}>
          {loading ? "Generating…" : "📊 Generate Report"}
        </button>
        <button onClick={loadHistory} disabled={historyLoading} style={btnSecondary}>
          {historyLoading ? "Loading…" : "📁 Session History"}
        </button>
      </div>

      {error && <p style={errStyle}>{error}</p>}

      {/* Report result */}
      {report && (
        <div style={{ marginTop: "1.25rem" }}>
          <div style={card}>
            <p style={{ fontWeight: 700, marginBottom: "0.5rem" }}>
              Session: <code>{report.session_id}</code> &nbsp;|&nbsp;
              Benchmark Level: <strong>{report.benchmark.candidate_level}</strong> &nbsp;|&nbsp;
              Avg Score: {report.benchmark.candidate_avg}
            </p>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              <a href={`${api}${report.report_url}`} target="_blank" rel="noreferrer" style={linkBtn}>⬇ Download PDF</a>
              <a href={`${api}${report.csv_url}`}    target="_blank" rel="noreferrer" style={linkBtn}>⬇ Export CSV</a>
              <a href={`${api}${report.json_url}`}   target="_blank" rel="noreferrer" style={linkBtn}>⬇ Export JSON</a>
            </div>
          </div>

          {/* Score cards */}
          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", marginTop: "0.75rem" }}>
            {SCORE_KEYS.map(({ key, label }) => {
              const val = Math.round(Number(report.metrics[key]) || 0);
              return (
                <div key={key} style={{ ...metricBox, borderTop: `3px solid ${scoreColor(val)}` }}>
                  <div style={{ fontSize: "0.7rem", color: "#888" }}>{label}</div>
                  <div style={{ fontWeight: 800, fontSize: "1.3rem", color: scoreColor(val) }}>{val}</div>
                </div>
              );
            })}
          </div>

          {/* Benchmark comparison table */}
          <div style={{ ...card, marginTop: "0.75rem" }}>
            <p style={{ fontWeight: 700, marginBottom: "0.5rem", fontSize: "0.9rem" }}>Benchmark Comparison</p>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
              <thead>
                <tr style={{ background: "#1a1a2e", color: "#fff" }}>
                  {["Metric", "You", "Beginner", "Intermediate", "Advanced", "vs Advanced"].map(h => (
                    <th key={h} style={th}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(report.benchmark.benchmark_comparison).map(([metric, vals], i) => (
                  <tr key={metric} style={{ background: i % 2 === 0 ? "#f8f9fa" : "#fff" }}>
                    <td style={td}>{metric.replace(/_/g, " ")}</td>
                    <td style={{ ...td, fontWeight: 700 }}>{vals.candidate}</td>
                    <td style={td}>{vals.beginner}</td>
                    <td style={td}>{vals.intermediate}</td>
                    <td style={td}>{vals.advanced}</td>
                    <td style={{ ...td, color: vals.vs_advanced >= 0 ? "#2d6a4f" : "#dc3545", fontWeight: 600 }}>
                      {vals.vs_advanced >= 0 ? "+" : ""}{vals.vs_advanced}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Session History */}
      {history && history.length > 0 && (
        <div style={{ marginTop: "1.5rem" }}>
          <p style={{ fontWeight: 700, marginBottom: "0.5rem" }}>Session History</p>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
            <thead>
              <tr style={{ background: "#1a1a2e", color: "#fff" }}>
                {["Session", "Date", "Role", "Score", "Rating", "Readiness", "PDF"].map(h => (
                  <th key={h} style={th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {history.map((s, i) => (
                <tr key={s.session_id} style={{ background: i % 2 === 0 ? "#f8f9fa" : "#fff" }}>
                  <td style={td}><code>{s.session_id}</code></td>
                  <td style={td}>{new Date(s.timestamp).toLocaleDateString()}</td>
                  <td style={td}>{s.role.replace(/_/g, " ")}</td>
                  <td style={{ ...td, fontWeight: 700, color: scoreColor(s.overall_score) }}>{s.overall_score}</td>
                  <td style={td}>{s.rating}</td>
                  <td style={td}>{s.readiness_level}</td>
                  <td style={td}>
                    <a href={`${api}/report/download/${s.session_id}`} target="_blank" rel="noreferrer" style={{ color: "#457b9d", fontWeight: 600 }}>PDF</a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Compare sessions */}
          <div style={{ ...card, marginTop: "1rem" }}>
            <p style={{ fontWeight: 700, marginBottom: "0.5rem", fontSize: "0.9rem" }}>🔀 Compare Sessions</p>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", alignItems: "center" }}>
              <select value={compareA} onChange={e => setCompareA(e.target.value)} style={select}>
                <option value="">Session A</option>
                {history.map(s => <option key={s.session_id} value={s.session_id}>{s.session_id} — {s.overall_score}</option>)}
              </select>
              <span style={{ color: "#888" }}>vs</span>
              <select value={compareB} onChange={e => setCompareB(e.target.value)} style={select}>
                <option value="">Session B</option>
                {history.map(s => <option key={s.session_id} value={s.session_id}>{s.session_id} — {s.overall_score}</option>)}
              </select>
              <button onClick={compareSessions} disabled={!compareA || !compareB || compareLoading} style={compareA && compareB ? btnPrimary : btnDisabled}>
                {compareLoading ? "Comparing…" : "Compare"}
              </button>
            </div>

            {compareError && <p style={errStyle}>{compareError}</p>}

            {comparison && (
              <div style={{ marginTop: "0.75rem" }}>
                <p style={{ fontSize: "0.85rem", color: "#555", marginBottom: "0.5rem" }}>{comparison.summary}</p>
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  <ImprovementBadge value={comparison.overall_improvement}          label="Overall" />
                  <ImprovementBadge value={comparison.communication_improvement}    label="Communication" />
                  <ImprovementBadge value={comparison.eye_contact_improvement}      label="Eye Contact" />
                  <ImprovementBadge value={comparison.voice_confidence_improvement} label="Voice" />
                  <ImprovementBadge value={comparison.readiness_improvement}        label="Readiness" />
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {history && history.length === 0 && (
        <p style={{ color: "#888", fontSize: "0.85rem", marginTop: "0.75rem" }}>No previous sessions found.</p>
      )}
    </section>
  );
}

const section:     React.CSSProperties = { marginTop: "2rem", borderTop: "1px solid #eee", paddingTop: "1.5rem" };
const heading:     React.CSSProperties = { fontSize: "1rem", marginBottom: "0.75rem" };
const select:      React.CSSProperties = { padding: "0.45rem 0.75rem", borderRadius: 6, border: "1px solid #ccc", fontSize: "0.9rem" };
const btnPrimary:  React.CSSProperties = { padding: "0.5rem 1.2rem", borderRadius: 6, border: "none", background: "#1a1a2e", color: "#fff", cursor: "pointer", fontWeight: 600 };
const btnSecondary:React.CSSProperties = { padding: "0.5rem 1.2rem", borderRadius: 6, border: "1px solid #ccc", background: "#fff", cursor: "pointer", fontWeight: 600 };
const btnDisabled: React.CSSProperties = { ...btnPrimary, background: "#ccc", cursor: "not-allowed" };
const linkBtn:     React.CSSProperties = { padding: "0.4rem 0.9rem", borderRadius: 6, border: "1px solid #457b9d", color: "#457b9d", textDecoration: "none", fontSize: "0.85rem", fontWeight: 600 };
const card:        React.CSSProperties = { background: "#f8f9fa", border: "1px solid #e0e0e0", borderRadius: 8, padding: "1rem" };
const metricBox:   React.CSSProperties = { background: "#fff", border: "1px solid #e0e0e0", borderRadius: 6, padding: "0.5rem 0.75rem", minWidth: 90, textAlign: "center" as const };
const th:          React.CSSProperties = { padding: "0.5rem 0.75rem", textAlign: "left" as const, fontWeight: 600, fontSize: "0.8rem" };
const td:          React.CSSProperties = { padding: "0.4rem 0.75rem", borderBottom: "1px solid #eee" };
const errStyle:    React.CSSProperties = { color: "red", marginTop: "0.5rem", fontSize: "0.9rem" };
