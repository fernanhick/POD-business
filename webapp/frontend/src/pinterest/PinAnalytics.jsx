import { useEffect, useState } from "react";
import { api } from "../api";

export default function PinAnalytics() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.pinterestGetAnalytics().then(setData).catch(() => {});
  }, []);

  if (!data) return <div className="loading">Loading analytics...</div>;

  const m = data.metrics || {};

  return (
    <div className="pin-analytics">
      <div className="kpi-bar">
        <div className="kpi-card">
          <div className="kpi-card__value">{data.total_pins}</div>
          <div className="kpi-card__label">Total Pins</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card__value">{data.posted_pins}</div>
          <div className="kpi-card__label">Posted</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card__value">{data.scheduled_pins}</div>
          <div className="kpi-card__label">Scheduled</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card__value">{m.impressions?.toLocaleString() || 0}</div>
          <div className="kpi-card__label">Impressions</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card__value">{m.saves || 0}</div>
          <div className="kpi-card__label">Saves</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card__value">{m.clicks || 0}</div>
          <div className="kpi-card__label">Clicks</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card__value">{m.ctr || 0}%</div>
          <div className="kpi-card__label">Avg CTR</div>
        </div>
      </div>

      {data.scaling_candidates?.length > 0 && (
        <div>
          <h3 style={{ color: "#4ade80", fontSize: 15, marginBottom: 8 }}>
            Scaling Candidates (CTR &ge; 3x avg)
          </h3>
          <div className="pin-grid">
            {data.scaling_candidates.map((pin) => (
              <div key={pin.id} className="pin-card">
                <div className="pin-card__image-wrap">
                  <img src={api.pinterestPinImageUrl(pin.id)} alt={pin.title} loading="lazy" />
                </div>
                <div className="pin-card__body">
                  <div className="pin-card__title">{pin.title}</div>
                  <div className="pin-card__meta">
                    {pin.impressions} imp &middot; {pin.clicks} clicks &middot;{" "}
                    {pin.impressions > 0
                      ? ((pin.clicks / pin.impressions) * 100).toFixed(1)
                      : 0}
                    % CTR
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.top_pins?.length > 0 && (
        <div>
          <h3 style={{ color: "#aaa", fontSize: 15, marginBottom: 8 }}>
            Top Pins
          </h3>
          <div className="table-wrap">
            <table className="analytics-table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Type</th>
                  <th>Impressions</th>
                  <th>Saves</th>
                  <th>Clicks</th>
                  <th>CTR</th>
                </tr>
              </thead>
              <tbody>
                {data.top_pins.map((pin) => (
                  <tr key={pin.id}>
                    <td>{pin.title}</td>
                    <td><span className={`badge ${pin.pin_type}`}>{pin.pin_type}</span></td>
                    <td>{pin.impressions?.toLocaleString()}</td>
                    <td>{pin.saves}</td>
                    <td>{pin.clicks}</td>
                    <td>
                      {pin.impressions > 0
                        ? ((pin.clicks / pin.impressions) * 100).toFixed(1)
                        : 0}
                      %
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {data.total_pins === 0 && (
        <div className="empty-state">
          No pins generated yet. Go to Pin Factory to get started.
        </div>
      )}
    </div>
  );
}
