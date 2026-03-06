import { useEffect, useMemo, useState } from "react";
import { api } from "./api";

const NAV_ITEMS = [
  "Dashboard",
  "Designs",
  "Generate",
  "Approvals",
  "Expenses",
  "Jobs",
];

const initialGeneration = {
  generationStyle: "random",
  mode: "single",
  designType: "general",
  randomVisualMode: "mixed",
  dropId: "",
  phrase: "",
  niche: "",
  subNiche: "",
  style: "",
  render: "",
  skipApi: false,
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
  const [modalState, setModalState] = useState(null);
  const [selectedJobLog, setSelectedJobLog] = useState(null);
  const [generationOptions, setGenerationOptions] = useState({
    sneaker: { dropIds: [] },
    general: { niches: [], subNiches: [], styles: [], phrases: [] },
    renderers: ["hf", "ideogram", "leonardo"],
  });

  const loadAll = async () => {
    setLoading(true);
    setError("");
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
      setGenerationOptions(generationOptionsRes || generationOptions);
    } catch (err) {
      setError(err.message || "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, []);

  const filteredDesigns = useMemo(() => {
    return designs.filter((item) => {
      if (
        designFilters.designType &&
        item.designType !== designFilters.designType
      )
        return false;
      if (
        designFilters.status !== "all" &&
        item.location !== designFilters.status
      )
        return false;
      return true;
    });
  }, [designs, designFilters]);

  const handleGenerate = async (e) => {
    e.preventDefault();
    setError("");
    try {
      if (
        generationForm.generationStyle === "detailed" &&
        generationForm.mode === "single" &&
        generationForm.designType === "general" &&
        !generationForm.phrase.trim()
      ) {
        setError("Single general generation requires a phrase.");
        return;
      }

      const payload = {
        ...generationForm,
        render: generationForm.render || null,
        dropId: generationForm.dropId || null,
        phrase: generationForm.phrase || null,
        niche: generationForm.niche || null,
        subNiche: generationForm.subNiche || null,
        style: generationForm.style || null,
      };
      await api.generate(payload);
      setSelectedJobLog(null);
      setTab("Jobs");
      await loadAll();
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
      await loadAll();
      setTab("Approvals");
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

  const modalImage = modalState
    ? modalState.items[modalState.index] || null
    : null;

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">POD Control Center</div>
        {NAV_ITEMS.map((item) => (
          <button
            key={item}
            className={`nav-item ${tab === item ? "active" : ""}`}
            onClick={() => setTab(item)}
          >
            {item}
          </button>
        ))}
      </aside>
      <main className="main">
        <div className="topbar">
          <h1 style={{ margin: 0 }}>{tab}</h1>
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
                <h3>General Total</h3>
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
                  General: G {summary?.designs?.general?.generated ?? 0} / A{" "}
                  {summary?.designs?.general?.approved ?? 0} / R{" "}
                  {summary?.designs?.general?.rejected ?? 0}
                </span>
              </div>
            </div>
          </>
        )}

        {tab === "Designs" && (
          <>
            <div className="row">
              <select
                value={designFilters.designType}
                onChange={(e) =>
                  setDesignFilters((old) => ({
                    ...old,
                    designType: e.target.value,
                  }))
                }
              >
                <option value="">All Types</option>
                <option value="sneaker">Sneaker</option>
                <option value="general">General</option>
              </select>
              <select
                value={designFilters.status}
                onChange={(e) =>
                  setDesignFilters((old) => ({
                    ...old,
                    status: e.target.value,
                  }))
                }
              >
                <option value="all">All Status</option>
                <option value="generated">Generated</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Preview</th>
                    <th>Filename</th>
                    <th>Type</th>
                    <th>Name/Phrase</th>
                    <th>IP Risk</th>
                    <th>Location</th>
                    <th>Status</th>
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
                      <td>{item.filename}</td>
                      <td>{item.designType}</td>
                      <td>{item.name || item.phrase || "-"}</td>
                      <td>{item.ipRisk || "-"}</td>
                      <td>
                        <span className={`badge ${statusClass(item.location)}`}>
                          {item.location}
                        </span>
                      </td>
                      <td>{item.status || "-"}</td>
                      <td className="row">
                        <button
                          className="primary"
                          onClick={() =>
                            updateApproval(item.designType, item.filename, true)
                          }
                        >
                          Approve
                        </button>
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
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {tab === "Generate" && (
          <form className="card" onSubmit={handleGenerate}>
            <h3 className="section-title">Trigger Generation</h3>
            <div className="form-grid">
              <select
                value={generationForm.generationStyle}
                onChange={(e) =>
                  setGenerationForm((old) => ({
                    ...old,
                    generationStyle: e.target.value,
                  }))
                }
              >
                <option value="random">Random Generator</option>
                <option value="detailed">Detailed Setup</option>
              </select>
              <select
                value={generationForm.mode}
                onChange={(e) =>
                  setGenerationForm((old) => ({ ...old, mode: e.target.value }))
                }
              >
                <option value="single">Single</option>
                <option value="batch">Batch</option>
              </select>
              <select
                value={generationForm.designType}
                onChange={(e) =>
                  setGenerationForm((old) => ({
                    ...old,
                    designType: e.target.value,
                  }))
                }
              >
                <option value="general">General</option>
                <option value="sneaker">Sneaker</option>
              </select>

              {generationForm.generationStyle === "random" && (
                <select
                  value={generationForm.randomVisualMode}
                  onChange={(e) =>
                    setGenerationForm((old) => ({
                      ...old,
                      randomVisualMode: e.target.value,
                    }))
                  }
                >
                  <option value="mixed">Mixed (Words + Some Images)</option>
                  <option value="text_only">Words Only</option>
                  <option value="text_plus_image">Words + Image</option>
                </select>
              )}

              {generationForm.generationStyle === "detailed" && (
                <select
                  value={generationForm.render}
                  onChange={(e) =>
                    setGenerationForm((old) => ({
                      ...old,
                      render: e.target.value,
                    }))
                  }
                >
                  <option value="">No Render</option>
                  {(generationOptions.renderers || []).map((renderer) => (
                    <option key={renderer} value={renderer}>
                      {renderer}
                    </option>
                  ))}
                </select>
              )}

              {generationForm.designType === "sneaker" &&
                generationForm.generationStyle === "detailed" && (
                  <select
                    value={generationForm.dropId}
                    onChange={(e) =>
                      setGenerationForm((old) => ({
                        ...old,
                        dropId: e.target.value,
                      }))
                    }
                  >
                    <option value="">Auto / Default Drop</option>
                    {(generationOptions.sneaker?.dropIds || []).map((drop) => (
                      <option key={drop} value={drop}>
                        {drop}
                      </option>
                    ))}
                  </select>
                )}

              {generationForm.designType === "general" &&
                generationForm.generationStyle === "detailed" && (
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
                      placeholder="Custom phrase (required for single)"
                      value={generationForm.phrase}
                      onChange={(e) =>
                        setGenerationForm((old) => ({
                          ...old,
                          phrase: e.target.value,
                        }))
                      }
                    />
                    <select
                      value={generationForm.niche}
                      onChange={(e) =>
                        setGenerationForm((old) => ({
                          ...old,
                          niche: e.target.value,
                        }))
                      }
                    >
                      <option value="">Any Niche</option>
                      {(generationOptions.general?.niches || []).map(
                        (niche) => (
                          <option key={niche} value={niche}>
                            {niche}
                          </option>
                        ),
                      )}
                    </select>
                    <select
                      value={generationForm.subNiche}
                      onChange={(e) =>
                        setGenerationForm((old) => ({
                          ...old,
                          subNiche: e.target.value,
                        }))
                      }
                    >
                      <option value="">Any Sub-Niche</option>
                      {(generationOptions.general?.subNiches || []).map(
                        (subNiche) => (
                          <option key={subNiche} value={subNiche}>
                            {subNiche}
                          </option>
                        ),
                      )}
                    </select>
                    <select
                      value={generationForm.style}
                      onChange={(e) =>
                        setGenerationForm((old) => ({
                          ...old,
                          style: e.target.value,
                        }))
                      }
                    >
                      <option value="">Default Style</option>
                      {(generationOptions.general?.styles || []).map(
                        (style) => (
                          <option key={style} value={style}>
                            {style}
                          </option>
                        ),
                      )}
                    </select>
                  </>
                )}

              {generationForm.generationStyle === "random" && (
                <div className="hint-box">
                  Random mode uses existing phrase pools/themes and auto-picks
                  niche/style/drop.
                </div>
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
                Queue Job
              </button>
            </div>
          </form>
        )}

        {tab === "Approvals" && (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Preview</th>
                  <th>Filename</th>
                  <th>Type</th>
                  <th>Current</th>
                  <th>Spreadsheet Approved?</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {designs.map((item) => (
                  <tr key={`approval-${item.designType}-${item.filename}`}>
                    <td className="thumb-cell">
                      {item.location !== "missing" ? (
                        <button
                          type="button"
                          className="thumb-button"
                          onClick={() => openImageModal(designs, item)}
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
                    <td>{item.filename}</td>
                    <td>{item.designType}</td>
                    <td>{item.location}</td>
                    <td>{item.approved || "-"}</td>
                    <td className="row">
                      <button
                        className="primary"
                        onClick={() =>
                          updateApproval(item.designType, item.filename, true)
                        }
                      >
                        Approve
                      </button>
                      <button
                        className="danger"
                        onClick={() =>
                          updateApproval(item.designType, item.filename, false)
                        }
                      >
                        Reject
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

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
              <table>
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
              <table>
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
