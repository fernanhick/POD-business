# FRONTEND_COMPONENTS.md
> Step 5 of 8 — All new files in webapp/frontend/src/pinterest/
> These are all new files. Nothing here modifies existing components.
> Match the visual style of your existing portal (same CSS classes, same patterns).

---

## FOLDER STRUCTURE

```
webapp/frontend/src/pinterest/
├── PinterestTab.jsx      ← root of the tab, owns sub-navigation
├── PinFactory.jsx        ← pick design → generate pins → schedule
├── PinSchedule.jsx       ← view and manage the posting queue
├── PinAnalytics.jsx      ← performance metrics and scaling candidates
└── AppMode.jsx           ← mobile app phase toggle + launch burst management
```

---

## PinterestTab.jsx

Root component rendered when the Pinterest tab is active.
Owns internal sub-navigation between the three views.
Match the sub-tab or section-switch pattern already used in your app.

```jsx
import { useState } from "react"
import PinFactory from "./PinFactory"
import PinSchedule from "./PinSchedule"
import PinAnalytics from "./PinAnalytics"
import AppMode from "./AppMode"

const VIEWS = [
  { id: "factory",   label: "Pin Factory" },
  { id: "schedule",  label: "Schedule" },
  { id: "analytics", label: "Analytics" },
  { id: "appmode",   label: "App Mode 📱" },
]

export default function PinterestTab() {
  const [view, setView] = useState("factory")

  return (
    <div className="pinterest-tab">
      {/* Sub-navigation — use same CSS pattern as existing tabs in your app */}
      <div className="pinterest-tab__nav">
        {VIEWS.map(v => (
          <button
            key={v.id}
            onClick={() => setView(v.id)}
            className={view === v.id ? "subtab subtab--active" : "subtab"}
          >
            {v.label}
          </button>
        ))}
      </div>

      {/* View content */}
      <div className="pinterest-tab__content">
        {view === "factory"   && <PinFactory />}
        {view === "schedule"  && <PinSchedule />}
        {view === "analytics" && <PinAnalytics />}
        {view === "appmode"   && <AppMode />}
      </div>
    </div>
  )
}
```

---

## PinFactory.jsx

Two-panel layout:
- Left: pick an approved design from the workspace
- Right: generate pin set, preview thumbnails, select and schedule

```jsx
import { useState, useEffect } from "react"
import {
  pinterestGetDesigns,
  pinterestGetDesignImageUrl,
  pinterestGeneratePins,
  pinterestGetPinImageUrl,
  pinterestSchedulePins,
} from "../api"

export default function PinFactory() {
  const [designs, setDesigns]       = useState([])
  const [selected, setSelected]     = useState(null)   // DesignOption
  const [pins, setPins]             = useState([])
  const [checkedPins, setChecked]   = useState(new Set())
  const [generating, setGenerating] = useState(false)
  const [scheduling, setScheduling] = useState(false)
  const [message, setMessage]       = useState("")

  useEffect(() => {
    pinterestGetDesigns().then(setDesigns)
  }, [])

  const handleGenerate = async () => {
    if (!selected) return
    setGenerating(true)
    setMessage("")
    try {
      const result = await pinterestGeneratePins({ design_filename: selected.filename })
      setPins(result)
      setChecked(new Set(result.map(p => p.id)))  // select all by default
      setMessage(`${result.length} pins generated.`)
    } catch (e) {
      setMessage("Error generating pins.")
    }
    setGenerating(false)
  }

  const handleSchedule = async () => {
    if (checkedPins.size === 0) return
    setScheduling(true)
    try {
      const res = await pinterestSchedulePins({ pin_ids: [...checkedPins] })
      setMessage(`${res.scheduled} pins scheduled.`)
      setPins(prev => prev.map(p => checkedPins.has(p.id) ? { ...p, status: "scheduled" } : p))
    } catch (e) {
      setMessage("Error scheduling pins.")
    }
    setScheduling(false)
  }

  const togglePin = (id) => {
    setChecked(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  return (
    <div className="pin-factory">
      {/* Left panel — design selector */}
      <div className="pin-factory__sidebar">
        <h3>Approved Designs</h3>
        <p className="hint">Only designs approved in workspace/front_a_sneaker/approved/ appear here.</p>

        {designs.length === 0 && <p className="empty">No approved designs found.</p>}

        {designs.map(d => (
          <div
            key={d.filename}
            className={`design-card ${selected?.filename === d.filename ? "design-card--active" : ""}`}
            onClick={() => { setSelected(d); setPins([]); setMessage("") }}
          >
            <img src={pinterestGetDesignImageUrl(d.filename)} alt={d.title} className="design-card__thumb" />
            <div className="design-card__info">
              <strong>{d.title}</strong>
              <span>{d.concept}</span>
              {d.product_url
                ? <span className="badge badge--green">Listed on Printify</span>
                : <span className="badge badge--gray">Not yet listed</span>}
            </div>
          </div>
        ))}
      </div>

      {/* Right panel — pin generation and preview */}
      <div className="pin-factory__main">
        {!selected && (
          <div className="pin-factory__empty">
            <p>Select an approved design on the left to generate pins.</p>
          </div>
        )}

        {selected && (
          <>
            <div className="pin-factory__header">
              <h3>{selected.title}</h3>
              <p>{selected.concept}</p>
              <button
                className="btn btn--primary"
                onClick={handleGenerate}
                disabled={generating}
              >
                {generating ? "Generating..." : "Generate 20 Pins"}
              </button>
            </div>

            {message && <p className="pin-factory__message">{message}</p>}

            {pins.length > 0 && (
              <>
                {/* Schedule bar */}
                <div className="pin-factory__schedule-bar">
                  <span>{checkedPins.size} of {pins.length} pins selected</span>
                  <button
                    className="btn btn--orange"
                    onClick={handleSchedule}
                    disabled={scheduling || checkedPins.size === 0}
                  >
                    {scheduling ? "Scheduling..." : "Schedule Selected"}
                  </button>
                </div>

                {/* Pin grid */}
                <div className="pin-grid">
                  {pins.map(pin => (
                    <div
                      key={pin.id}
                      className={`pin-card ${checkedPins.has(pin.id) ? "pin-card--selected" : ""}`}
                      onClick={() => togglePin(pin.id)}
                    >
                      <div className="pin-card__checkbox">
                        <input type="checkbox" readOnly checked={checkedPins.has(pin.id)} />
                      </div>
                      {pin.image_url && (
                        <img src={pinterestGetPinImageUrl(pin.id)} alt={pin.title} className="pin-card__image" />
                      )}
                      <div className="pin-card__meta">
                        <span className="pin-card__template">{pin.template_name}</span>
                        <span className={`badge badge--${pin.status === "scheduled" ? "purple" : "gray"}`}>
                          {pin.status}
                        </span>
                        <p className="pin-card__title">{pin.title}</p>
                        <p className="pin-card__board">{pin.board_name}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  )
}
```

---

## PinSchedule.jsx

Shows the posting queue for the next 14 days and current settings.

```jsx
import { useState, useEffect } from "react"
import { pinterestGetQueue, pinterestGetScheduleSettings, pinterestRunNow, pinterestGetPinImageUrl } from "../api"

export default function PinSchedule() {
  const [queue, setQueue]         = useState([])
  const [settings, setSettings]   = useState(null)
  const [totalQueued, setTotal]   = useState(0)
  const [nextPost, setNextPost]   = useState(null)
  const [posting, setPosting]     = useState(false)
  const [message, setMessage]     = useState("")

  useEffect(() => {
    pinterestGetQueue(14).then(data => {
      setQueue(data.queue || [])
      setTotal(data.total_queued || 0)
      setNextPost(data.next_post_at)
    })
    pinterestGetScheduleSettings().then(setSettings)
  }, [])

  const handlePostNow = async () => {
    setPosting(true)
    try {
      await pinterestRunNow()
      setMessage("Post triggered successfully.")
      pinterestGetQueue(14).then(data => { setQueue(data.queue || []); setTotal(data.total_queued || 0) })
    } catch (e) {
      setMessage("Post trigger failed.")
    }
    setPosting(false)
  }

  // Group queue items by date
  const byDate = queue.reduce((acc, item) => {
    const day = item.scheduled_at.slice(0, 10)
    if (!acc[day]) acc[day] = []
    acc[day].push(item)
    return acc
  }, {})

  return (
    <div className="pin-schedule">
      {/* Summary bar */}
      <div className="pin-schedule__summary">
        <div className="kpi-card">
          <span className="kpi-card__label">Queued Pins</span>
          <span className="kpi-card__value">{totalQueued}</span>
        </div>
        {nextPost && (
          <div className="kpi-card">
            <span className="kpi-card__label">Next Post</span>
            <span className="kpi-card__value">{new Date(nextPost).toLocaleString()}</span>
          </div>
        )}
        {settings && (
          <div className="kpi-card">
            <span className="kpi-card__label">Daily Target</span>
            <span className="kpi-card__value">{settings.pins_per_day} pins/day</span>
          </div>
        )}
        <button className="btn btn--orange" onClick={handlePostNow} disabled={posting}>
          {posting ? "Posting..." : "Post Now"}
        </button>
      </div>

      {message && <p className="pin-schedule__message">{message}</p>}

      {/* Queue timeline */}
      {Object.keys(byDate).length === 0 && (
        <p className="empty">No pins in queue. Generate pins in Pin Factory and schedule them.</p>
      )}

      {Object.entries(byDate).map(([date, items]) => (
        <div key={date} className="schedule-day">
          <h4 className="schedule-day__date">
            {new Date(date).toLocaleDateString("en-US", { weekday: "long", month: "short", day: "numeric" })}
            <span className="schedule-day__count">{items.length} pin{items.length !== 1 ? "s" : ""}</span>
          </h4>
          <div className="schedule-day__pins">
            {items.map(item => (
              <div key={item.job_id} className="schedule-pin-card">
                <img src={pinterestGetPinImageUrl(item.pin_id)} alt={item.pin_title} className="schedule-pin-card__thumb" />
                <div className="schedule-pin-card__info">
                  <strong>{item.pin_title}</strong>
                  <span>{item.board_name}</span>
                  <span className="schedule-pin-card__time">
                    {new Date(item.scheduled_at).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
                <span className={`badge badge--${item.status === "pending" ? "purple" : "green"}`}>
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
```

---

## PinAnalytics.jsx

Performance dashboard: KPI cards, top pins, scaling candidates.

```jsx
import { useState, useEffect } from "react"
import { pinterestGetAnalytics, pinterestGetPinImageUrl } from "../api"

export default function PinAnalytics() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    pinterestGetAnalytics().then(d => { setData(d); setLoading(false) })
  }, [])

  if (loading) return <p>Loading analytics...</p>
  if (!data)   return <p>No analytics data yet. Start posting pins to see performance.</p>

  return (
    <div className="pin-analytics">
      {/* KPI row */}
      <div className="kpi-row">
        {[
          { label: "Pins Generated",  value: data.total_pins_generated },
          { label: "Pins Posted",     value: data.total_pins_posted },
          { label: "Pins Scheduled",  value: data.total_pins_scheduled },
          { label: "Total Impressions", value: data.total_impressions.toLocaleString() },
          { label: "Total Saves",     value: data.total_saves.toLocaleString() },
          { label: "Total Clicks",    value: data.total_clicks.toLocaleString() },
          { label: "Avg CTR",         value: `${data.avg_ctr_pct}%` },
        ].map(kpi => (
          <div key={kpi.label} className="kpi-card">
            <span className="kpi-card__label">{kpi.label}</span>
            <span className="kpi-card__value">{kpi.value}</span>
          </div>
        ))}
      </div>

      {/* Scaling candidates */}
      {data.scaling_candidates.length > 0 && (
        <div className="analytics-section">
          <h3>🔥 Scale These Designs</h3>
          <p className="hint">These pins have CTR 3× above your average. Generate more variations from the same design.</p>
          <div className="pin-grid pin-grid--compact">
            {data.scaling_candidates.map(pin => (
              <div key={pin.pin_id} className="pin-card pin-card--highlight">
                <img src={pinterestGetPinImageUrl(pin.pin_id)} alt={pin.title} className="pin-card__image" />
                <div className="pin-card__meta">
                  <strong>{pin.title}</strong>
                  <span>CTR: {pin.ctr_pct}%  •  Clicks: {pin.outbound_clicks}  •  Saves: {pin.saves}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top pins table */}
      {data.top_pins.length > 0 && (
        <div className="analytics-section">
          <h3>Top Performing Pins</h3>
          <table className="data-table">
            <thead>
              <tr>
                <th>Preview</th>
                <th>Title</th>
                <th>Impressions</th>
                <th>Saves</th>
                <th>Clicks</th>
                <th>CTR</th>
              </tr>
            </thead>
            <tbody>
              {data.top_pins.map(pin => (
                <tr key={pin.pin_id}>
                  <td><img src={pinterestGetPinImageUrl(pin.pin_id)} alt="" style={{ width: 48, height: 72, objectFit: "cover" }} /></td>
                  <td>{pin.title}</td>
                  <td>{pin.impressions.toLocaleString()}</td>
                  <td>{pin.saves.toLocaleString()}</td>
                  <td>{pin.outbound_clicks.toLocaleString()}</td>
                  <td>{pin.ctr_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data.total_pins_posted === 0 && (
        <p className="empty">No posted pins yet. Analytics will appear here once pins start going live.</p>
      )}
    </div>
  )
}
```

---

## CSS — What to Add to styles.css

Append these classes to `webapp/frontend/src/styles.css`.
Match the values (colors, spacing) to whatever your existing styles use.
These are the new class names referenced by the Pinterest components above.

```css
/* ── Pinterest Tab ─────────────────────────────────────────── */
.pinterest-tab__nav { display: flex; gap: 8px; margin-bottom: 20px; border-bottom: 1px solid #ddd; padding-bottom: 8px; }
.subtab { background: none; border: none; padding: 8px 16px; cursor: pointer; color: #555; border-radius: 4px 4px 0 0; }
.subtab--active { background: #E8500A; color: #fff; font-weight: 600; }

/* ── Pin Factory ───────────────────────────────────────────── */
.pin-factory { display: flex; gap: 24px; min-height: 600px; }
.pin-factory__sidebar { width: 280px; flex-shrink: 0; overflow-y: auto; }
.pin-factory__main { flex: 1; }
.pin-factory__empty { display: flex; align-items: center; justify-content: center; height: 300px; color: #999; }
.pin-factory__header { margin-bottom: 16px; }
.pin-factory__message { color: #E8500A; margin: 8px 0; }
.pin-factory__schedule-bar { display: flex; align-items: center; justify-content: space-between; padding: 12px; background: #f5f5f5; border-radius: 6px; margin-bottom: 16px; }

/* Design cards in sidebar */
.design-card { display: flex; gap: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 6px; cursor: pointer; margin-bottom: 8px; transition: border-color 0.15s; }
.design-card--active { border-color: #E8500A; background: #fdeee5; }
.design-card__thumb { width: 60px; height: 60px; object-fit: cover; border-radius: 4px; }
.design-card__info { display: flex; flex-direction: column; gap: 4px; font-size: 13px; }

/* Pin grid */
.pin-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
.pin-grid--compact { grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); }
.pin-card { border: 2px solid #ddd; border-radius: 6px; cursor: pointer; overflow: hidden; transition: border-color 0.15s; }
.pin-card--selected { border-color: #E8500A; }
.pin-card--highlight { border-color: #E8500A; background: #fdeee5; }
.pin-card__image { width: 100%; aspect-ratio: 2/3; object-fit: cover; display: block; }
.pin-card__meta { padding: 8px; font-size: 12px; }
.pin-card__template { display: block; font-weight: 600; color: #333; margin-bottom: 4px; }
.pin-card__title { color: #555; margin: 4px 0 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.pin-card__board { color: #999; font-size: 11px; }
.pin-card__checkbox { position: absolute; top: 6px; left: 6px; }

/* ── Pin Schedule ──────────────────────────────────────────── */
.pin-schedule__summary { display: flex; gap: 16px; align-items: center; margin-bottom: 24px; flex-wrap: wrap; }
.pin-schedule__message { color: #E8500A; margin: 8px 0; }
.schedule-day { margin-bottom: 24px; }
.schedule-day__date { font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.schedule-day__count { font-size: 12px; font-weight: 400; color: #999; }
.schedule-day__pins { display: flex; flex-direction: column; gap: 8px; }
.schedule-pin-card { display: flex; align-items: center; gap: 12px; padding: 10px; border: 1px solid #eee; border-radius: 6px; }
.schedule-pin-card__thumb { width: 40px; height: 60px; object-fit: cover; border-radius: 3px; }
.schedule-pin-card__info { flex: 1; font-size: 13px; display: flex; flex-direction: column; gap: 2px; }
.schedule-pin-card__time { color: #E8500A; font-weight: 600; }

/* ── Analytics ─────────────────────────────────────────────── */
.kpi-row { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 28px; }
.kpi-card { background: #f5f5f5; border-radius: 8px; padding: 16px 20px; min-width: 120px; }
.kpi-card__label { display: block; font-size: 12px; color: #777; margin-bottom: 6px; }
.kpi-card__value { display: block; font-size: 24px; font-weight: 700; color: #1a1a1a; }
.analytics-section { margin-bottom: 32px; }
.analytics-section h3 { font-size: 16px; font-weight: 600; margin-bottom: 12px; }

/* ── Shared utilities ──────────────────────────────────────── */
.badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.badge--green  { background: #d1fae5; color: #065f46; }
.badge--gray   { background: #f3f4f6; color: #6b7280; }
.badge--purple { background: #ede9fe; color: #5b21b6; }
.badge--orange { background: #fdeee5; color: #E8500A; }
.btn--orange { background: #E8500A; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; }
.btn--orange:disabled { opacity: 0.5; cursor: not-allowed; }
.hint { font-size: 12px; color: #999; margin: 0 0 12px; }
.empty { color: #aaa; text-align: center; padding: 40px 0; }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 8px; border-bottom: 2px solid #eee; color: #555; }
.data-table td { padding: 8px; border-bottom: 1px solid #f0f0f0; }
```

---

## AppMode.jsx

Controls the mobile app promotion phase.
The founder uses this to switch between pre-launch and launched mode
and to generate the launch burst pin set before flipping the switch.

```jsx
import { useState, useEffect } from "react"
import { pinterestGetAppPhase, pinterestSetAppPhase, pinterestGenerateBurst } from "../api"

export default function AppMode() {
  const [data, setData]         = useState(null)
  const [loading, setLoading]   = useState(true)
  const [switching, setSwitching] = useState(false)
  const [bursting, setBursting]  = useState(false)
  const [message, setMessage]   = useState("")

  const load = () =>
    pinterestGetAppPhase().then(d => { setData(d); setLoading(false) })

  useEffect(() => { load() }, [])

  const handleSwitch = async (newPhase) => {
    if (!confirm(
      newPhase === "launched"
        ? "Switch to LAUNCHED mode? This will immediately release all draft app promo pins into the posting queue."
        : "Switch back to PRE-LAUNCH mode?"
    )) return

    setSwitching(true)
    setMessage("")
    try {
      const updated = await pinterestSetAppPhase(newPhase)
      setData(updated)
      setMessage(
        newPhase === "launched"
          ? `Launched! ${updated.launch_burst_generated} burst pins released to queue.`
          : "Switched back to pre-launch mode."
      )
    } catch (e) {
      setMessage("Error switching phase.")
    }
    setSwitching(false)
  }

  const handleGenerateBurst = async () => {
    if (!confirm(`Generate ${data.launch_burst_total} launch burst pins? They will sit as drafts until you activate launch mode.`)) return
    setBursting(true)
    setMessage("")
    try {
      await pinterestGenerateBurst()
      setMessage("Generating burst pins in background. Refresh in a moment to see progress.")
      setTimeout(load, 5000)  // refresh after 5s
    } catch (e) {
      setMessage("Error starting burst generation.")
    }
    setBursting(false)
  }

  if (loading) return <p>Loading app phase status...</p>
  if (!data)   return <p>Could not load app phase.</p>

  const isLaunched = data.phase === "launched"

  return (
    <div className="app-mode">

      {/* Phase status banner */}
      <div className={`app-mode__banner ${isLaunched ? "app-mode__banner--launched" : "app-mode__banner--pre"}`}>
        <div className="app-mode__banner-content">
          <span className="app-mode__phase-label">
            {isLaunched ? "🟢 LAUNCHED" : "🟡 PRE-LAUNCH"}
          </span>
          <p className="app-mode__phase-desc">
            {isLaunched
              ? "App pins are linking to App Store / Google Play. Promotion is live."
              : "App pins are linking to your website and email capture. Building the waitlist."}
          </p>
        </div>

        {/* Toggle button */}
        <button
          className={`btn ${isLaunched ? "btn--gray" : "btn--orange"}`}
          onClick={() => handleSwitch(isLaunched ? "pre_launch" : "launched")}
          disabled={switching || (!isLaunched && !data.launch_burst_ready)}
          title={!isLaunched && !data.launch_burst_ready ? "Generate burst pins before launching" : ""}
        >
          {switching
            ? "Switching..."
            : isLaunched
              ? "Switch to Pre-Launch"
              : "🚀 Activate Launch Mode"}
        </button>
      </div>

      {message && <p className="app-mode__message">{message}</p>}

      {/* Current URLs */}
      <div className="app-mode__section">
        <h3>Current Pin Links</h3>
        <table className="data-table">
          <tbody>
            <tr>
              <td>App Website</td>
              <td>{data.app_website_url || <span className="empty-val">Not set — add APP_WEBSITE_URL to .env</span>}</td>
            </tr>
            <tr>
              <td>Email Capture Page</td>
              <td>{data.app_email_capture_url || <span className="empty-val">Not set — add APP_EMAIL_CAPTURE_URL to .env</span>}</td>
            </tr>
            <tr>
              <td>App Store URL</td>
              <td>{data.app_store_url || <span className="empty-val">Not set — add APP_STORE_URL to .env before launch</span>}</td>
            </tr>
            <tr>
              <td>Google Play URL</td>
              <td>{data.play_store_url || <span className="empty-val">Not set — add PLAY_STORE_URL to .env before launch</span>}</td>
            </tr>
          </tbody>
        </table>
        <p className="hint">URLs are set in workspace/.env — restart the backend after changing them.</p>
      </div>

      {/* Launch burst status */}
      <div className="app-mode__section">
        <h3>Launch Day Burst</h3>
        <p>
          Generate <strong>{data.launch_burst_total} pins</strong> in advance, hold them as drafts,
          then release them all the moment you flip to launched mode.
          This floods Pinterest with your app on day one when App Store ranking matters most.
        </p>

        {/* Progress bar */}
        <div className="burst-progress">
          <div
            className="burst-progress__bar"
            style={{ width: `${Math.min(100, (data.launch_burst_generated / data.launch_burst_total) * 100)}%` }}
          />
        </div>
        <p className="burst-progress__label">
          {data.launch_burst_generated} / {data.launch_burst_total} pins generated
          {data.launch_burst_ready && " ✅ Ready to launch"}
        </p>

        {!data.launch_burst_ready && !isLaunched && (
          <button
            className="btn btn--orange"
            onClick={handleGenerateBurst}
            disabled={bursting}
          >
            {bursting ? "Generating..." : `Generate ${data.launch_burst_total} Burst Pins`}
          </button>
        )}

        {data.launch_burst_ready && !isLaunched && (
          <p className="app-mode__ready-msg">
            ✅ Burst pins are ready. Hit "Activate Launch Mode" above to release them.
          </p>
        )}

        {isLaunched && (
          <p className="hint">Burst pins have been released. Check the Schedule tab to see them queued.</p>
        )}
      </div>

    </div>
  )
}
```

### Add these functions to api.js (append alongside the other Pinterest functions)

```js
// App Phase (mobile app promotion)
export const pinterestGetAppPhase = () =>
  fetch(`${PINTEREST_BASE}/app-phase`).then(r => r.json())

export const pinterestSetAppPhase = (phase) =>
  fetch(`${PINTEREST_BASE}/app-phase`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ phase }),
  }).then(r => r.json())

export const pinterestGenerateBurst = () =>
  fetch(`${PINTEREST_BASE}/app-phase/generate-burst`, { method: "POST" }).then(r => r.json())
```

### Additional CSS for AppMode (append to styles.css)

```css
/* ── App Mode ──────────────────────────────────────────────── */
.app-mode { max-width: 800px; }
.app-mode__banner { display: flex; align-items: center; justify-content: space-between; gap: 20px; padding: 20px 24px; border-radius: 10px; margin-bottom: 28px; flex-wrap: wrap; }
.app-mode__banner--pre      { background: #fffbeb; border: 2px solid #f59e0b; }
.app-mode__banner--launched { background: #f0fdf4; border: 2px solid #22c55e; }
.app-mode__phase-label { font-size: 18px; font-weight: 700; display: block; margin-bottom: 6px; }
.app-mode__phase-desc  { font-size: 13px; color: #555; margin: 0; }
.app-mode__message     { color: #E8500A; font-weight: 600; margin: 0 0 16px; }
.app-mode__section     { margin-bottom: 32px; }
.app-mode__section h3  { font-size: 16px; font-weight: 600; margin-bottom: 10px; }
.app-mode__ready-msg   { color: #16a34a; font-weight: 600; margin-top: 10px; }
.empty-val             { color: #ccc; font-style: italic; }
.burst-progress        { background: #f3f4f6; border-radius: 6px; height: 12px; margin: 12px 0 6px; overflow: hidden; }
.burst-progress__bar   { background: #E8500A; height: 100%; border-radius: 6px; transition: width 0.4s; }
.burst-progress__label { font-size: 13px; color: #555; margin-bottom: 12px; }
.btn--gray { background: #e5e7eb; color: #374151; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 600; }
```
