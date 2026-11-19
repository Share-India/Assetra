import React, { useState, useEffect, useMemo, useCallback } from "react";
import { 
  ArrowLeft, ArrowRight, Download, Search, Filter, RefreshCw, 
  Loader2, LayoutGrid, Table as TableIcon, FileText, CheckCircle2, 
  AlertTriangle, Clock, Hash, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight
} from "lucide-react";

export default function ResultsStep({
  analysisId,
  companyDetails,
  selectedFile,
  token,
  apiBaseUrl,
  onNext,
  onBack,
  onAnalyzeNew
}) {
  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [rows, setRows] = useState([]);
  const [totalRows, setTotalRows] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(100);
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [wpiFilter, setWpiFilter] = useState("");
  const [rowsLoading, setRowsLoading] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [forceTableMobile, setForceTableMobile] = useState(false);
  const [analysisMeta, setAnalysisMeta] = useState(null);

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  // Fetch analysis metadata & summary
  useEffect(() => {
    if (!analysisId) return;
    const fetchMetaAndSummary = async () => {
      setSummaryLoading(true);
      try {
        const [metaRes, sumRes] = await Promise.all([
          fetch(`${apiBaseUrl}/analyses/${analysisId}`, { headers: { "Authorization": `Bearer ${token}` } }),
          fetch(`${apiBaseUrl}/analyses/${analysisId}/summary`, { headers: { "Authorization": `Bearer ${token}` } })
        ]);
        if (metaRes.ok) {
          const metaData = await metaRes.json();
          setAnalysisMeta(metaData);
        }
        if (sumRes.ok) {
          const sumData = await sumRes.json();
          setSummary(sumData);
        }
      } catch (e) {
        console.error("Error fetching summary:", e);
      } finally {
        setSummaryLoading(false);
      }
    };
    fetchMetaAndSummary();
  }, [analysisId, apiBaseUrl, token]);

  // Fetch paginated rows from server
  const fetchRows = useCallback(async () => {
    if (!analysisId) return;
    setRowsLoading(true);
    try {
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString()
      });
      if (debouncedSearch.trim()) params.append("search", debouncedSearch.trim());
      if (statusFilter) params.append("status", statusFilter);
      if (wpiFilter) params.append("wpi_group", wpiFilter);

      const res = await fetch(`${apiBaseUrl}/analyses/${analysisId}/rows?${params.toString()}`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setRows(data.rows || []);
        setTotalRows(data.total || 0);
        setTotalPages(data.total_pages || 1);
      }
    } catch (e) {
      console.error("Error fetching rows:", e);
    } finally {
      setRowsLoading(false);
    }
  }, [analysisId, page, pageSize, debouncedSearch, statusFilter, wpiFilter, apiBaseUrl, token]);

  useEffect(() => {
    fetchRows();
  }, [fetchRows]);

  const handleDownloadReport = async () => {
    if (!analysisId) return;
    setDownloading(true);
    try {
      const res = await fetch(`${apiBaseUrl}/analyses/${analysisId}/download`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const compName = (analysisMeta?.company_name || companyDetails?.name || "ASSETRA").replace(/\s+/g, "_");
      a.download = `ASSETRA_Replacement_Report_${compName}_${analysisId}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      alert("Failed to download report. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  const fmtINR = (val) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val || 0);
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return "-";
    try {
      const d = new Date(isoStr);
      return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch {
      return isoStr;
    }
  };

  const renderMethodPill = (method, status) => {
    const m = String(method || "");
    if (m.includes("5%") || m.includes("Compound") || m.includes("Escalation")) {
      return (
        <span style={{
          display: "inline-flex",
          alignItems: "center",
          padding: "2px 8px",
          borderRadius: 9999,
          fontSize: 11,
          fontWeight: 600,
          background: "#F5F3FF",
          color: "#6D28D9",
          border: "1px solid #DDD6FE",
          whiteSpace: "nowrap"
        }}>
          5% Compound
        </span>
      );
    }

    let label = "WPI Based";
    if (m.includes("no index change")) label = "WPI (No Change)";
    else if (m.includes("floored")) label = "WPI (Floored)";
    
    return (
      <span style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: 9999,
        fontSize: 11,
        fontWeight: 600,
        background: "#EFF6FF",
        color: "#1D4ED8",
        border: "1px solid #BFDBFE",
        whiteSpace: "nowrap"
      }} title={m}>
        {label}
      </span>
    );
  };

  const wpiGroupOptions = useMemo(() => {
    if (!summary?.["Assets by WPI Category"]) return [];
    return Object.keys(summary["Assets by WPI Category"]).filter(g => g && g !== "Unassigned");
  }, [summary]);

  return (
    <div style={{ maxWidth: 1400, margin: "0 auto", width: "100%" }}>
      <style>{`
        .far-filter-toolbar {
          background: #fff;
          border: 1px solid #E2E8F0;
          border-radius: 12px;
          padding: 16px 20px;
          margin-bottom: 16px;
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          align-items: center;
          justify-content: space-between;
        }
        @media (max-width: 767px) {
          .far-filter-toolbar {
            padding: 12px 14px;
            gap: 10px;
          }
          .far-filter-left {
            width: 100% !important;
            flex: 1 1 100% !important;
          }
          .far-filter-right {
            width: 100% !important;
            display: flex !important;
            justify-content: space-between !important;
          }
          .far-filter-right select,
          .far-filter-right button {
            flex: 1 !important;
            justify-content: center !important;
          }
        }
        @media (max-width: 639px) {
          .far-pagination-bar {
            flex-direction: column !important;
            align-items: center !important;
            text-align: center !important;
            gap: 12px !important;
            padding: 12px 14px !important;
          }
          .far-pagination-controls {
            width: 100% !important;
            justify-content: center !important;
            flex-wrap: wrap !important;
          }
        }
        @media (max-width: 480px) {
          .far-filter-left > * {
            width: 100% !important;
            max-width: 100% !important;
          }
          .far-filter-left select {
            width: 100% !important;
            max-width: 100% !important;
          }
        }
      `}</style>
      {/* HEADER SECTION */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "flex-end",
        marginBottom: 20,
        flexWrap: "wrap",
        gap: 16
      }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginBottom: 6 }}>
            <h2 style={{ fontSize: 24, fontWeight: 700, color: "#0F172A", margin: 0 }}>
              Replacement Value Dashboard
            </h2>
            {analysisMeta?.master_version && (
              <span style={{
                fontSize: 12,
                fontFamily: "monospace",
                background: "#E2E8F0",
                color: "#334155",
                padding: "2px 8px",
                borderRadius: 4,
                fontWeight: 600
              }}>
                master v{analysisMeta.master_version}
              </span>
            )}
          </div>
          <p style={{ fontSize: 13, color: "#64748B", margin: 0, display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span>Calculated on {formatDate(analysisMeta?.created_at)}</span>
            <span>•</span>
            <span>Linked WPI series up to 2025</span>
          </p>
        </div>

        <div className="far-btn-container" style={{ display: "flex", gap: 12, alignItems: "center" }}>
          {onBack && (
            <button
              onClick={onBack}
              style={{
                background: "transparent",
                color: "#64748B",
                border: "1px solid #CBD5E1",
                padding: "10px 18px",
                borderRadius: 8,
                fontSize: 14,
                fontWeight: 500,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                minHeight: 44
              }}
              className="far-btn"
            >
              <ArrowLeft size={18} /> Back
            </button>
          )}

          <button
            onClick={handleDownloadReport}
            disabled={downloading}
            style={{
              background: "#2563EB",
              color: "#fff",
              border: "none",
              padding: "10px 22px",
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              minHeight: 44,
              boxShadow: "0 2px 4px rgba(37,99,235,0.2)"
            }}
            className="far-btn"
          >
            {downloading ? <Loader2 size={18} className="animate-spin" /> : <Download size={18} />}
            Download Report (Excel)
          </button>
        </div>
      </div>

      {/* SUMMARY CARDS (1 / 2 / 5 columns responsive) */}
      <div className="far-summary-cards-grid">
        <div style={{ background: "#fff", border: "1px solid #E2E8F0", borderRadius: 12, padding: "18px 20px" }}>
          <div style={{ fontSize: 13, color: "#64748B", fontWeight: 500 }}>Total Assets</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: "#0F172A", margin: "4px 0 2px" }}>
            {(summary?.["Total Assets"] || analysisMeta?.rows_total || 0).toLocaleString("en-IN")}
          </div>
          <div style={{ fontSize: 12, color: "#94A3B8" }}>All rows in file</div>
        </div>

        <div style={{ background: "#fff", border: "1px solid #E2E8F0", borderRadius: 12, padding: "18px 20px" }}>
          <div style={{ fontSize: 13, color: "#64748B", fontWeight: 500 }}>Calculated Assets</div>
          <div style={{ fontSize: 24, fontWeight: 700, color: "#16A34A", margin: "4px 0 2px" }}>
            {(summary?.["Calculated Assets"] || analysisMeta?.rows_calculated || 0).toLocaleString("en-IN")}
          </div>
          <div style={{ fontSize: 12, color: "#94A3B8" }}>WPI & Building Escalation</div>
        </div>

        <div style={{ background: "#fff", border: "1px solid #E2E8F0", borderRadius: 12, padding: "18px 20px" }}>
          <div style={{ fontSize: 13, color: "#64748B", fontWeight: 500 }}>Total Acquisition Value</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: "#0F172A", margin: "4px 0 2px" }}>
            {fmtINR(summary?.["Total Acquisition Value"] || analysisMeta?.total_acquisition)}
          </div>
          <div style={{ fontSize: 12, color: "#94A3B8" }}>Historical cost basis</div>
        </div>

        <div style={{ background: "#EFF6FF", border: "1px solid #BFDBFE", borderRadius: 12, padding: "18px 20px" }}>
          <div style={{ fontSize: 13, color: "#1E40AF", fontWeight: 600 }}>Total Replacement Value</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: "#1D4ED8", margin: "4px 0 2px" }}>
            {fmtINR(summary?.["Total Replacement Value"] || analysisMeta?.total_replacement)}
          </div>
          <div style={{ fontSize: 12, color: "#60A5FA" }}>Current replacement cost</div>
        </div>

        <div style={{ background: "#fff", border: "1px solid #E2E8F0", borderRadius: 12, padding: "18px 20px" }}>
          <div style={{ fontSize: 13, color: "#64748B", fontWeight: 500 }}>Total Difference</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: (summary?.["Total Difference"] >= 0) ? "#15803D" : "#B91C1C", margin: "4px 0 2px" }}>
            {fmtINR(summary?.["Total Difference"])}
          </div>
          <div style={{ fontSize: 12, color: "#15803D", fontWeight: 600 }}>
            {summary?.["Overall Increase %"] ? `+${(summary["Overall Increase %"] * 100).toFixed(1)}% overall` : "+0.0%"}
          </div>
        </div>
      </div>

      {/* FILTER & SEARCH CONTROLS BAR */}
      <div className="far-filter-toolbar">
        <div className="far-filter-left" style={{ display: "flex", flex: 1, minWidth: 240, gap: 10, flexWrap: "wrap" }}>
          {/* SEARCH INPUT */}
          <div style={{ position: "relative", flex: 1, minWidth: 200 }}>
            <Search size={16} color="#94A3B8" style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)" }} />
            <input
              type="text"
              placeholder="Search description, asset code, category..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: "100%",
                height: 40,
                paddingLeft: 36,
                paddingRight: 12,
                borderRadius: 8,
                border: "1px solid #CBD5E1",
                fontSize: 13,
                outline: "none",
                boxSizing: "border-box"
              }}
            />
          </div>

          {/* STATUS FILTER */}
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            style={{
              height: 40,
              padding: "0 12px",
              borderRadius: 8,
              border: "1px solid #CBD5E1",
              fontSize: 13,
              background: "#fff",
              color: "#334155",
              outline: "none"
            }}
          >
            <option value="">All Statuses</option>
            <option value="calculated">Calculated Only</option>
            <option value="manual">Manual Review Required</option>
            <option value="na">Not Applicable</option>
          </select>

          {/* WPI GROUP FILTER */}
          <select
            value={wpiFilter}
            onChange={(e) => { setWpiFilter(e.target.value); setPage(1); }}
            style={{
              height: 40,
              padding: "0 12px",
              borderRadius: 8,
              border: "1px solid #CBD5E1",
              fontSize: 13,
              background: "#fff",
              color: "#334155",
              outline: "none",
              maxWidth: 220
            }}
          >
            <option value="">All WPI Groups</option>
            {wpiGroupOptions.map(g => (
              <option key={g} value={g}>{g}</option>
            ))}
          </select>
        </div>

        {/* VIEW TOGGLE & PAGE SIZE */}
        <div className="far-filter-right" style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <select
            value={pageSize}
            onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
            style={{
              height: 40,
              padding: "0 10px",
              borderRadius: 8,
              border: "1px solid #CBD5E1",
              fontSize: 13,
              background: "#fff",
              color: "#334155"
            }}
          >
            <option value={50}>50 per page</option>
            <option value={100}>100 per page</option>
            <option value={200}>200 per page</option>
          </select>

          <button
            onClick={() => setForceTableMobile(!forceTableMobile)}
            style={{
              height: 40,
              padding: "0 12px",
              borderRadius: 8,
              border: "1px solid #CBD5E1",
              background: "#fff",
              color: "#475569",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
              fontSize: 13,
              fontWeight: 500
            }}
          >
            {forceTableMobile ? <><LayoutGrid size={15} /> Cards</> : <><TableIcon size={15} /> Table</>}
          </button>
        </div>
      </div>

      {/* TABLE / CARDS CONTAINER */}
      <div className={forceTableMobile ? "far-force-table" : ""} style={{
        background: "#fff",
        border: "1px solid #E2E8F0",
        borderRadius: 12,
        overflow: "hidden",
        boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
        position: "relative"
      }}>
        {rowsLoading && (
          <div style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(255, 255, 255, 0.7)",
            backdropFilter: "blur(2px)",
            zIndex: 50,
            display: "flex",
            alignItems: "center",
            justifyContent: "center"
          }}>
            <Loader2 className="animate-spin" size={32} color="#2563EB" />
          </div>
        )}

        {/* DESKTOP TABLE */}
        <div className="far-desktop-table-view far-table-container">
          <table style={{ textAlign: "left", fontSize: 13, width: "100%", minWidth: 950, borderCollapse: "separate", borderSpacing: 0 }}>
            <thead>
              <tr style={{ background: "#F8FAFC" }}>
                <th className="col-fixed" style={{ padding: "14px 16px", fontWeight: 600, color: "#64748B", width: 50, background: "#F8FAFC" }}>#</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: "#64748B" }}>Asset Code</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: "#64748B" }}>Description</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: "#64748B" }}>Purchase Year</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: "#64748B", textAlign: "right" }}>Acq Value</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: "#64748B" }}>WPI Group</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: "#64748B" }}>Method</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: "#2563EB", textAlign: "right" }}>Replacement Value</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: "#64748B", textAlign: "right" }}>Difference</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: "#64748B", textAlign: "center" }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const diff = (r.replacementValue || 0) - (r.acquisitionValue || 0);
                return (
                  <tr key={r.id || r.rowNo} style={{ borderBottom: "1px solid #E2E8F0" }}>
                    <td className="col-fixed" style={{ padding: "12px 16px", color: "#64748B", fontSize: 12, background: "#fff" }}>
                      {r.rowNo}
                    </td>
                    <td style={{ padding: "12px 16px", color: "#0F172A", fontFamily: "monospace", fontSize: 12 }}>
                      {r.assetCode || "-"}
                    </td>
                    <td style={{
                      padding: "12px 16px",
                      color: "#0F172A",
                      maxWidth: 260,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis"
                    }} title={r.description}>
                      {r.description || "-"}
                    </td>
                    <td style={{ padding: "12px 16px", color: "#0F172A", fontVariantNumeric: "tabular-nums" }}>
                      {r.purchaseYear || "-"}
                    </td>
                    <td style={{ padding: "12px 16px", color: "#0F172A", textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                      {fmtINR(r.acquisitionValue)}
                    </td>
                    <td style={{ padding: "12px 16px", color: "#475569", maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={r.wpiGroup}>
                      {r.wpiGroup || "-"}
                    </td>
                    <td style={{ padding: "12px 16px" }}>
                      {renderMethodPill(r.calculationMethod, r.status)}
                    </td>
                    <td style={{
                      padding: "12px 16px",
                      color: "#0F172A",
                      fontWeight: 700,
                      textAlign: "right",
                      background: "#EFF6FF",
                      fontVariantNumeric: "tabular-nums"
                    }}>
                      {fmtINR(r.replacementValue)}
                    </td>
                    <td style={{
                      padding: "12px 16px",
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                      fontWeight: 600,
                      color: diff > 0 ? "#15803D" : diff < 0 ? "#B91C1C" : "#64748B"
                    }}>
                      {diff !== 0 ? (diff > 0 ? `+${fmtINR(diff)}` : fmtINR(diff)) : "₹0.00"}
                    </td>
                    <td style={{ padding: "12px 16px", textAlign: "center" }}>
                      <span style={{
                        padding: "3px 8px",
                        borderRadius: 4,
                        fontSize: 11,
                        fontWeight: 600,
                        whiteSpace: "nowrap",
                        background: r.status === "Success" ? "#DCFCE7" : (r.status === "Not Applicable" ? "#F1F5F9" : "#FEF3C7"),
                        color: r.status === "Success" ? "#166534" : (r.status === "Not Applicable" ? "#475569" : "#92400E")
                      }}>
                        {r.status || "Success"}
                      </span>
                    </td>
                  </tr>
                );
              })}
              {rows.length === 0 && !rowsLoading && (
                <tr>
                  <td colSpan={10} style={{ padding: "40px 20px", textAlign: "center", color: "#64748B" }}>
                    No matching asset rows found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* MOBILE CARDS VIEW */}
        <div className="far-mobile-cards-view" style={{ padding: 12 }}>
          {rows.map((r) => {
            const diff = (r.replacementValue || 0) - (r.acquisitionValue || 0);
            return (
              <div key={r.id || r.rowNo} style={{
                background: "#fff",
                border: "1px solid #E2E8F0",
                borderRadius: 10,
                padding: "14px",
                marginBottom: 10,
                boxShadow: "0 1px 3px rgba(0,0,0,0.03)"
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: "#64748B", background: "#F1F5F9", padding: "2px 6px", borderRadius: 4 }}>
                      #{r.rowNo}
                    </span>
                    {r.assetCode && (
                      <span style={{ fontSize: 12, fontFamily: "monospace", color: "#0F172A", fontWeight: 600 }}>
                        {r.assetCode}
                      </span>
                    )}
                  </div>
                  {renderMethodPill(r.calculationMethod, r.status)}
                </div>

                <div style={{ fontSize: 14, fontWeight: 600, color: "#0F172A", marginBottom: 10, lineHeight: 1.4 }}>
                  {r.description || "-"}
                </div>

                <div style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "8px 10px",
                  fontSize: 12,
                  background: "#F8FAFC",
                  padding: "10px 12px",
                  borderRadius: 8,
                  marginBottom: 10
                }}>
                  <div>
                    <span style={{ color: "#64748B", display: "block" }}>Purchase Year</span>
                    <span style={{ fontWeight: 600, color: "#0F172A" }}>{r.purchaseYear || "-"}</span>
                  </div>
                  <div>
                    <span style={{ color: "#64748B", display: "block" }}>WPI Group</span>
                    <span style={{ fontWeight: 500, color: "#0F172A", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block" }}>
                      {r.wpiGroup || "-"}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: "#64748B", display: "block" }}>Acquisition Value</span>
                    <span style={{ fontWeight: 600, color: "#0F172A" }}>{fmtINR(r.acquisitionValue)}</span>
                  </div>
                  <div>
                    <span style={{ color: "#64748B", display: "block" }}>Replacement Value</span>
                    <span style={{ fontWeight: 700, color: "#2563EB" }}>{fmtINR(r.replacementValue)}</span>
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12 }}>
                  <span style={{ color: "#64748B" }}>Difference:</span>
                  <span style={{ fontWeight: 600, color: diff >= 0 ? "#15803D" : "#B91C1C" }}>
                    {diff >= 0 ? "+" : ""}{fmtINR(diff)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* SERVER-SIDE PAGINATION BAR */}
        <div className="far-pagination-bar" style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "14px 20px",
          borderTop: "1px solid #E2E8F0",
          background: "#FAFAFA",
          flexWrap: "wrap",
          gap: 12
        }}>
          <div style={{ fontSize: 13, color: "#64748B" }}>
            Showing {totalRows === 0 ? 0 : (page - 1) * pageSize + 1}–{Math.min(page * pageSize, totalRows)} of {totalRows.toLocaleString("en-IN")} asset rows
          </div>

          <div className="far-pagination-controls" style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <button
              onClick={() => setPage(1)}
              disabled={page <= 1 || rowsLoading}
              title="First Page"
              style={{
                height: 34,
                padding: "0 8px",
                borderRadius: 6,
                border: "1px solid #CBD5E1",
                background: "#fff",
                color: "#475569",
                cursor: page <= 1 ? "not-allowed" : "pointer",
                opacity: page <= 1 ? 0.4 : 1
              }}
            >
              <ChevronsLeft size={16} />
            </button>

            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page <= 1 || rowsLoading}
              style={{
                height: 34,
                padding: "0 12px",
                borderRadius: 6,
                border: "1px solid #CBD5E1",
                background: "#fff",
                color: "#475569",
                cursor: page <= 1 ? "not-allowed" : "pointer",
                opacity: page <= 1 ? 0.4 : 1,
                fontSize: 13,
                fontWeight: 500,
                display: "flex",
                alignItems: "center",
                gap: 4
              }}
            >
              <ChevronLeft size={16} /> Prev
            </button>

            <span style={{ fontSize: 13, color: "#0F172A", fontWeight: 600, padding: "0 6px" }}>
              Page {page} of {totalPages}
            </span>

            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || rowsLoading}
              style={{
                height: 34,
                padding: "0 12px",
                borderRadius: 6,
                border: "1px solid #CBD5E1",
                background: "#fff",
                color: "#475569",
                cursor: page >= totalPages ? "not-allowed" : "pointer",
                opacity: page >= totalPages ? 0.4 : 1,
                fontSize: 13,
                fontWeight: 500,
                display: "flex",
                alignItems: "center",
                gap: 4
              }}
            >
              Next <ChevronRight size={16} />
            </button>

            <button
              onClick={() => setPage(totalPages)}
              disabled={page >= totalPages || rowsLoading}
              title="Last Page"
              style={{
                height: 34,
                padding: "0 8px",
                borderRadius: 6,
                border: "1px solid #CBD5E1",
                background: "#fff",
                color: "#475569",
                cursor: page >= totalPages ? "not-allowed" : "pointer",
                opacity: page >= totalPages ? 0.4 : 1
              }}
            >
              <ChevronsRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
