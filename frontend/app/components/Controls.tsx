"use client";

import { UploadStatus } from "../types/analysis";

type Props = {
  active: boolean;
  recording: boolean;
  uploadStatus: UploadStatus;
  onStartCamera: () => void;
  onStartRecording: () => void;
  onStopRecording: () => void;
};

const btn: React.CSSProperties = {
  padding: "0.5rem 1.1rem",
  borderRadius: 6,
  border: "1px solid #ccc",
  cursor: "pointer",
  fontWeight: 500,
};

export default function Controls({
  active,
  recording,
  uploadStatus,
  onStartCamera,
  onStartRecording,
  onStopRecording,
}: Props) {
  return (
    <div>
      <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
        <button style={btn} onClick={onStartCamera} disabled={active}>
          {active ? "📷 Camera On" : "Start Interview"}
        </button>
        {active && (
          <>
            <button
              style={{ ...btn, background: recording ? "#eee" : "#d4edda" }}
              onClick={onStartRecording}
              disabled={recording}
            >
              ● Start Recording
            </button>
            <button
              style={{ ...btn, background: !recording ? "#eee" : "#f8d7da" }}
              onClick={onStopRecording}
              disabled={!recording}
            >
              ■ Stop Recording
            </button>
          </>
        )}
      </div>

      <div style={{ marginTop: "0.5rem", fontSize: "0.9rem" }}>
        {recording && <span style={{ color: "orange" }}>● Recording…</span>}
        {uploadStatus === "uploading" && <span style={{ color: "#555" }}>⏫ Uploading…</span>}
        {uploadStatus === "success"   && <span style={{ color: "green" }}>✔ Upload complete</span>}
        {uploadStatus === "error"     && <span style={{ color: "red"   }}>✖ Upload failed</span>}
      </div>
    </div>
  );
}
