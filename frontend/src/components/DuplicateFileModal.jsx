import React from "react";
import { AlertCircle, Clock, Hash, CheckCircle2, RefreshCw, X, ArrowRight } from "lucide-react";

export default function DuplicateFileModal({ analysis, onOpenSaved, onRecalculate, onCancel }) {
  if (!analysis) return null;

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
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: "rgba(15, 23, 42, 0.7)",
      backdropFilter: "blur(4px)",
      zIndex: 9999,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: 16
    }}>
      <div style={{
        background: "#fff",
        borderRadius: 16,
        maxWidth: 500,
        width: "100%",
        maxHeight: "calc(100dvh - 32px)",
        overflowY: "auto",
        WebkitOverflowScrolling: "touch",
        padding: "28px 24px",
        boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
        border: "1px solid #E2E8F0",
        boxSizing: "border-box",
        position: "relative"
      }}>
        <button
          onClick={onCancel}
          style={{
            position: "absolute",
            top: 16,
            right: 16,
            background: "transparent",
            border: "none",
            color: "#64748B",
            cursor: "pointer",
            padding: 4
          }}
        >
          <X size={20} />
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
          <div style={{
            width: 44,
            height: 44,
            borderRadius: "50%",
            background: "#EFF6FF",
            color: "#2563EB",
            display: "flex",
            alignItems: "center",
            justifyContent: "center"
          }}>
            <CheckCircle2 size={24} />
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#0F172A" }}>
              Saved Analysis Found
            </h3>
            <p style={{ margin: 0, fontSize: 13, color: "#64748B" }}>
              This exact file has already been calculated.
            </p>
          </div>
        </div>

        <div style={{
          background: "#F8FAFC",
          border: "1px solid #E2E8F0",
          borderRadius: 10,
          padding: "14px 16px",
          marginBottom: 20
        }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: "#1E293B", marginBottom: 6 }}>
            {analysis.original_filename || "FAR File"}
          </div>
          <div style={{ fontSize: 12, color: "#64748B", display: "flex", flexDirection: "column", gap: 4 }}>
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <Clock size={13} />
              Calculated on {formatDate(analysis.created_at)}
            </span>
            {analysis.master_version && (
              <span style={{ display: "flex", alignItems: "center", gap: 6, fontFamily: "monospace" }}>
                <Hash size={13} />
                Master Version: v{analysis.master_version}
              </span>
            )}
          </div>

          <div style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 10,
            marginTop: 12,
            paddingTop: 10,
            borderTop: "1px solid #E2E8F0"
          }}>
            <div>
              <div style={{ fontSize: 11, color: "#64748B", fontWeight: 600 }}>ROWS</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#0F172A" }}>
                {(analysis.rows_total || 0).toLocaleString()}
              </div>
            </div>
            <div>
              <div style={{ fontSize: 11, color: "#64748B", fontWeight: 600 }}>REPLACEMENT VALUE</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#2563EB" }}>
                {fmtCurrency(analysis.total_replacement)}
              </div>
            </div>
          </div>
        </div>

        <p style={{ fontSize: 13, color: "#475569", margin: "0 0 20px" }}>
          Would you like to open the existing saved analysis instantly (with zero waiting time), or recalculate from scratch?
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <button
            onClick={onOpenSaved}
            style={{
              width: "100%",
              minHeight: 44,
              padding: "10px 18px",
              borderRadius: 8,
              border: "none",
              background: "#2563EB",
              color: "#fff",
              cursor: "pointer",
              fontSize: 14,
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8,
              boxShadow: "0 2px 4px rgba(37,99,235,0.2)"
            }}
          >
            Open Saved Analysis
            <ArrowRight size={16} />
          </button>

          <button
            onClick={onRecalculate}
            style={{
              width: "100%",
              minHeight: 44,
              padding: "10px 18px",
              borderRadius: 8,
              border: "1px solid #CBD5E1",
              background: "#fff",
              color: "#475569",
              cursor: "pointer",
              fontSize: 14,
              fontWeight: 500,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8
            }}
          >
            <RefreshCw size={15} />
            Recalculate Anyway
          </button>
        </div>
      </div>
    </div>
  );
}
