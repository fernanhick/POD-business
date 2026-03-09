import { useCallback, useEffect, useState } from "react";
import { api } from "../api";

export default function PinSchedule() {
  const [queue, setQueue] = useState([]);
  const [settings, setSettings] = useState(null);
  const [posting, setPosting] = useState(false);

  const load = useCallback(() => {
    api.pinterestGetQueue().then((r) => setQueue(r.items || [])).catch(() => {});
    api.pinterestGetScheduleSettings().then(setSettings).catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  const handlePostNow = useCallback(async () => {
    setPosting(true);
    try {
      await api.pinterestRunNow();
      load();
    } catch {
      // ignore
    } finally {
      setPosting(false);
    }
  }, [load]);

  // Group queue by date
  const grouped = {};
  for (const item of queue) {
    const date = item.scheduled_at?.split("T")[0] || "Unknown";
    if (!grouped[date]) grouped[date] = [];
    grouped[date].push(item);
  }

  const pendingCount = queue.filter((q) => q.status === "pending").length;
  const nextPost = queue.find((q) => q.status === "pending");

  return (
    <div className="pin-schedule">
      <div className="kpi-bar">
        <div className="kpi-card">
          <div className="kpi-card__value">{pendingCount}</div>
          <div className="kpi-card__label">Queued</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card__value">
            {nextPost ? new Date(nextPost.scheduled_at).toLocaleString() : "--"}
          </div>
          <div className="kpi-card__label">Next Post</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card__value">
            {settings?.pins_per_day || "--"}
          </div>
          <div className="kpi-card__label">Daily Target</div>
        </div>
        <div className="kpi-card">
          <div className="kpi-card__value">
            {settings?.holiday_multiplier ? `${settings.holiday_multiplier}x` : "1x"}
          </div>
          <div className="kpi-card__label">Holiday Boost</div>
        </div>
      </div>

      <div className="toolbar">
        <button
          className="btn--orange"
          disabled={posting || pendingCount === 0}
          onClick={handlePostNow}
        >
          {posting ? "Posting..." : "Post Now"}
        </button>
        <span style={{ fontSize: 12, color: "#888" }}>
          Times: {settings?.post_times?.join(", ") || "--"} ({settings?.timezone || "--"})
        </span>
      </div>

      {queue.length === 0 && (
        <div className="empty-state">
          No pins scheduled. Go to Pin Factory to generate and schedule pins.
        </div>
      )}

      {Object.entries(grouped).map(([date, items]) => (
        <div key={date} className="schedule-day">
          <div className="schedule-day__header">{date}</div>
          <div className="schedule-day__pins">
            {items.map((item) => (
              <div key={item.id} className="schedule-pin-row">
                <img
                  src={api.pinterestPinImageUrl(item.pin_id)}
                  alt={item.pin?.title || "Pin"}
                  loading="lazy"
                />
                <div className="schedule-pin-row__info">
                  <div className="schedule-pin-row__title">
                    {item.pin?.title || "Untitled"}
                  </div>
                  <div className="schedule-pin-row__time">
                    {new Date(item.scheduled_at).toLocaleTimeString()} &middot;{" "}
                    {item.pin?.pin_type || ""}
                  </div>
                </div>
                <span className={`badge ${item.status}`}>{item.status}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
