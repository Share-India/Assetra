import React from "react";
import { X, Download, CheckCircle2, Info, HelpCircle, FileSpreadsheet } from "lucide-react";

export default function FarColumnsHelpModal({ isOpen, onClose, apiBaseUrl }) {
  if (!isOpen) return null;

  const coreCols = [
    {
      name: "Asset Description",
      badge: "Required",
      examples: "Description, Particulars, Asset Name, Item Description, Narration",
      format: "Plain text describing the asset (e.g. 'Dell Latitude 5440 Laptop', 'CNC Lathe Machine').",
      why: "Identifies the asset and allows automatic WPI classification when no category column is present."
    },
    {
      name: "Category (Major Category / Asset Group)",
      badge: "Recommended",
      examples: "Major Cat., Asset Group, Block of Assets, Classification, Item Category, Asset Segment",
      format: "Asset group or category name (e.g. 'Plant & Machinery', 'Computers', 'Furniture & Fixtures', 'Vehicles').",
      why: "Maps assets directly to the appropriate WPI Major Category. If your file has no category column, you can choose 'No category column' to classify from the Asset Description."
    },
    {
      name: "Capitalized Date or Year",
      badge: "Required",
      examples: "Cap. Date, Date of Purchase, Date Placed in Service, Capitalization Date, Year",
      format: "Dates (e.g. 2021-06-15, 15/06/2021, 15-Jun-2021), Financial Years (FY 2021-22), or 4-digit years (2021).",
      why: "Determines the purchase financial year so the right historical Wholesale Price Index (WPI) is applied."
    },
    {
      name: "Acquisition Value (Original Cost)",
      badge: "Required",
      examples: "Acquisition Value, Original Cost, Gross Block, Purchase Cost, Cost (INR)",
      format: "Numeric purchase value (e.g. 68500, 14,50,000.00).",
      why: "Base cost multiplied by the WPI inflation ratio to compute Replacement Value."
    }
  ];

  const optionalCols = [
    { name: "Second Category Column (Sub-Category / Class)", examples: "Sub Category, Asset Class, Asset Sub-Group, Nature of Asset" },
    { name: "Asset Code / Tag No.", examples: "Asset No., Asset Code, Tag Number, Equipment ID" },
    { name: "Location / Plant", examples: "Location, Plant, Site, Branch, Cost Center" },
    { name: "Accumulated Depreciation", examples: "Accum. Dep., Total Depreciation, Dep. Reserve" },
    { name: "Net Book Value (WDV)", examples: "Book Value, Net Block, WDV" }
  ];

  return (
    <div
      id="far-columns-help-modal"
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15, 23, 42, 0.65)",
        backdropFilter: "blur(3px)",
        zIndex: 9999,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "16px"
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "#FFFFFF",
          borderRadius: 16,
          maxWidth: 780,
          width: "100%",
          maxHeight: "calc(100dvh - 32px)",
          overflowY: "auto",
          WebkitOverflowScrolling: "touch",
          boxShadow: "0 20px 35px -5px rgba(0, 0, 0, 0.25)",
          border: "1px solid #E2E8F0",
          boxSizing: "border-box"
        }}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid #E2E8F0",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
            position: "sticky",
            top: 0,
            background: "#FFFFFF",
            zIndex: 10
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: 10,
                background: "#EFF6FF",
                color: "#2563EB",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0
              }}
            >
              <HelpCircle size={20} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: "#0F172A" }}>
                What columns are needed for ASSETRA?
              </h3>
              <p style={{ margin: "2px 0 0", fontSize: 13, color: "#64748B" }}>
                Guide to required, recommended, and optional columns for ASSETRA files
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close help"
            style={{
              background: "#F8FAFC",
              border: "1px solid #E2E8F0",
              borderRadius: 8,
              width: 44,
              height: 44,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              color: "#475569",
              flexShrink: 0
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: "22px 24px" }}>
          {/* Section 1: 4 Key FAR Columns (including Category) */}
          <div style={{ marginBottom: 24 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <span
                style={{
                  background: "#FEE2E2",
                  color: "#991B1B",
                  fontSize: 11,
                  fontWeight: 700,
                  padding: "3px 8px",
                  borderRadius: 6,
                  textTransform: "uppercase"
                }}
              >
                Core FAR Columns (4 Columns)
              </span>
              <span style={{ fontSize: 14, fontWeight: 700, color: "#0F172A" }}>
                Key columns used to classify and calculate your FAR
              </span>
            </div>

            <div style={{ display: "grid", gap: 12 }}>
              {coreCols.map((col) => (
                <div
                  key={col.name}
                  style={{
                    border: "1px solid #E2E8F0",
                    borderRadius: 10,
                    padding: "14px 16px",
                    background: "#F8FAFC"
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8, marginBottom: 4 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <CheckCircle2 size={16} color={col.badge === "Required" ? "#16A34A" : "#2563EB"} />
                      <span style={{ fontSize: 14, fontWeight: 700, color: "#0F172A" }}>{col.name}</span>
                    </div>
                    <span
                      style={{
                        fontSize: 11,
                        fontWeight: 700,
                        padding: "2px 8px",
                        borderRadius: 999,
                        background: col.badge === "Required" ? "#FEE2E2" : "#DBEAFE",
                        color: col.badge === "Required" ? "#991B1B" : "#1E40AF"
                      }}
                    >
                      {col.badge}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "#334155", marginBottom: 4 }}>
                    <strong>Expected values:</strong> {col.format}
                  </div>
                  <div style={{ fontSize: 12, color: "#64748B", marginBottom: 4 }}>
                    <strong>Common header names:</strong> <em>{col.examples}</em>
                  </div>
                  <div style={{ fontSize: 12, color: "#475569" }}>
                    <strong>Why it is needed:</strong> {col.why}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Section 2: Optional Columns */}
          <div style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#0F172A", marginBottom: 10 }}>
              Additional Optional Columns
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: 10
              }}
            >
              {optionalCols.map((c) => (
                <div
                  key={c.name}
                  style={{
                    border: "1px solid #E2E8F0",
                    borderRadius: 8,
                    padding: "10px 12px",
                    background: "#F8FAFC"
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 600, color: "#0F172A" }}>{c.name}</div>
                  <div style={{ fontSize: 11, color: "#64748B", marginTop: 2 }}>{c.examples}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: "14px 24px",
            borderTop: "1px solid #E2E8F0",
            display: "flex",
            justifyContent: "flex-end",
            background: "#F8FAFC"
          }}
        >
          <button
            onClick={onClose}
            style={{
              background: "#0F172A",
              color: "#FFFFFF",
              border: "none",
              borderRadius: 8,
              padding: "10px 20px",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer"
            }}
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}

