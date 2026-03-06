const API_BASE = "http://127.0.0.1:8000/api";

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
      message = body.detail || JSON.stringify(body);
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
    request("/designs/variant", { method: "POST", body: JSON.stringify(payload) }),
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
    request("/printify/upload", { method: "POST", body: JSON.stringify(payload) }),
};
