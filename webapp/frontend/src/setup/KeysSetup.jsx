import { useEffect, useState } from "react";
import { api } from "../api";
import "../pinterest/pinterest.css";

const initialGeneration = {
  openai_api_key: "",
  ideogram_api_key: "",
  hf_api_token: "",
  leonardo_api_key: "",
};

export default function KeysSetup({ onSaved }) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState("");
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  const [printify, setPrintify] = useState({ token: "", shop_id: "" });
  const [printful, setPrintful] = useState({ api_key: "", store_id: "", api_base: "" });
  const [generation, setGeneration] = useState(initialGeneration);

  const fetchStatus = async () => {
    try {
      const data = await api.setupKeysStatus();
      setStatus(data?.groups || {});
    } catch {
      setError("Failed to load setup status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const afterSave = async (message) => {
    setSuccessMsg(message);
    await fetchStatus();
    if (onSaved) {
      await onSaved();
    }
  };

  const savePrintify = async () => {
    if (!printify.token.trim() || !printify.shop_id.trim()) {
      setError("Printify token and shop ID are required");
      return;
    }

    setError("");
    setSaving("printify");
    try {
      await api.saveSetupPrintifyKeys({
        token: printify.token,
        shop_id: printify.shop_id,
      });
      setPrintify({ token: "", shop_id: "" });
      await afterSave("Printify credentials saved");
    } catch (err) {
      setError(err.message || "Failed to save Printify credentials");
    } finally {
      setSaving("");
    }
  };

  const savePrintful = async () => {
    if (!printful.api_key.trim() || !printful.store_id.trim()) {
      setError("Printful API key and store ID are required");
      return;
    }

    setError("");
    setSaving("printful");
    try {
      await api.saveSetupPrintfulKeys({
        api_key: printful.api_key,
        store_id: printful.store_id,
        api_base: printful.api_base,
      });
      setPrintful({ api_key: "", store_id: "", api_base: "" });
      await afterSave("Printful credentials saved");
    } catch (err) {
      setError(err.message || "Failed to save Printful credentials");
    } finally {
      setSaving("");
    }
  };

  const saveGeneration = async () => {
    setError("");
    setSaving("generation");
    try {
      await api.saveSetupGenerationKeys(generation);
      setGeneration(initialGeneration);
      await afterSave("Generation API keys saved");
    } catch (err) {
      setError(err.message || "Failed to save generation keys");
    } finally {
      setSaving("");
    }
  };

  const group = (name) => status?.[name] || { configured: false, keys: {} };

  if (loading) {
    return <div className="loading">Loading setup keys...</div>;
  }

  return (
    <div className="pinterest-setup">
      {error && (
        <div className="setup-alert setup-alert--error">
          {error}
          <button className="setup-alert__close" onClick={() => setError("")}>x</button>
        </div>
      )}
      {successMsg && (
        <div className="setup-alert setup-alert--success">
          {successMsg}
          <button className="setup-alert__close" onClick={() => setSuccessMsg("")}>x</button>
        </div>
      )}

      <div className={`setup-step ${group("printify").configured ? "setup-step--complete" : ""}`}>
        <div className="setup-step__header">
          <span className="setup-step__icon">{group("printify").configured ? "✓" : "1"}</span>
          <h3>Printify (US)</h3>
        </div>
        <div className="setup-step__body">
          <p className="setup-step__desc">Saved values persist locally and are loaded automatically on restart.</p>
          <div className="setup-input-group">
            <label>Printify Token</label>
            <input
              type="password"
              value={printify.token}
              onChange={(e) => setPrintify((old) => ({ ...old, token: e.target.value }))}
              placeholder="Enter PRINTIFY_TOKEN"
              disabled={saving === "printify"}
            />
          </div>
          <div className="setup-input-group">
            <label>Printify Shop ID</label>
            <input
              type="text"
              value={printify.shop_id}
              onChange={(e) => setPrintify((old) => ({ ...old, shop_id: e.target.value }))}
              placeholder="Enter PRINTIFY_SHOP_ID"
              disabled={saving === "printify"}
            />
          </div>
          <p className="setup-step__desc">
            Current: {group("printify").keys?.PRINTIFY_TOKEN?.masked || "not set"} / {group("printify").keys?.PRINTIFY_SHOP_ID?.masked || "not set"}
          </p>
          <button className="btn--orange" onClick={savePrintify} disabled={saving === "printify"}>
            {saving === "printify" ? "Saving..." : "Save Printify"}
          </button>
        </div>
      </div>

      <div className={`setup-step ${group("printful").configured ? "setup-step--complete" : ""}`}>
        <div className="setup-step__header">
          <span className="setup-step__icon">{group("printful").configured ? "✓" : "2"}</span>
          <h3>Printful (EU)</h3>
        </div>
        <div className="setup-step__body">
          <div className="setup-input-group">
            <label>Printful API Key</label>
            <input
              type="password"
              value={printful.api_key}
              onChange={(e) => setPrintful((old) => ({ ...old, api_key: e.target.value }))}
              placeholder="Enter PRINTFUL_API_KEY"
              disabled={saving === "printful"}
            />
          </div>
          <div className="setup-input-group">
            <label>Printful Store ID</label>
            <input
              type="text"
              value={printful.store_id}
              onChange={(e) => setPrintful((old) => ({ ...old, store_id: e.target.value }))}
              placeholder="Enter PRINTFUL_STORE_ID"
              disabled={saving === "printful"}
            />
          </div>
          <div className="setup-input-group">
            <label>Printful API Base (optional)</label>
            <input
              type="text"
              value={printful.api_base}
              onChange={(e) => setPrintful((old) => ({ ...old, api_base: e.target.value }))}
              placeholder="https://api.printful.com"
              disabled={saving === "printful"}
            />
          </div>
          <p className="setup-step__desc">
            Current: {group("printful").keys?.PRINTFUL_API_KEY?.masked || "not set"} / {group("printful").keys?.PRINTFUL_STORE_ID?.masked || "not set"}
          </p>
          <button className="btn--orange" onClick={savePrintful} disabled={saving === "printful"}>
            {saving === "printful" ? "Saving..." : "Save Printful"}
          </button>
        </div>
      </div>

      <div className={`setup-step ${group("generation").configured ? "setup-step--complete" : ""}`}>
        <div className="setup-step__header">
          <span className="setup-step__icon">{group("generation").configured ? "✓" : "3"}</span>
          <h3>Generation APIs</h3>
        </div>
        <div className="setup-step__body">
          <p className="setup-step__desc">Set one or more render providers. Empty fields are ignored unless you clear and save.</p>
          <div className="setup-input-group">
            <label>OpenAI API Key</label>
            <input
              type="password"
              value={generation.openai_api_key}
              onChange={(e) => setGeneration((old) => ({ ...old, openai_api_key: e.target.value }))}
              placeholder="Enter OPENAI_API_KEY"
              disabled={saving === "generation"}
            />
          </div>
          <div className="setup-input-group">
            <label>Ideogram API Key</label>
            <input
              type="password"
              value={generation.ideogram_api_key}
              onChange={(e) => setGeneration((old) => ({ ...old, ideogram_api_key: e.target.value }))}
              placeholder="Enter IDEOGRAM_API_KEY"
              disabled={saving === "generation"}
            />
          </div>
          <div className="setup-input-group">
            <label>HF API Token</label>
            <input
              type="password"
              value={generation.hf_api_token}
              onChange={(e) => setGeneration((old) => ({ ...old, hf_api_token: e.target.value }))}
              placeholder="Enter HF_API_TOKEN"
              disabled={saving === "generation"}
            />
          </div>
          <div className="setup-input-group">
            <label>Leonardo API Key</label>
            <input
              type="password"
              value={generation.leonardo_api_key}
              onChange={(e) => setGeneration((old) => ({ ...old, leonardo_api_key: e.target.value }))}
              placeholder="Enter LEONARDO_API_KEY"
              disabled={saving === "generation"}
            />
          </div>
          <button className="btn--orange" onClick={saveGeneration} disabled={saving === "generation"}>
            {saving === "generation" ? "Saving..." : "Save Generation Keys"}
          </button>
        </div>
      </div>
    </div>
  );
}
