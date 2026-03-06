# FRONTEND_CHANGES.md
> Step 4 of 8 — The ONLY changes to existing frontend files.
> Every change is additive. Nothing is deleted or rewritten.
> Read this before touching App.jsx or api.js.

---

## CHANGE 1 OF 3 — App.jsx: Add Pinterest Tab

File: `webapp/frontend/src/App.jsx`

Your existing tab system has 5 tabs: Dashboard, Designs, Generate, Expenses, Jobs.
Add Pinterest as the 6th tab. Find where the other tabs are defined and add one entry.

The exact code to add depends on how your tab state is managed.
Look for the pattern where tab labels are defined (likely an array or a series of
button/nav elements) and add this entry in the same style:

```jsx
// If your tabs are defined as an array, add this entry:
{ id: "pinterest", label: "Pinterest" }

// If your tabs are inline JSX button elements, add this in the same pattern:
<button
  onClick={() => setActiveTab("pinterest")}
  className={activeTab === "pinterest" ? "tab tab--active" : "tab"}
>
  Pinterest
</button>
```

Then in the section where each tab's content is conditionally rendered, add:

```jsx
{activeTab === "pinterest" && <PinterestTab />}
```

And add the import at the top of App.jsx:

```jsx
import PinterestTab from "./pinterest/PinterestTab";
```

**That is the complete change to App.jsx — one import line, one tab entry, one render condition.**

---

## CHANGE 2 OF 3 — api.js: Append Pinterest Functions

File: `webapp/frontend/src/api.js`

Do not touch any existing function in this file.
Scroll to the very bottom and append the following block:

```js
// ─────────────────────────────────────────────────────────────────────────────
// PINTEREST MODULE — added alongside existing API functions
// All routes use /api/pinterest/ prefix — no conflict with existing routes
// ─────────────────────────────────────────────────────────────────────────────

const PINTEREST_BASE = `${BASE_URL}/api/pinterest`
// Note: BASE_URL should already be defined earlier in api.js as the existing
// base URL (http://127.0.0.1:8000). Use whatever constant is already defined.
// If the existing file uses a different variable name, replace BASE_URL below.

// Approved designs available for pin generation (reads from workspace)
export const pinterestGetDesigns = () =>
  fetch(`${PINTEREST_BASE}/designs`).then(r => r.json())

export const pinterestGetDesignImageUrl = (filename) =>
  `${PINTEREST_BASE}/designs/image?filename=${encodeURIComponent(filename)}`

// Pin generation
export const pinterestGeneratePins = (body) =>
  fetch(`${PINTEREST_BASE}/pins/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(r => r.json())

export const pinterestListPins = (params = {}) =>
  fetch(`${PINTEREST_BASE}/pins?${new URLSearchParams(params)}`).then(r => r.json())

export const pinterestGetPinImageUrl = (pinId) =>
  `${PINTEREST_BASE}/pins/image?id=${pinId}`

// Scheduling
export const pinterestSchedulePins = (body) =>
  fetch(`${PINTEREST_BASE}/schedule`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(r => r.json())

export const pinterestGetQueue = (days = 14) =>
  fetch(`${PINTEREST_BASE}/schedule/queue?days=${days}`).then(r => r.json())

export const pinterestRunNow = () =>
  fetch(`${PINTEREST_BASE}/schedule/run`, { method: "POST" }).then(r => r.json())

export const pinterestGetScheduleSettings = () =>
  fetch(`${PINTEREST_BASE}/schedule/settings`).then(r => r.json())

// Analytics
export const pinterestGetAnalytics = () =>
  fetch(`${PINTEREST_BASE}/analytics`).then(r => r.json())

// Keywords
export const pinterestGetKeywords = (category) =>
  fetch(`${PINTEREST_BASE}/keywords${category ? `?category=${category}` : ""}`).then(r => r.json())

// Account status
export const pinterestGetStatus = () =>
  fetch(`${PINTEREST_BASE}/status`).then(r => r.json())
```

---

## CHANGE 3 OF 3 — No other existing files are touched

Everything else — `main.jsx`, `styles.css`, `vite.config.js`, `package.json`,
all workspace scripts, all spreadsheets — remains exactly as-is.

The new Pinterest UI lives entirely in:
`webapp/frontend/src/pinterest/` ← new folder, does not conflict with anything
