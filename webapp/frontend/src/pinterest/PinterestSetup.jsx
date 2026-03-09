import { useState, useEffect } from "react";
import { api } from "../api";

export default function PinterestSetup({ onStatusChange }) {
  const [status, setStatus] = useState(null);
  const [appId, setAppId] = useState("");
  const [appSecret, setAppSecret] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [creatingBoards, setCreatingBoards] = useState(false);
  const [boardResults, setBoardResults] = useState(null);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const fetchStatus = async () => {
    try {
      const data = await api.pinterestSetupStatus();
      setStatus(data);
      if (onStatusChange) onStatusChange(data);
    } catch (err) {
      setError("Failed to load setup status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Check for OAuth callback result in URL
    const params = new URLSearchParams(window.location.search);
    const setupResult = params.get("pinterest_setup");
    if (setupResult === "success") {
      setSuccessMsg("Pinterest connected successfully!");
      // Clean up URL
      const url = new URL(window.location);
      url.searchParams.delete("pinterest_setup");
      window.history.replaceState({}, "", url.toString());
    } else if (setupResult === "error") {
      setError("Pinterest authorization failed. Please try again.");
      const url = new URL(window.location);
      url.searchParams.delete("pinterest_setup");
      window.history.replaceState({}, "", url.toString());
    }

    fetchStatus();
  }, []);

  const handleConnect = async () => {
    if (!appId.trim() || !appSecret.trim()) {
      setError("Both App ID and App Secret are required");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      const data = await api.pinterestSaveCredentials(appId.trim(), appSecret.trim());
      if (data.authorize_url) {
        window.location.href = data.authorize_url;
      }
    } catch (err) {
      setError(err.message || "Failed to save credentials");
      setSaving(false);
    }
  };

  const handleCreateBoards = async () => {
    setError(null);
    setCreatingBoards(true);
    setBoardResults(null);
    try {
      const data = await api.pinterestCreateBoards();
      setBoardResults(data.boards);
      await fetchStatus();
    } catch (err) {
      setError(err.message || "Failed to create boards");
    } finally {
      setCreatingBoards(false);
    }
  };

  const handleRefreshToken = async () => {
    setError(null);
    try {
      await api.pinterestRefreshToken();
      setSuccessMsg("Token refreshed successfully");
      await fetchStatus();
    } catch (err) {
      setError(err.message || "Failed to refresh token");
    }
  };

  if (loading) {
    return <div className="loading">Loading setup status...</div>;
  }

  const isConnected = status?.is_connected;
  const hasCredentials = status?.has_app_credentials;
  const allBoardsCreated = status?.all_boards_created;
  const setupComplete = status?.setup_complete;

  return (
    <div className="pinterest-setup">
      {error && (
        <div className="setup-alert setup-alert--error">
          {error}
          <button className="setup-alert__close" onClick={() => setError(null)}>x</button>
        </div>
      )}
      {successMsg && (
        <div className="setup-alert setup-alert--success">
          {successMsg}
          <button className="setup-alert__close" onClick={() => setSuccessMsg(null)}>x</button>
        </div>
      )}

      {/* Step 1: App Credentials */}
      <div className={`setup-step ${isConnected ? "setup-step--complete" : ""}`}>
        <div className="setup-step__header">
          <span className="setup-step__icon">{isConnected ? "\u2713" : "1"}</span>
          <h3>Connect Pinterest Account</h3>
        </div>
        {isConnected ? (
          <div className="setup-step__body">
            <div className="connection-banner">
              <span className="connection-banner__status">Connected</span>
              <button className="btn--outline" onClick={handleRefreshToken}>
                Refresh Token
              </button>
            </div>
          </div>
        ) : (
          <div className="setup-step__body">
            <p className="setup-step__desc">
              Enter your Pinterest App ID and App Secret from the{" "}
              <a href="https://developers.pinterest.com/apps/" target="_blank" rel="noreferrer">
                Pinterest Developer Dashboard
              </a>.
            </p>
            <div className="setup-input-group">
              <label>App ID</label>
              <input
                type="text"
                value={appId}
                onChange={(e) => setAppId(e.target.value)}
                placeholder="Enter Pinterest App ID"
                disabled={saving}
              />
            </div>
            <div className="setup-input-group">
              <label>App Secret</label>
              <input
                type="password"
                value={appSecret}
                onChange={(e) => setAppSecret(e.target.value)}
                placeholder="Enter Pinterest App Secret"
                disabled={saving}
              />
            </div>
            <button
              className="btn--orange"
              onClick={handleConnect}
              disabled={saving || !appId.trim() || !appSecret.trim()}
            >
              {saving ? "Connecting..." : "Connect Pinterest"}
            </button>
          </div>
        )}
      </div>

      {/* Step 2: Create Boards */}
      {isConnected && (
        <div className={`setup-step ${allBoardsCreated ? "setup-step--complete" : ""}`}>
          <div className="setup-step__header">
            <span className="setup-step__icon">{allBoardsCreated ? "\u2713" : "2"}</span>
            <h3>Create Pinterest Boards</h3>
          </div>
          <div className="setup-step__body">
            <div className="board-list">
              {(boardResults || status?.boards || []).map((board) => {
                const created = board.created || board.status === "created" || board.status === "already_exists";
                return (
                  <div key={board.env_key || board.name} className={`board-item ${created ? "board-item--created" : ""}`}>
                    <span className="board-item__icon">{created ? "\u2713" : "\u25CB"}</span>
                    <span className="board-item__name">{board.name}</span>
                    {board.status && board.status !== "unknown" && (
                      <span className="board-item__status">{board.status}</span>
                    )}
                  </div>
                );
              })}
            </div>
            {!allBoardsCreated && (
              <button
                className="btn--orange"
                onClick={handleCreateBoards}
                disabled={creatingBoards}
                style={{ marginTop: 12 }}
              >
                {creatingBoards ? "Creating Boards..." : "Create Boards"}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Complete state */}
      {setupComplete && (
        <div className="setup-step setup-step--complete">
          <div className="setup-step__header">
            <span className="setup-step__icon">{"\u2713"}</span>
            <h3>Setup Complete</h3>
          </div>
          <div className="setup-step__body">
            <p className="setup-step__desc">
              Pinterest is connected and all boards are created. You can now generate, schedule, and post pins.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
