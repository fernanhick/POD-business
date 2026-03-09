import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

export default function PinFactory() {
  const [designs, setDesigns] = useState([]);
  const [selected, setSelected] = useState(null);
  const [pins, setPins] = useState([]);
  const [checkedPins, setCheckedPins] = useState(new Set());
  const [generating, setGenerating] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.pinterestDesigns().then((r) => setDesigns(r.items || [])).catch(() => {});
  }, []);

  const handleGenerate = useCallback(async () => {
    if (!selected) return;
    setGenerating(true);
    setError(null);
    try {
      const res = await api.pinterestGeneratePins({
        design_filename: selected.filename,
      });
      setPins(res.items || []);
      setCheckedPins(new Set());
    } catch (e) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  }, [selected]);

  const toggleCheck = useCallback((pinId) => {
    setCheckedPins((prev) => {
      const next = new Set(prev);
      if (next.has(pinId)) next.delete(pinId);
      else next.add(pinId);
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    if (checkedPins.size === pins.length) {
      setCheckedPins(new Set());
    } else {
      setCheckedPins(new Set(pins.map((p) => p.id)));
    }
  }, [checkedPins, pins]);

  const handleSchedule = useCallback(async () => {
    if (checkedPins.size === 0) return;
    setScheduling(true);
    setError(null);
    try {
      await api.pinterestSchedulePins({
        pin_ids: Array.from(checkedPins),
      });
      setPins((prev) =>
        prev.map((p) =>
          checkedPins.has(p.id) ? { ...p, status: "queued" } : p
        )
      );
      setCheckedPins(new Set());
    } catch (e) {
      setError(e.message);
    } finally {
      setScheduling(false);
    }
  }, [checkedPins]);

  return (
    <div className="pin-factory">
      <div className="pin-factory__sidebar">
        <h3 style={{ margin: "0 0 8px", fontSize: 14, color: "#aaa" }}>
          Approved Designs
        </h3>
        {designs.length === 0 && (
          <p style={{ color: "#666", fontSize: 13 }}>No approved designs found</p>
        )}
        {designs.map((d) => (
          <div
            key={d.filename}
            className={`design-picker-item ${selected?.filename === d.filename ? "selected" : ""}`}
            onClick={() => setSelected(d)}
          >
            <img
              src={api.pinterestDesignImageUrl(d.filename)}
              alt={d.name || d.filename}
              loading="lazy"
            />
            <span className="design-picker-item__name">
              {d.name || d.filename.replace(".png", "").replace(/_/g, " ")}
            </span>
          </div>
        ))}
      </div>

      <div className="pin-factory__main">
        <div className="toolbar">
          <button
            className="btn--orange"
            disabled={!selected || generating}
            onClick={handleGenerate}
          >
            {generating ? "Generating..." : "Generate 20 Pins"}
          </button>

          {pins.length > 0 && (
            <>
              <button className="btn--outline" onClick={toggleAll}>
                {checkedPins.size === pins.length ? "Deselect All" : "Select All"}
              </button>
              <button
                className="btn--orange"
                disabled={checkedPins.size === 0 || scheduling}
                onClick={handleSchedule}
              >
                {scheduling
                  ? "Scheduling..."
                  : `Schedule Selected (${checkedPins.size})`}
              </button>
            </>
          )}
        </div>

        {error && (
          <p style={{ color: "#f87171", fontSize: 13 }}>{error}</p>
        )}

        {selected && pins.length === 0 && !generating && (
          <div className="empty-state">
            Select a design and click "Generate 20 Pins" to create pin variants.
          </div>
        )}

        <div className="pin-grid">
          {pins.map((pin) => (
            <div key={pin.id} className="pin-card">
              <div className="pin-card__image-wrap">
                <input
                  type="checkbox"
                  className="pin-card__checkbox"
                  checked={checkedPins.has(pin.id)}
                  onChange={() => toggleCheck(pin.id)}
                />
                <img
                  src={api.pinterestPinImageUrl(pin.id)}
                  alt={pin.title}
                  loading="lazy"
                />
              </div>
              <div className="pin-card__body">
                <div className="pin-card__title">{pin.title}</div>
                <div className="pin-card__meta">
                  <span className={`badge ${pin.status}`}>{pin.status}</span>
                  {" "}
                  <span>{pin.pin_type}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
