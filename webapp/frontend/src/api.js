function resolveApiBase() {
  const envBase = import.meta.env.VITE_API_BASE_URL;
  if (envBase) {
    return String(envBase).replace(/\/$/, "");
  }

  return "/api";
}

const API_BASE = resolveApiBase();

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let message;
    try {
      const body = await response.json();
      message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail || body);
    } catch {
      message = await response.text().catch(() => "");
    }
    throw new Error(message || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const api = {
  health: () => request("/health"),
  summary: () => request("/dashboard/summary"),
  designs: (params = {}) => {
    const query = new URLSearchParams(params).toString();
    return request(`/designs${query ? `?${query}` : ""}`);
  },
  generationOptions: () => request("/generation/options"),
  jobs: () => request("/jobs"),
  job: (id) => request(`/jobs/${id}`),
  generate: (payload) =>
    request("/generate", { method: "POST", body: JSON.stringify(payload) }),
  approve: (payload) =>
    request("/approvals", { method: "POST", body: JSON.stringify(payload) }),
  variant: (payload) =>
    request("/designs/variant", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  expenses: () => request("/expenses"),
  createExpense: (payload) =>
    request("/expenses", { method: "POST", body: JSON.stringify(payload) }),
  updateExpense: (id, payload) =>
    request(`/expenses/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  deleteExpense: (id) => request(`/expenses/${id}`, { method: "DELETE" }),
  designImageUrl: (designType, filename) => {
    const query = new URLSearchParams({ designType, filename }).toString();
    return `${API_BASE}/designs/image?${query}`;
  },
  printifyStatus: () => request("/printify/status"),
  printifyUpload: (payload) =>
    request("/printify/upload", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  // Pinterest
  pinterestStatus: () => request("/pinterest/status"),
  pinterestDesigns: () => request("/pinterest/designs"),
  pinterestDesignImageUrl: (filename) =>
    `${API_BASE}/pinterest/designs/image?filename=${encodeURIComponent(filename)}`,
  pinterestGeneratePins: (body) =>
    request("/pinterest/pins/generate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  pinterestListPins: (params = {}) =>
    request(`/pinterest/pins?${new URLSearchParams(params)}`),
  pinterestPinImageUrl: (id) => `${API_BASE}/pinterest/pins/image?id=${id}`,
  pinterestSchedulePins: (body) =>
    request("/pinterest/schedule", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  pinterestGetQueue: (days = 14) =>
    request(`/pinterest/schedule/queue?days=${days}`),
  pinterestRunNow: () => request("/pinterest/schedule/run", { method: "POST" }),
  pinterestGetScheduleSettings: () => request("/pinterest/schedule/settings"),
  pinterestGetAnalytics: () => request("/pinterest/analytics"),
  pinterestGetKeywords: (cat) =>
    request(`/pinterest/keywords${cat ? `?category=${cat}` : ""}`),
  pinterestGetAppPhase: () => request("/pinterest/app-phase"),
  pinterestSetAppPhase: (phase) =>
    request("/pinterest/app-phase", {
      method: "POST",
      body: JSON.stringify({ phase }),
    }),
  pinterestGenerateBurst: () =>
    request("/pinterest/app-phase/generate-burst", { method: "POST" }),

  // Etsy Setup
  etsySetupStatus: () => request("/etsy/setup/status"),
  etsySaveCredentials: (api_key, shared_secret) =>
    request("/etsy/setup/credentials", {
      method: "POST",
      body: JSON.stringify({ api_key, shared_secret }),
    }),
  etsyCreateSections: () =>
    request("/etsy/setup/create-sections", { method: "POST" }),
  etsyRefreshToken: () =>
    request("/etsy/setup/refresh-token", { method: "POST" }),
  etsyListSections: () => request("/etsy/sections"),
  etsyAssignSection: (listing_id, section_name) =>
    request("/etsy/sections/assign", {
      method: "POST",
      body: JSON.stringify({ listing_id, section_name }),
    }),

  // Pinterest Setup
  pinterestSetupStatus: () => request("/pinterest/setup/status"),
  pinterestSaveCredentials: (app_id, app_secret) =>
    request("/pinterest/setup/credentials", {
      method: "POST",
      body: JSON.stringify({ app_id, app_secret }),
    }),
  pinterestCreateBoards: () =>
    request("/pinterest/setup/create-boards", { method: "POST" }),
  pinterestRefreshToken: () =>
    request("/pinterest/setup/refresh-token", { method: "POST" }),
};
