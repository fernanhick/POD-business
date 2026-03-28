import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "./api";
import PinterestTab from "./pinterest/PinterestTab";
import EtsySetup from "./etsy/EtsySetup";
import KeysSetup from "./setup/KeysSetup";
import PrepareTab from "./prepare/PrepareTab";

const NAV_ITEMS = [
  "Dashboard",
  "Designs",
  "Generate",
  "Prepare",
  "Expenses",
  "Jobs",
  "Setup",
  "Etsy",
  "Pinterest",
];

const initialGeneration = {
  designType: "sneaker",
  visualMode: "random",
  phraseVisibilityMode: "balanced",
  palette: "0",
  count: "0",
  dropId: "",
  phrase: "",
  niche: "",
  subNiche: "",
  skipApi: false,
  openaiHd: false,
  gptQuality: "medium",
  mascotExpression: "random",
  mascotMatchColorway: false,
  promptHint: "",
};

const COUNT_OPTIONS = [
  { value: "0", label: "All (default batch)" },
  { value: "1", label: "Single design" },
  { value: "10", label: "10 designs" },
  { value: "20", label: "20 designs" },
  { value: "custom", label: "Custom amount..." },
];

const ORIGINAL_PALETTE_OPTIONS = [
  { value: "0", label: "Black & Cream (vintage wash)" },
  { value: "1", label: "Off-white & Charcoal (distressed)" },
  { value: "2", label: "Forest Green & Ecru (military)" },
  { value: "3", label: "Washed Black & Bone White (faded)" },
];

const EXTENDED_PALETTE_OPTIONS = [
  { value: "4", label: "Navy & Gold (luxury streetwear)" },
  { value: "5", label: "Burgundy & Cream (vintage sport)" },
  { value: "6", label: "Rust Orange & Sand (earth tone)" },
  { value: "7", label: "Black & White (high contrast)" },
  { value: "8", label: "Olive & Tan (utilitarian)" },
  { value: "9", label: "Slate Grey & Neon Green (tech)" },
  { value: "10", label: "Terracotta & Ivory (bohemian)" },
  { value: "11", label: "Deep Teal & Cream (coastal)" },
  { value: "12", label: "Dusty Rose & Charcoal (modern)" },
  { value: "13", label: "Mustard & Dark Brown (retro 70s)" },
  { value: "14", label: "Lavender & Slate (muted pastel)" },
  { value: "15", label: "Red & Black (bold graphic)" },
];

const PALETTE_OPTIONS = [
  ...ORIGINAL_PALETTE_OPTIONS,
  ...EXTENDED_PALETTE_OPTIONS,
];

function renderPaletteOptions() {
  return [
    <optgroup key="original-colorways" label="Original Colorways">
      {ORIGINAL_PALETTE_OPTIONS.map((p) => (
        <option key={p.value} value={p.value}>
          {p.label}
        </option>
      ))}
    </optgroup>,
    <optgroup key="new-colorways" label="New Colorways">
      {EXTENDED_PALETTE_OPTIONS.map((p) => (
        <option key={p.value} value={p.value}>
          {p.label}
        </option>
      ))}
    </optgroup>,
  ];
}

const VISUAL_MODE_HINTS = {
  random:
    "Randomly generates a text design, graphic + text, or graphic-only design.",
  text_only:
    "Ideogram renders the complete typography design with text in one shot. Best for text-heavy streetwear and quote designs.",
  graphic_text:
    "HuggingFace generates the graphic, then Ideogram adds text via remix. Two-step pipeline for best quality.",
  graphic_only:
    "HuggingFace generates a standalone graphic/illustration with no text overlay.",
  text_only_openai:
    "OpenAI DALL-E 3 renders the complete design — graphic + text in one shot (~$0.04/image, ~$0.08 HD).",
  graphic_openai:
    "OpenAI DALL-E 3 generates a standalone graphic/illustration with no text (~$0.04/image, ~$0.08 HD).",
  text_gpt_image:
    "GPT Image 1 renders complete design with text — native transparent bg, ~98% text accuracy (~$0.02 low / ~$0.06 med / ~$0.26 high).",
  graphic_gpt_image:
    "GPT Image 1 generates graphic only, no text — native transparent bg (~$0.02 low / ~$0.06 med / ~$0.26 high).",
  mascot_gpt_image:
    "GPT Image 1 generates mascot chimp character with text — uses reference sheet for consistency (~$0.02 low / ~$0.06 med / ~$0.26 high).",
};

const initialExpense = {
  date: new Date().toISOString().slice(0, 10),
  front: "BOTH",
  category: "Software",
  description: "",
  amount: "",
  taxDeductible: "Yes",
  receipt: "No",
  notes: "",
};

function statusClass(status) {
  const value = String(status || "").toLowerCase();
  if (value.includes("approved")) return "approved";
  if (value.includes("reject")) return "rejected";
  if (value.includes("generated")) return "generated";
  return value || "missing";
}

export function App() {
  const [tab, setTab] = useState("Dashboard");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [summary, setSummary] = useState(null);
  const [designs, setDesigns] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [expenses, setExpenses] = useState([]);
  const [generationForm, setGenerationForm] = useState(initialGeneration);
  const [expenseForm, setExpenseForm] = useState(initialExpense);
  const [editingExpenseId, setEditingExpenseId] = useState("");
  const [designFilters, setDesignFilters] = useState({
    designType: "",
    status: "all",
  });
  const [designSubTab, setDesignSubTab] = useState("pipeline");
  const [modalState, setModalState] = useState(null);
  const [variantForm, setVariantForm] = useState(null);
  const [selectedJobLog, setSelectedJobLog] = useState(null);
  const [generationOptions, setGenerationOptions] = useState({
    sneaker: { dropIds: [] },
    general: { niches: [], subNiches: [], phrases: [] },
  });
  const [genModal, setGenModal] = useState(null);
  const genModalLogRef = useRef(null);
  const [providerStatus, setProviderStatus] = useState({
    printify: { configured: false, market: "US" },
    printful: { configured: false, market: "EU" },
  });
  const [selectedProviderByFile, setSelectedProviderByFile] = useState({});
  const [uploadingDesign, setUploadingDesign] = useState(null);

  const loadAll = useCallback(async (silent = false) => {
    if (!silent) {
      setLoading(true);
      setError("");
    }
    try {
      const [summaryRes, designsRes, jobsRes, expensesRes] = await Promise.all([
        api.summary(),
        api.designs(),
        api.jobs(),
        api.expenses(),
      ]);
      const generationOptionsRes = await api.generationOptions();
      setSummary(summaryRes);
      setDesigns(designsRes.items || []);
      setJobs(jobsRes.items || []);
      setExpenses(expensesRes.items || []);
      setGenerationOptions(generationOptionsRes || {});
    } catch (err) {
      if (!silent) setError(err.message || "Failed to load data");
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const refreshProviderStatus = useCallback(async () => {
    try {
      const res = await api.podProviderStatus();
      const providers = res?.providers || {};
      setProviderStatus({
        printify: providers.printify || { configured: false, market: "US" },
        printful: providers.printful || { configured: false, market: "EU" },
      });
    } catch {
      // ignore status fetch errors
    }
  }, []);

  useEffect(() => {
    refreshProviderStatus();
  }, [refreshProviderStatus]);

  const handlePrintifyUpload = async (
    designType,
    filename,
    productType = "tshirt",
    provider = "printify",
  ) => {
    const market = provider === "printful" ? "EU" : "US";
    const uploadKey = `${filename}:${provider}:${productType}`;
    setUploadingDesign(uploadKey);
    setError("");
    try {
      await api.printifyUpload({
        designType,
        filename,
        productType,
        provider,
        market,
        draft: false,
      });
      await loadAll(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploadingDesign(null);
    }
  };

  // Auto-poll: 3s when a job is running/queued, 30s otherwise
  const hasActiveJob = jobs.some(
    (j) => j.status === "running" || j.status === "queued",
  );
  const pollInterval = hasActiveJob ? 3000 : 30000;

  useEffect(() => {
    const timer = setInterval(() => loadAll(true), pollInterval);
    return () => clearInterval(timer);
  }, [loadAll, pollInterval]);

  const filteredDesigns = useMemo(() => {
    return designs.filter((item) => {
      if (
        designFilters.designType &&
        item.designType !== designFilters.designType
      )
        return false;
      if (designSubTab === "pipeline") {
        if (item.location !== "generated") return false;
      } else if (designSubTab === "approved") {
        if (item.location !== "approved" || item.printifyProductId)
          return false;
      } else if (designSubTab === "published") {
        if (!item.printifyProductId) return false;
      } else if (designSubTab === "rejected") {
        if (item.location !== "rejected") return false;
      }
      return true;
    });
  }, [designs, designFilters, designSubTab]);

  const handleGenerate = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const payload = {
        designType: generationForm.designType,
        visualMode: generationForm.visualMode,
        phraseVisibilityMode: generationForm.phraseVisibilityMode,
        palette: Number(generationForm.palette),
        count: Number(generationForm.count) || 0,
        dropId: generationForm.dropId || null,
        phrase: generationForm.phrase || null,
        niche: generationForm.niche || null,
        subNiche: generationForm.subNiche || null,
        skipApi: generationForm.skipApi,
        openaiHd: generationForm.openaiHd,
        gptQuality: generationForm.gptQuality,
        promptHint: generationForm.promptHint,
        mascotExpression: generationForm.mascotExpression,
        mascotMatchColorway: generationForm.mascotMatchColorway,
      };
      const result = await api.generate(payload);
      setGenModal({
        jobId: result.jobId,
        phase: "generating",
        output: "",
        status: "queued",
        generatedFiles: [],
        designType: payload.designType,
        showLog: true,
        approvedFiles: {},
      });
    } catch (err) {
      setError(err.message);
    }
  };

  const handleVariant = async (e) => {
    e.preventDefault();
    if (!variantForm) return;
    setError("");
    try {
      const payload = {
        designType: variantForm.designType,
        designName: variantForm.designName,
        palette: Number(variantForm.palette),
        visualMode: variantForm.visualMode,
        phraseVisibilityMode: variantForm.phraseVisibilityMode || "balanced",
        phrase: variantForm.phrase || null,
        niche: variantForm.niche || null,
        subNiche: variantForm.subNiche || null,
        skipApi: false,
        openaiHd: variantForm.openaiHd || false,
        gptQuality: variantForm.gptQuality || "medium",
        promptHint: variantForm.promptHint || "",
        mascotExpression: variantForm.mascotExpression || "random",
        mascotMatchColorway: variantForm.mascotMatchColorway || false,
      };
      const result = await api.variant(payload);
      setVariantForm(null);
      setGenModal({
        jobId: result.jobId,
        phase: "generating",
        output: "",
        status: "queued",
        generatedFiles: [],
        designType: payload.designType,
        showLog: true,
        approvedFiles: {},
      });
    } catch (err) {
      setError(err.message);
    }
  };

  const getJobErrorSummary = (output) => {
    if (!output) {
      return "";
    }

    const firstLine = output
      .split("\n")
      .map((line) => line.trim())
      .find((line) => line.length > 0);

    return firstLine || "No output captured";
  };

  const updateApproval = async (designType, filename, approved) => {
    setError("");
    try {
      await api.approve({ designType, filename, approved });
      await loadAll(true);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCreateExpense = async (e) => {
    e.preventDefault();
    setError("");
    try {
      const payload = {
        ...expenseForm,
        amount: Number(expenseForm.amount || 0),
      };

      if (editingExpenseId) {
        await api.updateExpense(editingExpenseId, payload);
      } else {
        await api.createExpense(payload);
      }

      setEditingExpenseId("");
      setExpenseForm(initialExpense);
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const startEditExpense = (expense) => {
    setEditingExpenseId(expense.expenseId);
    setExpenseForm({
      date: String(expense.date || "").slice(0, 10),
      front: expense.front || "BOTH",
      category: expense.category || "",
      description: expense.description || "",
      amount: String(expense.amount ?? ""),
      taxDeductible: expense.taxDeductible || "Yes",
      receipt: expense.receipt || "No",
      notes: expense.notes || "",
    });
    setTab("Expenses");
  };

  const handleDeleteExpense = async (expenseId) => {
    setError("");
    try {
      await api.deleteExpense(expenseId);
      await loadAll();
    } catch (err) {
      setError(err.message);
    }
  };

  const openImageModal = (items, selectedItem) => {
    const modalItems = items
      .filter((item) => item.location !== "missing")
      .map((item) => ({
        designType: item.designType,
        filename: item.filename,
        src: api.designImageUrl(item.designType, item.filename),
        alt: item.filename,
      }));

    const selectedIndex = modalItems.findIndex(
      (item) =>
        item.designType === selectedItem.designType &&
        item.filename === selectedItem.filename,
    );

    if (selectedIndex < 0) {
      return;
    }

    setModalState({
      items: modalItems,
      index: selectedIndex,
    });
  };

  const closeImageModal = () => {
    setModalState(null);
  };

  const navigateModal = (direction) => {
    setModalState((current) => {
      if (!current || current.items.length === 0) {
        return current;
      }

      const nextIndex =
        (current.index + direction + current.items.length) %
        current.items.length;

      return { ...current, index: nextIndex };
    });
  };

  useEffect(() => {
    if (!modalState) {
      return;
    }

    const onKeyDown = (event) => {
      if (event.key === "Escape") {
        closeImageModal();
      }

      if (event.key === "ArrowRight") {
        event.preventDefault();
        navigateModal(1);
      }

      if (event.key === "ArrowLeft") {
        event.preventDefault();
        navigateModal(-1);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [modalState]);

  // Gen modal polling
  useEffect(() => {
    if (!genModal || genModal.phase !== "generating") return;
    let cancelled = false;
    const poll = async () => {
      try {
        const data = await api.job(genModal.jobId);
        if (cancelled) return;
        const terminal = data.status === "success" || data.status === "failed";
        setGenModal((prev) => {
          if (!prev || prev.jobId !== data.id) return prev;
          return {
            ...prev,
            output: data.output || "",
            status: data.status,
            generatedFiles: data.generated_files || [],
            phase: terminal
              ? data.status === "success"
                ? "complete"
                : "failed"
              : "generating",
          };
        });
        if (terminal) loadAll(true);
      } catch {
        // ignore poll errors
      }
    };
    poll();
    const timer = setInterval(poll, 2000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [genModal?.jobId, genModal?.phase, loadAll]);

  // Auto-scroll gen modal log
  useEffect(() => {
    if (genModalLogRef.current) {
      genModalLogRef.current.scrollTop = genModalLogRef.current.scrollHeight;
    }
  }, [genModal?.output]);

  const handleModalApproval = async (designType, filename, approved) => {
    try {
      await api.approve({ designType, filename, approved });
      setGenModal((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          approvedFiles: { ...prev.approvedFiles, [filename]: approved },
        };
      });
      loadAll(true);
    } catch (err) {
      setError(err.message);
    }
  };

  const closeGenModal = () => {
    setGenModal(null);
    loadAll(true);
  };

  // Escape key for gen modal
  useEffect(() => {
    if (!genModal) return;
    const onKey = (e) => {
      if (e.key === "Escape") closeGenModal();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [genModal]);

  const modalImage = modalState
    ? modalState.items[modalState.index] || null
    : null;

  const handleTabSelect = (item) => {
    setTab(item);
    setMobileNavOpen(false);
  };

  return (
    <div className="app">
      {mobileNavOpen && (
        <button
          type="button"
          className="mobile-nav-backdrop"
          aria-label="Close navigation"
          onClick={() => setMobileNavOpen(false)}
        />
      )}

      <aside className={`sidebar ${mobileNavOpen ? "open" : ""}`}>
        <div className="brand">POD Control Center</div>
        {NAV_ITEMS.map((item) => (
          <button
            key={item}
            className={`nav-item ${tab === item ? "active" : ""}`}
            onClick={() => handleTabSelect(item)}
          >
            {item}
          </button>
        ))}
      </aside>
      <main className="main">
        <div className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="mobile-nav-toggle"
              aria-label="Open navigation"
              onClick={() => setMobileNavOpen(true)}
            >
              ☰
            </button>
            <h1 style={{ margin: 0 }}>{tab}</h1>
          </div>
          <div className="row">
            <button onClick={loadAll}>Refresh</button>
            {loading && <span>Loading...</span>}
          </div>
        </div>

        {error && (
          <div
            className="card"
            style={{ borderColor: "#ef4444", marginBottom: 12 }}
          >
            <strong>Error:</strong> {error}
          </div>
        )}

        {tab === "Dashboard" && (
          <>
            <div className="grid-4">
              <div className="card">
                <h3>Sneaker Total</h3>
                <div className="value">
                  {summary?.designs?.sneaker?.total ?? "-"}
                </div>
              </div>
              <div className="card">
                <h3>Fitness Total</h3>
                <div className="value">
                  {summary?.designs?.general?.total ?? "-"}
                </div>
              </div>
              <div className="card">
                <h3>Expenses</h3>
                <div className="value">${summary?.expenses?.total ?? "-"}</div>
              </div>
              <div className="card">
                <h3>Jobs</h3>
                <div className="value">
                  {Object.values(summary?.jobs || {}).reduce(
                    (a, b) => a + b,
                    0,
                  )}
                </div>
              </div>
            </div>
            <div className="card">
              <h3 className="section-title">Design Buckets</h3>
              <div className="row">
                <span>
                  Sneaker: G {summary?.designs?.sneaker?.generated ?? 0} / A{" "}
                  {summary?.designs?.sneaker?.approved ?? 0} / R{" "}
                  {summary?.designs?.sneaker?.rejected ?? 0}
                </span>
                <span>
                  Fitness: G {summary?.designs?.general?.generated ?? 0} / A{" "}
                  {summary?.designs?.general?.approved ?? 0} / R{" "}
                  {summary?.designs?.general?.rejected ?? 0}
                </span>
              </div>
            </div>
          </>
        )}

        {tab === "Designs" && (
          <>
            <div className="sub-tabs">
              {[
                { id: "pipeline", label: "Pipeline" },
                { id: "approved", label: "Approved" },
                { id: "published", label: "Published" },
                { id: "rejected", label: "Rejected" },
              ].map((t) => (
                <button
                  key={t.id}
                  className={`sub-tab${designSubTab === t.id ? " active" : ""}`}
                  onClick={() => setDesignSubTab(t.id)}
                >
                  {t.label}
                  <span className="sub-tab-count">
                    {
                      designs.filter((d) => {
                        if (
                          designFilters.designType &&
                          d.designType !== designFilters.designType
                        )
                          return false;
                        if (t.id === "pipeline")
                          return d.location === "generated";
                        if (t.id === "approved")
                          return (
                            d.location === "approved" && !d.printifyProductId
                          );
                        if (t.id === "published") return !!d.printifyProductId;
                        if (t.id === "rejected")
                          return d.location === "rejected";
                        return false;
                      }).length
                    }
                  </span>
                </button>
              ))}
              <select
                value={designFilters.designType}
                onChange={(e) =>
                  setDesignFilters((old) => ({
                    ...old,
                    designType: e.target.value,
                  }))
                }
                style={{ marginLeft: "auto" }}
              >
                <option value="">All Types</option>
                <option value="sneaker">Sneaker</option>
                <option value="general">Fitness</option>
              </select>
            </div>
            <div className="table-wrap">
              <table className="designs-table">
                <thead>
                  <tr>
                    <th>Preview</th>
                    <th>Filename</th>
                    <th>Created</th>
                    <th>Type</th>
                    <th>Name/Phrase</th>
                    <th>Colorway</th>
                    <th>Model</th>
                    <th>Location</th>
                    <th>Status</th>
                    <th>Printify</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDesigns.map((item) => (
                    <tr key={`${item.designType}-${item.filename}`}>
                      <td className="thumb-cell">
                        {item.location !== "missing" ? (
                          <button
                            type="button"
                            className="thumb-button"
                            onClick={() =>
                              openImageModal(filteredDesigns, item)
                            }
                          >
                            <img
                              className="design-thumb"
                              src={api.designImageUrl(
                                item.designType,
                                item.filename,
                              )}
                              alt={item.filename}
                              loading="lazy"
                              onError={(event) => {
                                event.currentTarget.style.display = "none";
                              }}
                            />
                          </button>
                        ) : (
                          <span className="thumb-empty">No image</span>
                        )}
                      </td>
                      <td>
                        {item.filename}
                        {item.legacy ? (
                          <span className="badge legacy">Legacy</span>
                        ) : (
                          <span className="badge new-gen">New</span>
                        )}
                      </td>
                      <td className="date-cell">{item.createdAt || "-"}</td>
                      <td>{item.designType}</td>
                      <td>{item.name || item.phrase || "-"}</td>
                      <td>{item.colorway || "-"}</td>
                      <td>{item.generationModel || "-"}</td>
                      <td>
                        <span className={`badge ${statusClass(item.location)}`}>
                          {item.location}
                        </span>
                      </td>
                      <td>{item.status || "-"}</td>
                      <td>
                        {item.printifyProductId ? (
                          <div className="link-stack">
                            <span className="badge approved">Published</span>
                            {item.printifyUrl && (
                              <a
                                href={item.printifyUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="table-link"
                              >
                                Printify
                              </a>
                            )}
                            {item.etsyUrl ? (
                              <a
                                href={item.etsyUrl}
                                target="_blank"
                                rel="noreferrer"
                                className="table-link"
                              >
                                Etsy
                              </a>
                            ) : (
                              <span className="table-note">Etsy pending</span>
                            )}
                          </div>
                        ) : item.location === "approved" ? (
                          <span className="badge generated">Ready</span>
                        ) : (
                          "-"
                        )}
                      </td>
                      <td className="row">
                        {item.location !== "approved" && (
                          <button
                            className="primary"
                            onClick={() =>
                              updateApproval(
                                item.designType,
                                item.filename,
                                true,
                              )
                            }
                          >
                            Approve
                          </button>
                        )}
                        {item.location !== "rejected" && (
                          <button
                            className="danger"
                            onClick={() =>
                              updateApproval(
                                item.designType,
                                item.filename,
                                false,
                              )
                            }
                          >
                            Reject
                          </button>
                        )}
                        {item.location === "approved" &&
                          (providerStatus.printify.configured ||
                            providerStatus.printful.configured) && (
                            <>
                              <select
                                value={
                                  selectedProviderByFile[item.filename] ||
                                  (providerStatus.printify.configured
                                    ? "printify"
                                    : "printful")
                                }
                                onChange={(e) =>
                                  setSelectedProviderByFile((old) => ({
                                    ...old,
                                    [item.filename]: e.target.value,
                                  }))
                                }
                              >
                                <option
                                  value="printify"
                                  disabled={!providerStatus.printify.configured}
                                >
                                  Printify (US)
                                </option>
                                <option
                                  value="printful"
                                  disabled={!providerStatus.printful.configured}
                                >
                                  Printful (EU)
                                </option>
                              </select>
                              <button
                                className="primary"
                                disabled={
                                  uploadingDesign ===
                                  `${item.filename}:${
                                    selectedProviderByFile[item.filename] ||
                                    (providerStatus.printify.configured
                                      ? "printify"
                                      : "printful")
                                  }:tshirt`
                                }
                                onClick={() =>
                                  handlePrintifyUpload(
                                    item.designType,
                                    item.filename,
                                    "tshirt",
                                    selectedProviderByFile[item.filename] ||
                                      (providerStatus.printify.configured
                                        ? "printify"
                                        : "printful"),
                                  )
                                }
                              >
                                {uploadingDesign ===
                                `${item.filename}:${
                                  selectedProviderByFile[item.filename] ||
                                  (providerStatus.printify.configured
                                    ? "printify"
                                    : "printful")
                                }:tshirt`
                                  ? "Uploading Tee..."
                                  : "Upload T-Shirt"}
                              </button>
                              <button
                                disabled={
                                  uploadingDesign ===
                                  `${item.filename}:${
                                    selectedProviderByFile[item.filename] ||
                                    (providerStatus.printify.configured
                                      ? "printify"
                                      : "printful")
                                  }:hoodie`
                                }
                                onClick={() =>
                                  handlePrintifyUpload(
                                    item.designType,
                                    item.filename,
                                    "hoodie",
                                    selectedProviderByFile[item.filename] ||
                                      (providerStatus.printify.configured
                                        ? "printify"
                                        : "printful"),
                                  )
                                }
                              >
                                {uploadingDesign ===
                                `${item.filename}:${
                                  selectedProviderByFile[item.filename] ||
                                  (providerStatus.printify.configured
                                    ? "printify"
                                    : "printful")
                                }:hoodie`
                                  ? "Uploading Hoodie..."
                                  : "Upload Hoodie"}
                              </button>
                            </>
                          )}
                        <button
                          onClick={() =>
                            setVariantForm({
                              designType: item.designType,
                              designName:
                                item.name ||
                                item.phrase ||
                                item.filename
                                  .replace(/\.png$/, "")
                                  .replace(/_\d{3}$/, ""),
                              phrase: item.phrase || "",
                              niche: "",
                              subNiche: "",
                              palette: "1",
                              visualMode: "text_only",
                              phraseVisibilityMode: "balanced",
                            })
                          }
                        >
                          Variant
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {variantForm && (
              <form
                className="card"
                style={{ marginTop: 12 }}
                onSubmit={handleVariant}
              >
                <h3 className="section-title">
                  Colorway Variant: {variantForm.designName}
                </h3>
                <div className="form-grid">
                  <select
                    value={variantForm.palette}
                    onChange={(e) =>
                      setVariantForm((old) => ({
                        ...old,
                        palette: e.target.value,
                      }))
                    }
                  >
                    {renderPaletteOptions()}
                  </select>
                  <select
                    value={variantForm.visualMode}
                    onChange={(e) =>
                      setVariantForm((old) => ({
                        ...old,
                        visualMode: e.target.value,
                      }))
                    }
                  >
                    <option value="text_only">Text Design (Ideogram)</option>
                    <option value="graphic_text">
                      Graphic + Text (HuggingFace + Ideogram)
                    </option>
                    <option value="graphic_only">
                      Graphic Only (HuggingFace)
                    </option>
                    <option value="text_only_openai">
                      Graphic + Text (OpenAI DALL-E 3)
                    </option>
                    <option value="graphic_openai">
                      Graphic Only (OpenAI, no text)
                    </option>
                    <option value="text_gpt_image">
                      Graphic + Text (GPT Image 1)
                    </option>
                    <option value="graphic_gpt_image">
                      Graphic Only (GPT Image 1, no text)
                    </option>
                  </select>
                  <select
                    value={variantForm.phraseVisibilityMode || "balanced"}
                    onChange={(e) =>
                      setVariantForm((old) => ({
                        ...old,
                        phraseVisibilityMode: e.target.value,
                      }))
                    }
                  >
                    <option value="strict">
                      Phrase visibility: Strict (100%)
                    </option>
                    <option value="balanced">
                      Phrase visibility: Balanced (90%)
                    </option>
                    <option value="flexible">
                      Phrase visibility: Flexible (80%)
                    </option>
                  </select>
                  {variantForm.visualMode.includes("openai") && (
                    <label className="row">
                      <input
                        type="checkbox"
                        checked={variantForm.openaiHd || false}
                        onChange={(e) =>
                          setVariantForm((old) => ({
                            ...old,
                            openaiHd: e.target.checked,
                          }))
                        }
                      />
                      HD quality (~$0.08/image instead of ~$0.04)
                    </label>
                  )}
                  {variantForm.visualMode.includes("gpt_image") && (
                    <select
                      value={variantForm.gptQuality || "medium"}
                      onChange={(e) =>
                        setVariantForm((old) => ({
                          ...old,
                          gptQuality: e.target.value,
                        }))
                      }
                    >
                      <option value="low">Low quality (~$0.02/image)</option>
                      <option value="medium">
                        Medium quality (~$0.06/image)
                      </option>
                      <option value="high">High quality (~$0.26/image)</option>
                    </select>
                  )}
                  <input
                    type="text"
                    placeholder="Style hint (e.g. 'make it flashy', 'retro vibe')"
                    value={variantForm.promptHint || ""}
                    onChange={(e) =>
                      setVariantForm((old) => ({
                        ...old,
                        promptHint: e.target.value,
                      }))
                    }
                  />
                </div>
                <div className="row" style={{ marginTop: 12 }}>
                  <button className="primary" type="submit">
                    Generate Variant
                  </button>
                  <button type="button" onClick={() => setVariantForm(null)}>
                    Cancel
                  </button>
                </div>
              </form>
            )}
          </>
        )}

        {tab === "Generate" && (
          <form className="card" onSubmit={handleGenerate}>
            <h3 className="section-title">Generate New Designs</h3>
            <div className="form-grid">
              <select
                value={generationForm.designType}
                onChange={(e) =>
                  setGenerationForm((old) => ({
                    ...old,
                    designType: e.target.value,
                  }))
                }
              >
                <option value="sneaker">Sneaker Culture (Front A)</option>
                <option value="general">Functional Fitness (Front B)</option>
              </select>

              <select
                value={generationForm.visualMode}
                onChange={(e) =>
                  setGenerationForm((old) => ({
                    ...old,
                    visualMode: e.target.value,
                  }))
                }
              >
                <option value="random">Random (mix of all types)</option>
                <option value="text_only">Text Design (Ideogram)</option>
                <option value="graphic_text">
                  Graphic + Text (HuggingFace + Ideogram)
                </option>
                <option value="graphic_only">
                  Graphic Only (HuggingFace, no text)
                </option>
                <option value="text_only_openai">
                  Graphic + Text (OpenAI DALL-E 3)
                </option>
                <option value="graphic_openai">
                  Graphic Only (OpenAI, no text)
                </option>
                <option value="text_gpt_image">
                  Graphic + Text (GPT Image 1)
                </option>
                <option value="graphic_gpt_image">
                  Graphic Only (GPT Image 1, no text)
                </option>
                <option value="mascot_gpt_image">
                  Mascot Character + Text (GPT Image 1)
                </option>
              </select>

              <div className="hint-box">
                {VISUAL_MODE_HINTS[generationForm.visualMode]}
              </div>

              {generationForm.visualMode.includes("openai") && (
                <label className="row">
                  <input
                    type="checkbox"
                    checked={generationForm.openaiHd}
                    onChange={(e) =>
                      setGenerationForm((old) => ({
                        ...old,
                        openaiHd: e.target.checked,
                      }))
                    }
                  />
                  HD quality (~$0.08/image instead of ~$0.04)
                </label>
              )}

              {generationForm.visualMode.includes("gpt_image") && (
                <select
                  value={generationForm.gptQuality}
                  onChange={(e) =>
                    setGenerationForm((old) => ({
                      ...old,
                      gptQuality: e.target.value,
                    }))
                  }
                >
                  <option value="low">Low quality (~$0.02/image)</option>
                  <option value="medium">Medium quality (~$0.06/image)</option>
                  <option value="high">High quality (~$0.26/image)</option>
                </select>
              )}

              {generationForm.visualMode === "mascot_gpt_image" && (
                <select
                  value={generationForm.mascotExpression}
                  onChange={(e) =>
                    setGenerationForm((old) => ({
                      ...old,
                      mascotExpression: e.target.value,
                    }))
                  }
                >
                  <option value="random">Random expression</option>
                  <option value="stern">Stern</option>
                  <option value="happy">Happy</option>
                  <option value="surprised">Surprised</option>
                  <option value="laughing">Laughing</option>
                  <option value="annoyed">Annoyed</option>
                  <option value="thinking">Thinking</option>
                  <option value="wink">Wink</option>
                  <option value="nervous">Nervous</option>
                  <option value="huh">Huh?</option>
                  <option value="sleepy">Sleepy</option>
                  <option value="shocked">Shocked / Gasp</option>
                  <option value="calm">Calm</option>
                </select>
              )}

              {generationForm.visualMode === "mascot_gpt_image" && (
                <label className="row">
                  <input
                    type="checkbox"
                    checked={generationForm.mascotMatchColorway}
                    onChange={(e) =>
                      setGenerationForm((old) => ({
                        ...old,
                        mascotMatchColorway: e.target.checked,
                      }))
                    }
                  />
                  Match garment colors to colorway palette
                </label>
              )}

              <input
                type="text"
                placeholder="Style hint (e.g. 'make it flashy', 'retro vibe')"
                value={generationForm.promptHint}
                onChange={(e) =>
                  setGenerationForm((old) => ({
                    ...old,
                    promptHint: e.target.value,
                  }))
                }
              />

              <select
                value={generationForm.palette}
                onChange={(e) =>
                  setGenerationForm((old) => ({
                    ...old,
                    palette: e.target.value,
                  }))
                }
              >
                {renderPaletteOptions()}
              </select>

              <div className="hint-text">
                Selected colorway is fixed for the generation job. Only
                <strong> Visual Mode </strong>
                changes when set to Random.
              </div>

              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <select
                  value={
                    COUNT_OPTIONS.some((c) => c.value === generationForm.count)
                      ? generationForm.count
                      : "custom"
                  }
                  onChange={(e) => {
                    const v = e.target.value;
                    setGenerationForm((old) => ({
                      ...old,
                      count:
                        v === "custom"
                          ? old.count === "0"
                            ? ""
                            : old.count
                          : v,
                    }));
                  }}
                >
                  {COUNT_OPTIONS.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
                {!COUNT_OPTIONS.some(
                  (c) => c.value === generationForm.count,
                ) && (
                  <input
                    type="number"
                    min="1"
                    max="100"
                    placeholder="Amount"
                    value={generationForm.count}
                    onChange={(e) =>
                      setGenerationForm((old) => ({
                        ...old,
                        count: e.target.value,
                      }))
                    }
                    style={{ width: 90 }}
                  />
                )}
              </div>

              {generationForm.designType === "sneaker" && (
                <select
                  value={generationForm.dropId}
                  onChange={(e) =>
                    setGenerationForm((old) => ({
                      ...old,
                      dropId: e.target.value,
                    }))
                  }
                >
                  <option value="">Default Drop (DROP-01)</option>
                  {(generationOptions.sneaker?.dropIds || []).map((drop) => (
                    <option key={drop} value={drop}>
                      {drop}
                    </option>
                  ))}
                </select>
              )}

              {generationForm.designType === "general" && (
                <>
                  <select
                    value=""
                    onChange={(e) => {
                      if (!e.target.value) {
                        return;
                      }
                      setGenerationForm((old) => ({
                        ...old,
                        phrase: e.target.value,
                      }));
                    }}
                  >
                    <option value="">Pick a suggested phrase</option>
                    {(generationOptions.general?.phrases || []).map(
                      (phrase) => (
                        <option key={phrase} value={phrase}>
                          {phrase}
                        </option>
                      ),
                    )}
                  </select>
                  <input
                    placeholder="Phrase (leave empty for auto-generated batch)"
                    value={generationForm.phrase}
                    onChange={(e) =>
                      setGenerationForm((old) => ({
                        ...old,
                        phrase: e.target.value,
                      }))
                    }
                  />
                </>
              )}

              <label className="row">
                <input
                  type="checkbox"
                  checked={generationForm.skipApi}
                  onChange={(e) =>
                    setGenerationForm((old) => ({
                      ...old,
                      skipApi: e.target.checked,
                    }))
                  }
                />
                Skip USPTO API
              </label>
            </div>
            <div style={{ marginTop: 12 }}>
              <button className="primary" type="submit">
                Generate
              </button>
            </div>
          </form>
        )}

        {tab === "Prepare" && <PrepareTab />}

        {tab === "Expenses" && (
          <>
            <form className="card" onSubmit={handleCreateExpense}>
              <h3 className="section-title">Add Expense</h3>
              <div className="form-grid">
                <input
                  type="date"
                  value={expenseForm.date}
                  onChange={(e) =>
                    setExpenseForm((old) => ({ ...old, date: e.target.value }))
                  }
                />
                <select
                  value={expenseForm.front}
                  onChange={(e) =>
                    setExpenseForm((old) => ({ ...old, front: e.target.value }))
                  }
                >
                  <option value="A">A</option>
                  <option value="B">B</option>
                  <option value="BOTH">BOTH</option>
                </select>
                <input
                  placeholder="Category"
                  value={expenseForm.category}
                  onChange={(e) =>
                    setExpenseForm((old) => ({
                      ...old,
                      category: e.target.value,
                    }))
                  }
                />
                <input
                  placeholder="Description"
                  value={expenseForm.description}
                  onChange={(e) =>
                    setExpenseForm((old) => ({
                      ...old,
                      description: e.target.value,
                    }))
                  }
                />
                <input
                  type="number"
                  step="0.01"
                  placeholder="Amount"
                  value={expenseForm.amount}
                  onChange={(e) =>
                    setExpenseForm((old) => ({
                      ...old,
                      amount: e.target.value,
                    }))
                  }
                />
                <input
                  placeholder="Notes"
                  value={expenseForm.notes}
                  onChange={(e) =>
                    setExpenseForm((old) => ({ ...old, notes: e.target.value }))
                  }
                />
              </div>
              <div style={{ marginTop: 12 }}>
                <button className="primary" type="submit">
                  {editingExpenseId ? "Update Expense" : "Add Expense"}
                </button>
                {editingExpenseId && (
                  <button
                    type="button"
                    style={{ marginLeft: 8 }}
                    onClick={() => {
                      setEditingExpenseId("");
                      setExpenseForm(initialExpense);
                    }}
                  >
                    Cancel Edit
                  </button>
                )}
              </div>
            </form>
            <div className="card" style={{ marginTop: 12 }}>
              <strong>Total Expenses:</strong> $
              {expenses
                .reduce((a, b) => a + Number(b.amount || 0), 0)
                .toFixed(2)}
            </div>
            <div className="table-wrap">
              <table className="expenses-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Date</th>
                    <th>Front</th>
                    <th>Category</th>
                    <th>Description</th>
                    <th>Amount</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {expenses.map((item) => (
                    <tr key={item.expenseId}>
                      <td>{item.expenseId}</td>
                      <td>{String(item.date || "")}</td>
                      <td>{item.front}</td>
                      <td>{item.category}</td>
                      <td>{item.description}</td>
                      <td>${Number(item.amount || 0).toFixed(2)}</td>
                      <td className="row">
                        <button onClick={() => startEditExpense(item)}>
                          Edit
                        </button>
                        <button
                          className="danger"
                          onClick={() => handleDeleteExpense(item.expenseId)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {tab === "Jobs" && (
          <>
            <div className="table-wrap">
              <table className="jobs-table">
                <thead>
                  <tr>
                    <th>Job ID</th>
                    <th>Type</th>
                    <th>Mode</th>
                    <th>Status</th>
                    <th>Failure Reason</th>
                    <th>Created</th>
                    <th>Started</th>
                    <th>Finished</th>
                    <th>Log</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job) => (
                    <tr key={job.id}>
                      <td>{job.id.slice(0, 8)}</td>
                      <td>{job.design_type}</td>
                      <td>{job.mode}</td>
                      <td>
                        <span className={`badge ${statusClass(job.status)}`}>
                          {job.status}
                        </span>
                      </td>
                      <td>
                        {job.status === "failed"
                          ? getJobErrorSummary(job.output)
                          : "-"}
                      </td>
                      <td>{job.created_at}</td>
                      <td>{job.started_at || "-"}</td>
                      <td>{job.finished_at || "-"}</td>
                      <td>
                        <button
                          type="button"
                          onClick={() => setSelectedJobLog(job)}
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {selectedJobLog && (
              <div className="card" style={{ marginTop: 12 }}>
                <h3 className="section-title">
                  Job Log: {selectedJobLog.id.slice(0, 8)} (
                  {selectedJobLog.status})
                </h3>
                <pre className="job-log">
                  {selectedJobLog.output || "No output captured"}
                </pre>
              </div>
            )}
          </>
        )}

        {tab === "Etsy" && <EtsySetup />}
        {tab === "Setup" && <KeysSetup onSaved={refreshProviderStatus} />}
        {tab === "Pinterest" && <PinterestTab />}

        {genModal && (
          <div className="image-modal-overlay" onClick={closeGenModal}>
            <div
              className="gen-modal-content"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="gen-modal-header">
                <h3 style={{ margin: 0 }}>
                  {genModal.phase === "generating"
                    ? "Generating..."
                    : genModal.phase === "complete"
                      ? "Generation Complete"
                      : "Generation Failed"}
                </h3>
                <div className="row" style={{ gap: 8 }}>
                  <span
                    className={`badge ${genModal.status === "success" ? "approved" : genModal.status === "failed" ? "rejected" : "generated"}`}
                  >
                    {genModal.status}
                  </span>
                  {genModal.phase === "generating" && (
                    <span className="spinner" />
                  )}
                  <button type="button" onClick={closeGenModal}>
                    Close
                  </button>
                </div>
              </div>

              {(genModal.phase === "generating" || genModal.showLog) && (
                <pre className="gen-modal-log" ref={genModalLogRef}>
                  {genModal.output || "Waiting for output..."}
                </pre>
              )}

              {genModal.phase === "complete" && !genModal.showLog && (
                <button
                  type="button"
                  style={{ marginBottom: 12, fontSize: 13 }}
                  onClick={() =>
                    setGenModal((prev) =>
                      prev ? { ...prev, showLog: true } : prev,
                    )
                  }
                >
                  Show Log
                </button>
              )}

              {genModal.phase === "complete" &&
                genModal.showLog &&
                genModal.generatedFiles.length > 0 && (
                  <button
                    type="button"
                    style={{ marginBottom: 12, fontSize: 13 }}
                    onClick={() =>
                      setGenModal((prev) =>
                        prev ? { ...prev, showLog: false } : prev,
                      )
                    }
                  >
                    Hide Log
                  </button>
                )}

              {genModal.phase === "complete" &&
                genModal.generatedFiles.length === 1 && (
                  <div className="gen-modal-single">
                    <img
                      src={api.designImageUrl(
                        genModal.designType,
                        genModal.generatedFiles[0],
                      )}
                      alt={genModal.generatedFiles[0]}
                      className="gen-modal-single-img"
                      onError={(e) => {
                        e.currentTarget.style.display = "none";
                      }}
                    />
                    <div className="gen-modal-actions">
                      <button
                        className={`primary ${genModal.approvedFiles[genModal.generatedFiles[0]] === true ? "gen-modal-selected" : ""}`}
                        onClick={() =>
                          handleModalApproval(
                            genModal.designType,
                            genModal.generatedFiles[0],
                            true,
                          )
                        }
                      >
                        Approve
                      </button>
                      <button
                        className={`danger ${genModal.approvedFiles[genModal.generatedFiles[0]] === false ? "gen-modal-selected" : ""}`}
                        onClick={() =>
                          handleModalApproval(
                            genModal.designType,
                            genModal.generatedFiles[0],
                            false,
                          )
                        }
                      >
                        Reject
                      </button>
                    </div>
                  </div>
                )}

              {genModal.phase === "complete" &&
                genModal.generatedFiles.length > 1 && (
                  <div className="gen-modal-grid">
                    {genModal.generatedFiles.map((filename) => {
                      const state = genModal.approvedFiles[filename];
                      const borderClass =
                        state === true
                          ? "gen-card-approved"
                          : state === false
                            ? "gen-card-rejected"
                            : "";
                      return (
                        <div
                          key={filename}
                          className={`gen-modal-card ${borderClass}`}
                        >
                          <img
                            src={api.designImageUrl(
                              genModal.designType,
                              filename,
                            )}
                            alt={filename}
                            className="gen-modal-card-img"
                            onError={(e) => {
                              e.currentTarget.style.display = "none";
                            }}
                          />
                          <div className="gen-modal-card-name">{filename}</div>
                          <div className="gen-modal-actions">
                            <button
                              className={`primary ${state === true ? "gen-modal-selected" : ""}`}
                              onClick={() =>
                                handleModalApproval(
                                  genModal.designType,
                                  filename,
                                  true,
                                )
                              }
                            >
                              Approve
                            </button>
                            <button
                              className={`danger ${state === false ? "gen-modal-selected" : ""}`}
                              onClick={() =>
                                handleModalApproval(
                                  genModal.designType,
                                  filename,
                                  false,
                                )
                              }
                            >
                              Reject
                            </button>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
            </div>
          </div>
        )}

        {modalImage && (
          <div className="image-modal-overlay" onClick={closeImageModal}>
            <div
              className="image-modal-content"
              onClick={(event) => event.stopPropagation()}
            >
              {modalState && modalState.items.length > 1 && (
                <>
                  <button
                    type="button"
                    className="image-modal-nav left"
                    onClick={() => navigateModal(-1)}
                  >
                    ◀
                  </button>
                  <button
                    type="button"
                    className="image-modal-nav right"
                    onClick={() => navigateModal(1)}
                  >
                    ▶
                  </button>
                </>
              )}
              <button
                type="button"
                className="image-modal-close"
                onClick={closeImageModal}
              >
                Close
              </button>
              {modalState && (
                <div className="image-modal-counter">
                  {modalState.index + 1} / {modalState.items.length}
                </div>
              )}

              <select
                value={generationForm.phraseVisibilityMode}
                onChange={(e) =>
                  setGenerationForm((old) => ({
                    ...old,
                    phraseVisibilityMode: e.target.value,
                  }))
                }
              >
                <option value="strict">Phrase visibility: Strict (100%)</option>
                <option value="balanced">
                  Phrase visibility: Balanced (90%)
                </option>
                <option value="flexible">
                  Phrase visibility: Flexible (80%)
                </option>
              </select>
              <img
                src={modalImage.src}
                alt={modalImage.alt}
                className="image-modal-preview"
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
