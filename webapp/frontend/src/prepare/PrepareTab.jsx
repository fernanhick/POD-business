import { useState, useEffect, useRef, useCallback } from "react";
import { api } from "../api";

const SUBTABS = [
  { key: "upload", label: "Upload" },
  { key: "processed", label: "Processed" },
  { key: "published", label: "Published" },
];

export default function PrepareTab() {
  const [subtab, setSubtab] = useState("upload");
  const [images, setImages] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [uploading, setUploading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [processJobId, setProcessJobId] = useState(null);
  const [processLog, setProcessLog] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [uploadingPrintify, setUploadingPrintify] = useState(null);
  const [providerByFile, setProviderByFile] = useState({});
  const [providerStatus, setProviderStatus] = useState(null);
  const [previewVersion, setPreviewVersion] = useState({});
  const fileInputRef = useRef(null);

  const loadImages = useCallback(async () => {
    try {
      const data = await api.prepareImages();
      setImages(data.images || []);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  const loadProviderStatus = useCallback(async () => {
    try {
      const data = await api.podProviderStatus();
      setProviderStatus(data);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    loadImages();
    loadProviderStatus();
  }, [loadImages, loadProviderStatus]);

  // Poll processing job
  useEffect(() => {
    if (!processJobId) return;
    const interval = setInterval(async () => {
      try {
        const job = await api.job(processJobId);
        setProcessLog(job.output || "");
        if (job.status === "success" || job.status === "failed") {
          setProcessing(false);
          setProcessJobId(null);
          if (job.status === "success") {
            setSuccess("Processing complete!");
            setSubtab("processed");
          } else {
            setError("Processing failed. Check logs.");
          }
          setSelectedIds(new Set());
          loadImages();
        }
      } catch {
        /* ignore polling errors */
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [processJobId, loadImages]);

  const filterByStatus = (statuses) =>
    images.filter((img) => statuses.includes(img.status));

  // ── Upload handlers ──────────────────────────────────────────
  const handleFiles = async (fileList) => {
    if (!fileList.length) return;
    setUploading(true);
    setError("");
    setSuccess("");
    try {
      const data = await api.prepareUpload(fileList);
      setSuccess(`Uploaded ${data.count} image(s)`);
      await loadImages();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  const onDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  // ── Selection ────────────────────────────────────────────────
  const toggleSelect = (id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectAll = (items) => {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((i) => i.id)));
    }
  };

  // ── Process ──────────────────────────────────────────────────
  const handleProcess = async () => {
    if (!selectedIds.size) return;
    setProcessing(true);
    setProcessLog("");
    setError("");
    setSuccess("");
    try {
      const data = await api.prepareProcess([...selectedIds]);
      setProcessJobId(data.jobId);
    } catch (err) {
      setError(err.message);
      setProcessing(false);
    }
  };

  // ── Delete ───────────────────────────────────────────────────
  const handleDelete = async (ids) => {
    setError("");
    try {
      for (const id of ids) {
        await api.prepareDelete(id);
      }
      setSelectedIds(new Set());
      await loadImages();
    } catch (err) {
      setError(err.message);
    }
  };

  // ── Publish ──────────────────────────────────────────────────
  const handlePublish = async (ids) => {
    setError("");
    setSuccess("");
    try {
      for (const id of ids) {
        await api.preparePublish(id);
      }
      setSuccess(`Published ${ids.length} image(s)`);
      setSelectedIds(new Set());
      await loadImages();
    } catch (err) {
      setError(err.message);
    }
  };

  // ── Printify upload ──────────────────────────────────────────
  const handlePrintifyUpload = async (imageId, filename, productType, provider) => {
    const market = provider === "printful" ? "EU" : "US";
    const key = `${filename}:${provider}:${productType}`;
    setUploadingPrintify(key);
    setError("");
    try {
      // Auto-publish to front_custom/approved if not already published
      const img = images.find((i) => i.id === imageId);
      if (img && img.status === "processed") {
        await api.preparePublish(imageId);
      }
      await api.printifyUpload({
        designType: "custom",
        filename,
        productType,
        provider,
        market,
        draft: false,
      });
      setSuccess(`Uploaded ${productType} to ${provider}!`);
      await loadImages();
    } catch (err) {
      setError(err.message);
    } finally {
      setUploadingPrintify(null);
    }
  };

  const defaultProvider =
    providerStatus?.printify?.configured ? "printify" : "printful";
  const anyProviderConfigured =
    providerStatus?.printify?.configured || providerStatus?.printful?.configured;

  // ── Render ───────────────────────────────────────────────────
  return (
    <div>
      <h2>Prepare Custom Images</h2>

      <nav style={{ display: "flex", gap: 4, marginBottom: 16 }}>
        {SUBTABS.map((s) => (
          <button
            key={s.key}
            className={`subtab ${subtab === s.key ? "active" : ""}`}
            onClick={() => {
              setSubtab(s.key);
              setSelectedIds(new Set());
              setError("");
              setSuccess("");
            }}
          >
            {s.label}
            {s.key === "upload" && (
              <span className="badge" style={{ marginLeft: 6 }}>
                {filterByStatus(["uploaded"]).length}
              </span>
            )}
            {s.key === "processed" && (
              <span className="badge" style={{ marginLeft: 6 }}>
                {filterByStatus(["processed"]).length}
              </span>
            )}
            {s.key === "published" && (
              <span className="badge" style={{ marginLeft: 6 }}>
                {filterByStatus(["published"]).length}
              </span>
            )}
          </button>
        ))}
      </nav>

      {error && (
        <div className="card" style={{ background: "#fef2f2", borderColor: "#fca5a5", color: "#dc2626", marginBottom: 12 }}>
          {error}
        </div>
      )}
      {success && (
        <div className="card" style={{ background: "#f0fdf4", borderColor: "#86efac", color: "#16a34a", marginBottom: 12 }}>
          {success}
        </div>
      )}

      {/* ── UPLOAD TAB ─────────────────────────────────────── */}
      {subtab === "upload" && (
        <>
          <div
            className={`upload-dropzone ${dragOver ? "drag-over" : ""}`}
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={() => setDragOver(false)}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".png,.jpg,.jpeg"
              style={{ display: "none" }}
              onChange={(e) => handleFiles(e.target.files)}
            />
            {uploading ? (
              <span>Uploading...</span>
            ) : (
              <span>Drop images here or click to upload (PNG / JPG)</span>
            )}
          </div>

          {(() => {
            const items = filterByStatus(["uploaded"]);
            if (!items.length) return null;
            return (
              <>
                <div className="prepare-actions">
                  <button
                    className="primary"
                    disabled={!selectedIds.size || processing}
                    onClick={handleProcess}
                  >
                    {processing
                      ? "Processing..."
                      : `Process Selected (${selectedIds.size})`}
                  </button>
                  <button onClick={() => selectAll(items)}>
                    {selectedIds.size === items.length
                      ? "Deselect All"
                      : "Select All"}
                  </button>
                  <button
                    className="danger"
                    disabled={!selectedIds.size}
                    onClick={() => handleDelete([...selectedIds])}
                  >
                    Delete Selected
                  </button>
                </div>

                {processing && processLog && (
                  <pre className="card" style={{ fontSize: 11, maxHeight: 150, overflow: "auto", whiteSpace: "pre-wrap" }}>
                    {processLog}
                  </pre>
                )}

                <div className="prepare-grid">
                  {items.map((img) => (
                    <div
                      key={img.id}
                      className={`prepare-card ${
                        selectedIds.has(img.id) ? "selected" : ""
                      }`}
                      onClick={() => toggleSelect(img.id)}
                    >
                      <img
                        className="prepare-card-img"
                        src={api.prepareImageUrl(img.id, "original")}
                        alt={img.original_filename}
                        loading="lazy"
                      />
                      <div className="prepare-card-name">
                        {img.original_filename}
                      </div>
                      <div className="prepare-card-meta">
                        {img.original_width}x{img.original_height}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            );
          })()}

          {/* Also show processing/failed items */}
          {(() => {
            const processingItems = filterByStatus(["processing"]);
            if (!processingItems.length) return null;
            return (
              <div style={{ marginTop: 16 }}>
                <h3 style={{ fontSize: 14, color: "#6b7280" }}>Processing...</h3>
                <div className="prepare-grid">
                  {processingItems.map((img) => (
                    <div key={img.id} className="prepare-card" style={{ opacity: 0.6 }}>
                      <img
                        className="prepare-card-img"
                        src={api.prepareImageUrl(img.id, "original")}
                        alt={img.original_filename}
                        loading="lazy"
                      />
                      <div className="prepare-card-name">{img.original_filename}</div>
                      <span className="badge" style={{ background: "#dbeafe", color: "#2563eb" }}>Processing</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}
        </>
      )}

      {/* ── PROCESSED TAB ──────────────────────────────────── */}
      {subtab === "processed" && (
        <>
          {(() => {
            const items = filterByStatus(["processed"]);
            if (!items.length) {
              return <div className="card" style={{ color: "#6b7280" }}>No processed images yet. Upload and process images first.</div>;
            }
            return (
              <>
                <div className="prepare-actions">
                  <button
                    className="primary"
                    disabled={!selectedIds.size}
                    onClick={() => handlePublish([...selectedIds])}
                  >
                    Publish Selected ({selectedIds.size})
                  </button>
                  <button onClick={() => selectAll(items)}>
                    {selectedIds.size === items.length
                      ? "Deselect All"
                      : "Select All"}
                  </button>
                </div>

                <div className="prepare-grid">
                  {items.map((img) => {
                    const ver = previewVersion[img.id] || "processed";
                    return (
                      <div
                        key={img.id}
                        className={`prepare-card ${
                          selectedIds.has(img.id) ? "selected" : ""
                        }`}
                        onClick={() => toggleSelect(img.id)}
                      >
                        <img
                          className="prepare-card-img"
                          src={api.prepareImageUrl(img.id, ver)}
                          alt={img.original_filename}
                          loading="lazy"
                        />
                        <div className="prepare-card-name">
                          {img.original_filename}
                        </div>
                        <div className="prepare-card-meta">
                          {img.processed_width}x{img.processed_height}
                        </div>
                        <div style={{ display: "flex", gap: 4 }}>
                          <button
                            className={ver === "original" ? "primary" : ""}
                            style={{ fontSize: 10, padding: "2px 6px" }}
                            onClick={(e) => {
                              e.stopPropagation();
                              setPreviewVersion((p) => ({ ...p, [img.id]: "original" }));
                            }}
                          >
                            Before
                          </button>
                          <button
                            className={ver === "processed" ? "primary" : ""}
                            style={{ fontSize: 10, padding: "2px 6px" }}
                            onClick={(e) => {
                              e.stopPropagation();
                              setPreviewVersion((p) => ({ ...p, [img.id]: "processed" }));
                            }}
                          >
                            After
                          </button>
                          <button
                            className="primary"
                            style={{ fontSize: 10, padding: "2px 6px", marginLeft: "auto" }}
                            onClick={(e) => {
                              e.stopPropagation();
                              handlePublish([img.id]);
                            }}
                          >
                            Publish
                          </button>
                        </div>
                        {anyProviderConfigured && (
                          <div style={{ display: "flex", gap: 4, marginTop: 4 }}>
                            <select
                              style={{ fontSize: 11, flex: 1 }}
                              value={providerByFile[img.stored_filename] || defaultProvider}
                              onClick={(e) => e.stopPropagation()}
                              onChange={(e) =>
                                setProviderByFile((p) => ({
                                  ...p,
                                  [img.stored_filename]: e.target.value,
                                }))
                              }
                            >
                              <option value="printify" disabled={!providerStatus?.printify?.configured}>
                                Printify (US)
                              </option>
                              <option value="printful" disabled={!providerStatus?.printful?.configured}>
                                Printful (EU)
                              </option>
                            </select>
                            <button
                              className="primary"
                              style={{ fontSize: 10, padding: "2px 6px" }}
                              disabled={uploadingPrintify === `${img.stored_filename}:${providerByFile[img.stored_filename] || defaultProvider}:tshirt`}
                              onClick={(e) => {
                                e.stopPropagation();
                                handlePrintifyUpload(img.id, img.stored_filename, "tshirt", providerByFile[img.stored_filename] || defaultProvider);
                              }}
                            >
                              {uploadingPrintify === `${img.stored_filename}:${providerByFile[img.stored_filename] || defaultProvider}:tshirt` ? "..." : "Tee"}
                            </button>
                            <button
                              style={{ fontSize: 10, padding: "2px 6px" }}
                              disabled={uploadingPrintify === `${img.stored_filename}:${providerByFile[img.stored_filename] || defaultProvider}:hoodie`}
                              onClick={(e) => {
                                e.stopPropagation();
                                handlePrintifyUpload(img.id, img.stored_filename, "hoodie", providerByFile[img.stored_filename] || defaultProvider);
                              }}
                            >
                              {uploadingPrintify === `${img.stored_filename}:${providerByFile[img.stored_filename] || defaultProvider}:hoodie` ? "..." : "Hoodie"}
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </>
            );
          })()}
        </>
      )}

      {/* ── PUBLISHED TAB ──────────────────────────────────── */}
      {subtab === "published" && (
        <>
          {(() => {
            const items = filterByStatus(["published"]);
            if (!items.length) {
              return <div className="card" style={{ color: "#6b7280" }}>No published images yet.</div>;
            }
            return (
              <div className="prepare-grid">
                {items.map((img) => {
                  const prov =
                    providerByFile[img.stored_filename] || defaultProvider;
                  return (
                    <div key={img.id} className="prepare-card">
                      <img
                        className="prepare-card-img"
                        src={api.prepareImageUrl(img.id, "processed")}
                        alt={img.original_filename}
                        loading="lazy"
                      />
                      <div className="prepare-card-name">
                        {img.original_filename}
                      </div>
                      <div className="prepare-card-meta">
                        Published{" "}
                        {img.published_at
                          ? new Date(img.published_at).toLocaleDateString()
                          : ""}
                      </div>

                      {anyProviderConfigured && (
                        <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 4 }}>
                          <select
                            style={{ fontSize: 11 }}
                            value={prov}
                            onClick={(e) => e.stopPropagation()}
                            onChange={(e) =>
                              setProviderByFile((p) => ({
                                ...p,
                                [img.stored_filename]: e.target.value,
                              }))
                            }
                          >
                            <option
                              value="printify"
                              disabled={!providerStatus?.printify?.configured}
                            >
                              Printify (US)
                            </option>
                            <option
                              value="printful"
                              disabled={!providerStatus?.printful?.configured}
                            >
                              Printful (EU)
                            </option>
                          </select>
                          <div style={{ display: "flex", gap: 4 }}>
                            <button
                              className="primary"
                              style={{ fontSize: 10, padding: "2px 6px", flex: 1 }}
                              disabled={
                                uploadingPrintify ===
                                `${img.stored_filename}:${prov}:tshirt`
                              }
                              onClick={() =>
                                handlePrintifyUpload(
                                  img.id,
                                  img.stored_filename,
                                  "tshirt",
                                  prov,
                                )
                              }
                            >
                              {uploadingPrintify ===
                              `${img.stored_filename}:${prov}:tshirt`
                                ? "..."
                                : "T-Shirt"}
                            </button>
                            <button
                              style={{ fontSize: 10, padding: "2px 6px", flex: 1 }}
                              disabled={
                                uploadingPrintify ===
                                `${img.stored_filename}:${prov}:hoodie`
                              }
                              onClick={() =>
                                handlePrintifyUpload(
                                  img.id,
                                  img.stored_filename,
                                  "hoodie",
                                  prov,
                                )
                              }
                            >
                              {uploadingPrintify ===
                              `${img.stored_filename}:${prov}:hoodie`
                                ? "..."
                                : "Hoodie"}
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })()}
        </>
      )}
    </div>
  );
}
