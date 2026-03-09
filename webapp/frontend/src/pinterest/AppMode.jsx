import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

export default function AppMode() {
  const [phase, setPhase] = useState(null);
  const [toggling, setToggling] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(() => {
    api.pinterestGetAppPhase().then(setPhase).catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleToggle = useCallback(async () => {
    if (!phase) return;
    const newPhase = phase.phase === "pre_launch" ? "launched" : "pre_launch";
    setToggling(true);
    setError(null);
    try {
      await api.pinterestSetAppPhase(newPhase);
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setToggling(false);
    }
  }, [phase, load]);

  const handleGenerateBurst = useCallback(async () => {
    setGenerating(true);
    setError(null);
    try {
      await api.pinterestGenerateBurst();
      load();
    } catch (e) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  }, [load]);

  if (!phase) return <div className="loading">Loading app phase...</div>;

  const burstPercent =
    phase.burst_total > 0
      ? Math.round((phase.burst_released / phase.burst_total) * 100)
      : 0;

  return (
    <div className="app-mode">
      <div className="phase-banner">
        <div>
          <span className="phase-banner__label">App Phase: </span>
          <span className={`badge ${phase.phase}`}>
            {phase.phase === "pre_launch" ? "Pre-Launch" : "Launched"}
          </span>
        </div>
        <button
          className="btn--orange"
          disabled={toggling}
          onClick={handleToggle}
        >
          {toggling
            ? "Switching..."
            : phase.phase === "pre_launch"
            ? "Switch to Launched"
            : "Switch to Pre-Launch"}
        </button>
      </div>

      {error && <p style={{ color: "#f87171", fontSize: 13 }}>{error}</p>}

      <div>
        <h3 style={{ color: "#aaa", fontSize: 15, marginBottom: 8 }}>
          Configured URLs
        </h3>
        <table className="url-table">
          <tbody>
            <tr>
              <th>App Link</th>
              <td>{phase.app_link || <em style={{ color: "#666" }}>Not configured</em>}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="burst-section">
        <h3 style={{ margin: "0 0 8px", fontSize: 15, color: "#ddd" }}>
          Launch Burst Pins
        </h3>
        <p style={{ fontSize: 13, color: "#888", margin: "0 0 12px" }}>
          Generate app promo pins to be released in a burst when you switch to "Launched".
        </p>

        <div className="burst-progress">
          <div
            className="burst-progress__bar"
            style={{ width: `${burstPercent}%` }}
          />
        </div>
        <p style={{ fontSize: 12, color: "#888", margin: "4px 0 12px" }}>
          {phase.burst_released} / {phase.burst_total} released ({burstPercent}%)
        </p>

        <div className="toolbar">
          <button
            className="btn--orange"
            disabled={generating}
            onClick={handleGenerateBurst}
          >
            {generating ? "Generating..." : "Generate Burst Pins"}
          </button>
        </div>
      </div>
    </div>
  );
}
