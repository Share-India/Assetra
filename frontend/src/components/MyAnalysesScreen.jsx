import React, { useState, useEffect } from "react";
import { 
  FileText, Plus, Download, Trash2, ExternalLink, Calendar, 
  Hash, ArrowRight, Loader2, AlertCircle, RefreshCw, Layers,
  Building2, CheckCircle2, Clock
} from "lucide-react";

export default function MyAnalysesScreen({ 
  onOpenAnalysis, 
  onAnalyzeNew, 
  onRefreshProfile,
  token, 
  apiBaseUrl 
}) {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [justRefreshed, setJustRefreshed] = useState(false);
  const [error, setError] = useState("");
  const [deletingId, setDeletingId] = useState(null);

  const fetchAnalyses = async () => {
    setIsRefreshing(true);
    setError("");
    try {
      const promises = [
        fetch(`${apiBaseUrl}/analyses`, {
          headers: { "Authorization": `Bearer ${token}` }
        })
      ];
      if (typeof onRefreshProfile === "function") {
        promises.push(onRefreshProfile());
      }
      const [res] = await Promise.all(promises);
      if (!res.ok) {
        throw new Error("Failed to load your saved analyses.");
      }
      const data = await res.json();
      setAnalyses(data.analyses || []);
      setJustRefreshed(true);
      setTimeout(() => setJustRefreshed(false), 2000);
    } catch (err) {
      setError(err.message || "Failed to load analyses.");
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAnalyses();
  }, []);

  const handleDelete = async (id, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this analysis? This action cannot be undone.")) {
      return;
    }
    setDeletingId(id);
    try {
      const res = await fetch(`${apiBaseUrl}/analyses/${id}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) {
        throw new Error("Failed to delete analysis.");
      }
      setAnalyses(prev => prev.filter(a => a.id !== id));
    } catch (err) {
      alert(err.message || "Could not delete analysis.");
    } finally {
      setDeletingId(null);
    }
  };

  const handleDownload = async (id, company, e) => {
    e.stopPropagation();
    try {
      const res = await fetch(`${apiBaseUrl}/analyses/${id}/download`, {
        headers: { "Authorization": `Bearer ${token}` }
      });
      if (!res.ok) throw new Error("Download failed");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `ASSETRA_Report_${(company || "ASSETRA").replace(/\s+/g, "_")}_${id}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert("Failed to download report. Please try again.");
    }
  };

  const fmtCurrency = (val) => {
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

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "16px 8px" }}>
      <style>{`
        .far-analyses-header {
          display: flex;
          flex-wrap: wrap;
          justify-content: space-between;
          align-items: center;
          gap: 16px;
          margin-bottom: 24px;
          background: #fff;
          padding: 20px 24px;
          border-radius: 12px;
          border: 1px solid #E2E8F0;
          box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }
        .far-analyses-card-top {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          flex-wrap: wrap;
          gap: 12px;
        }
        .far-analyses-actions {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .far-analyses-stats-grid {
          display: grid;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          gap: 10px;
          padding-top: 10px;
          border-top: 1px solid #F1F5F9;
        }
        @media (max-width: 900px) {
          .far-analyses-stats-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
          }
        }
        @media (max-width: 639px) {
          .far-analyses-header {
            padding: 16px 14px !important;
            gap: 14px !important;
          }
          .far-analyses-header > div:first-child {
            width: 100% !important;
          }
          .far-analyses-header-btns {
            width: 100% !important;
            display: flex !important;
            gap: 10px !important;
          }
          .far-analyses-header-btns button {
            flex: 1 !important;
            justify-content: center !important;
          }
          .far-analyses-card-top {
            flex-direction: column !important;
            align-items: stretch !important;
          }
          .far-analyses-actions {
            width: 100% !important;
            justify-content: flex-end !important;
            padding-top: 4px;
          }
          .far-analyses-actions button {
            min-height: 40px !important;
          }
        }
        @media (max-width: 440px) {
          .far-analyses-stats-grid {
            grid-template-columns: 1fr !important;
          }
          .far-analyses-header-btns {
            flex-direction: column !important;
          }
          .far-analyses-header-btns button {
            width: 100% !important;
          }
        }
      `}</style>

      {/* HEADER SECTION */}
      <div className="far-analyses-header">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: "#0F172A", margin: 0, display: "flex", alignItems: "center", gap: 10 }}>
            <Layers className="text-blue-600" size={24} color="#2563EB" />
            My Saved Analyses
          </h1>
          <p style={{ margin: "4px 0 0", fontSize: 14, color: "#64748B" }}>
            View, open, download, or manage your previously calculated ASSETRA reports.
          </p>
        </div>

        <div className="far-analyses-header-btns" style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button
            id="refresh-analyses-btn"
            onClick={fetchAnalyses}
            disabled={isRefreshing}
            title="Refresh saved analyses and account profile"
            style={{
              height: 44,
              padding: "0 16px",
              borderRadius: 8,
              border: `1px solid ${justRefreshed ? "#86efac" : "#CBD5E1"}`,
              background: justRefreshed ? "#f0fdf4" : "#fff",
              color: justRefreshed ? "#15803d" : "#475569",
              cursor: isRefreshing ? "not-allowed" : "pointer",
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 14,
              fontWeight: 500,
              boxShadow: "0 1px 2px rgba(0,0,0,0.03)",
              transition: "all 0.2s ease"
            }}
          >
            {justRefreshed ? (
              <CheckCircle2 size={16} color="#16a34a" />
            ) : (
              <RefreshCw
                size={16}
                style={{
                  animation: isRefreshing ? "spin 0.8s linear infinite" : "none"
                }}
              />
            )}
            <span>{isRefreshing ? "Refreshing..." : justRefreshed ? "Updated!" : "Refresh"}</span>
          </button>

          <button
            onClick={onAnalyzeNew}
            style={{
              height: 44,
              padding: "0 20px",
              borderRadius: 8,
              border: "none",
              background: "#2563EB",
              color: "#fff",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 14,
              fontWeight: 600,
              boxShadow: "0 2px 4px rgba(37,99,235,0.2)"
            }}
          >
            <Plus size={18} />
            New Analysis
          </button>
        </div>
      </div>

      {/* ERROR BANNER */}
      {error && (
        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          background: "#FEF2F2",
          border: "1px solid #F87171",
          borderRadius: 8,
          padding: "12px 16px",
          color: "#991B1B",
          marginBottom: 20
        }}>
          <AlertCircle size={18} />
          <span style={{ fontSize: 14 }}>{error}</span>
        </div>
      )}

      {/* LOADING STATE */}
      {loading && analyses.length === 0 && (
        <div style={{
          background: "#fff",
          borderRadius: 12,
          padding: "60px 20px",
          textAlign: "center",
          border: "1px solid #E2E8F0"
        }}>
          <Loader2 className="animate-spin" size={32} color="#2563EB" style={{ margin: "0 auto 12px" }} />
          <p style={{ color: "#64748B", fontSize: 14 }}>Loading your saved analyses...</p>
        </div>
      )}

      {/* EMPTY STATE */}
      {!loading && analyses.length === 0 && !error && (
        <div style={{
          background: "#fff",
          borderRadius: 12,
          padding: "60px 24px",
          textAlign: "center",
          border: "1px dashed #CBD5E1"
        }}>
          <div style={{
            width: 56,
            height: 56,
            borderRadius: "50%",
            background: "#EFF6FF",
            color: "#2563EB",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 16px"
          }}>
            <FileText size={28} />
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 600, color: "#1E293B", margin: "0 0 6px" }}>No analyses found</h3>
          <p style={{ fontSize: 14, color: "#64748B", maxWidth: 420, margin: "0 auto 20px" }}>
            You haven't run any calculations yet. Upload your first register file to get started with ASSETRA.
          </p>
          <button
            onClick={onAnalyzeNew}
            style={{
              padding: "10px 22px",
              minHeight: 44,
              borderRadius: 8,
              border: "none",
              background: "#2563EB",
              color: "#fff",
              cursor: "pointer",
              fontSize: 14,
              fontWeight: 600
            }}
          >
            Start First Analysis
          </button>
        </div>
      )}

      {/* ANALYSES LIST */}
      <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
        {analyses.map((item) => (
          <div
            key={item.id}
            onClick={() => onOpenAnalysis(item.id)}
            style={{
              background: "#fff",
              border: "1px solid #E2E8F0",
              borderRadius: 12,
              padding: "18px 20px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
              cursor: "pointer",
              transition: "transform 0.15s ease, box-shadow 0.15s ease",
              display: "flex",
              flexDirection: "column",
              gap: 12
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "#93C5FD";
              e.currentTarget.style.boxShadow = "0 4px 12px rgba(37,99,235,0.08)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "#E2E8F0";
              e.currentTarget.style.boxShadow = "0 1px 3px rgba(0,0,0,0.02)";
            }}
          >
            {/* TOP ROW: Company name, status, actions */}
            <div className="far-analyses-card-top">
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
                  <span style={{ fontSize: 17, fontWeight: 700, color: "#0F172A" }}>
                    {item.company_name || "Unnamed Company"}
                  </span>
                  <span style={{
                    fontSize: 11,
                    fontWeight: 700,
                    textTransform: "uppercase",
                    padding: "3px 8px",
                    borderRadius: 9999,
                    background: item.status === "completed" ? "#DCFCE7" : (item.status === "processing" ? "#DBEAFE" : "#FEE2E2"),
                    color: item.status === "completed" ? "#166534" : (item.status === "processing" ? "#1E40AF" : "#991B1B")
                  }}>
                    {item.status}
                  </span>
                </div>
                <div style={{ fontSize: 13, color: "#64748B", marginTop: 4, display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <FileText size={14} />
                    {item.original_filename}
                  </span>
                  <span>•</span>
                  <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <Calendar size={14} />
                    Calculated on {formatDate(item.created_at)}
                  </span>
                  {item.master_version && (
                    <>
                      <span>•</span>
                      <span style={{ display: "flex", alignItems: "center", gap: 4, fontFamily: "monospace", fontSize: 12 }}>
                        <Hash size={13} />
                        master v{item.master_version}
                      </span>
                    </>
                  )}
                </div>
              </div>

              {/* ACTION BUTTONS */}
              <div className="far-analyses-actions" onClick={(e) => e.stopPropagation()}>
                <button
                  onClick={() => onOpenAnalysis(item.id)}
                  style={{
                    height: 38,
                    padding: "0 14px",
                    borderRadius: 6,
                    border: "1px solid #CBD5E1",
                    background: "#F8FAFC",
                    color: "#0F172A",
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 6
                  }}
                >
                  Open
                  <ArrowRight size={14} />
                </button>

                <button
                  onClick={(e) => handleDownload(item.id, item.company_name, e)}
                  title="Download Excel Report"
                  style={{
                    height: 38,
                    padding: "0 12px",
                    borderRadius: 6,
                    border: "1px solid #CBD5E1",
                    background: "#fff",
                    color: "#2563EB",
                    fontSize: 13,
                    fontWeight: 500,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 6
                  }}
                >
                  <Download size={15} />
                  <span className="hidden sm:inline">Report</span>
                </button>

                <button
                  onClick={(e) => handleDelete(item.id, e)}
                  disabled={deletingId === item.id}
                  title="Delete Analysis"
                  style={{
                    height: 38,
                    width: 38,
                    borderRadius: 6,
                    border: "1px solid #FCA5A5",
                    background: "#FEF2F2",
                    color: "#DC2626",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center"
                  }}
                >
                  {deletingId === item.id ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={15} />}
                </button>
              </div>
            </div>

            {/* STATS CHIPS BAR */}
            <div className="far-analyses-stats-grid">
              <div style={{ background: "#F8FAFC", padding: "8px 12px", borderRadius: 6 }}>
                <div style={{ fontSize: 11, color: "#64748B", textTransform: "uppercase", fontWeight: 600 }}>Total Rows</div>
                <div style={{ fontSize: 15, fontWeight: 700, color: "#0F172A" }}>
                  {(item.rows_total || 0).toLocaleString()}
                </div>
              </div>

              <div style={{ background: "#F8FAFC", padding: "8px 12px", borderRadius: 6 }}>
                <div style={{ fontSize: 11, color: "#64748B", textTransform: "uppercase", fontWeight: 600 }}>Calculated Assets</div>
                <div style={{ fontSize: 15, fontWeight: 700, color: "#16A34A" }}>
                  {(item.rows_calculated || 0).toLocaleString()}
                </div>
              </div>

              <div style={{ background: "#F8FAFC", padding: "8px 12px", borderRadius: 6 }}>
                <div style={{ fontSize: 11, color: "#64748B", textTransform: "uppercase", fontWeight: 600 }}>Total Acquisition</div>
                <div style={{ fontSize: 15, fontWeight: 700, color: "#0F172A" }}>
                  {fmtCurrency(item.total_acquisition)}
                </div>
              </div>

              <div style={{ background: "#F8FAFC", padding: "8px 12px", borderRadius: 6 }}>
                <div style={{ fontSize: 11, color: "#64748B", textTransform: "uppercase", fontWeight: 600 }}>Total Replacement</div>
                <div style={{ fontSize: 15, fontWeight: 700, color: "#2563EB" }}>
                  {fmtCurrency(item.total_replacement)}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
