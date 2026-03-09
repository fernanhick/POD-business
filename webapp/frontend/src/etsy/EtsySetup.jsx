import { useState, useEffect } from "react";
import { api } from "../api";

export default function EtsySetup() {
  const [status, setStatus] = useState(null);
  const [apiKey, setApiKey] = useState("");
  const [sharedSecret, setSharedSecret] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [creatingSections, setCreatingSections] = useState(false);
  const [sectionResults, setSectionResults] = useState(null);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const fetchStatus = async () => {
    try {
      const data = await api.etsySetupStatus();
      setStatus(data);
    } catch (err) {
      setError("Failed to load Etsy setup status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const setupResult = params.get("etsy_setup");
    if (setupResult === "success") {
      setSuccessMsg("Etsy connected successfully!");
      const url = new URL(window.location);
      url.searchParams.delete("etsy_setup");
      window.history.replaceState({}, "", url.toString());
    } else if (setupResult === "error") {
      setError("Etsy authorization failed. Please try again.");
      const url = new URL(window.location);
      url.searchParams.delete("etsy_setup");
      window.history.replaceState({}, "", url.toString());
    }
    fetchStatus();
  }, []);

  const handleConnect = async () => {
    if (!apiKey.trim() || !sharedSecret.trim()) {
      setError("Both API Key and Shared Secret are required");
      return;
    }
    setError(null);
    setSaving(true);
    try {
      const data = await api.etsySaveCredentials(apiKey.trim(), sharedSecret.trim());
      if (data.authorize_url) {
        window.location.href = data.authorize_url;
      }
    } catch (err) {
      setError(err.message || "Failed to save credentials");
      setSaving(false);
    }
  };

  const handleCreateSections = async () => {
    setError(null);
    setCreatingSections(true);
    setSectionResults(null);
    try {
      const data = await api.etsyCreateSections();
      setSectionResults(data.sections);
      await fetchStatus();
    } catch (err) {
      setError(err.message || "Failed to create sections");
    } finally {
      setCreatingSections(false);
    }
  };

  const handleRefreshToken = async () => {
    setError(null);
    try {
      await api.etsyRefreshToken();
      setSuccessMsg("Token refreshed successfully");
      await fetchStatus();
    } catch (err) {
      setError(err.message || "Failed to refresh token");
    }
  };

  if (loading) {
    return <div className="loading">Loading Etsy setup status...</div>;
  }

  const isConnected = status?.is_connected;
  const hasCredentials = status?.has_app_credentials;
  const allSectionsCreated = status?.all_sections_created;
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

      {/* Step 1: Credentials */}
      <div className={`setup-step ${isConnected ? "setup-step--complete" : ""}`}>
        <div className="setup-step__header">
          <span className="setup-step__icon">{isConnected ? "\u2713" : "1"}</span>
          <h3>Connect Etsy Account</h3>
        </div>
        {isConnected ? (
          <div className="setup-step__body">
            <div className="connection-banner">
              <span className="connection-banner__status">
                Connected{status?.shop_name ? ` — ${status.shop_name}` : ""}
              </span>
              <button className="btn--outline" onClick={handleRefreshToken}>
                Refresh Token
              </button>
            </div>
          </div>
        ) : (
          <div className="setup-step__body">
            <p className="setup-step__desc">
              Enter your Etsy API Keystring and Shared Secret from the{" "}
              <a href="https://www.etsy.com/developers/your-apps" target="_blank" rel="noreferrer">
                Etsy Developer Dashboard
              </a>.
              {!hasCredentials && " Your API key must be approved by Etsy before connecting."}
            </p>
            <div className="setup-input-group">
              <label>API Keystring</label>
              <input
                type="text"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter Etsy API Keystring"
                disabled={saving}
              />
            </div>
            <div className="setup-input-group">
              <label>Shared Secret</label>
              <input
                type="password"
                value={sharedSecret}
                onChange={(e) => setSharedSecret(e.target.value)}
                placeholder="Enter Etsy Shared Secret"
                disabled={saving}
              />
            </div>
            <button
              className="btn--orange"
              onClick={handleConnect}
              disabled={saving || !apiKey.trim() || !sharedSecret.trim()}
            >
              {saving ? "Connecting..." : "Connect Etsy"}
            </button>
          </div>
        )}
      </div>

      {/* Step 2: Create Sections */}
      {isConnected && (
        <div className={`setup-step ${allSectionsCreated ? "setup-step--complete" : ""}`}>
          <div className="setup-step__header">
            <span className="setup-step__icon">{allSectionsCreated ? "\u2713" : "2"}</span>
            <h3>Shop Sections</h3>
          </div>
          <div className="setup-step__body">
            <p className="setup-step__desc">
              Sections organize your listings on Etsy. New uploads will be auto-assigned to the correct section.
            </p>
            <div className="board-list">
              {(sectionResults || status?.sections || []).map((section) => {
                const created = section.created || section.status === "created" || section.status === "already_exists";
                return (
                  <div key={section.name} className={`board-item ${created ? "board-item--created" : ""}`}>
                    <span className="board-item__icon">{created ? "\u2713" : "\u25CB"}</span>
                    <span className="board-item__name">{section.name}</span>
                    {section.status && section.status !== "unknown" && (
                      <span className="board-item__status">{section.status}</span>
                    )}
                  </div>
                );
              })}
            </div>
            {!allSectionsCreated && (
              <button
                className="btn--orange"
                onClick={handleCreateSections}
                disabled={creatingSections}
                style={{ marginTop: 12 }}
              >
                {creatingSections ? "Creating Sections..." : "Create Sections"}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Complete */}
      {setupComplete && (
        <div className="setup-step setup-step--complete">
          <div className="setup-step__header">
            <span className="setup-step__icon">{"\u2713"}</span>
            <h3>Etsy Setup Complete</h3>
          </div>
          <div className="setup-step__body">
            <p className="setup-step__desc">
              Etsy is connected and sections are ready. New uploads will be auto-assigned to the correct section.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
