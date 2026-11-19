import React, { useState, useMemo, useCallback, useRef, useEffect } from "react";
import * as XLSX from "xlsx";
import {
  Building2, FlaskConical, Package, Rocket, Landmark, Beaker, Truck,
  Shirt, Sun, Factory, Boxes, Upload, FileSpreadsheet, ArrowLeft,
  ArrowRight, Loader2, CheckCircle2, AlertTriangle, Search, Download,
  SlidersHorizontal, X, Info, Home, ChevronRight, ChevronDown, ListFilter,
  FileCheck, HelpCircle, RefreshCw, Play, Check, ShieldCheck, MapPin,
  LayoutGrid, Table as TableIcon, LogOut, KeyRound, User as UserIcon,
  FolderArchive, Plus, Settings, Menu
} from "lucide-react";
import LoginScreen from "./components/LoginScreen";
import SignUpScreen from "./components/SignUpScreen";
import ChangePasswordScreen from "./components/ChangePasswordScreen";
import MyAnalysesScreen from "./components/MyAnalysesScreen";
import AdminDashboardScreen from "./components/AdminDashboardScreen";
import AccountSettingsScreen from "./components/AccountSettingsScreen";
import DuplicateFileModal from "./components/DuplicateFileModal";
import ResultsStepServer from "./components/ResultsStep";
import CheckColumnsStep from "./components/CheckColumnsStep";
import FarColumnsHelpModal from "./components/FarColumnsHelpModal";
import AssetraBrandLockup from "./components/AssetraBrandLockup";

// =========================================================================
// WPI MASTER DATA
// =========================================================================
import WPI_MASTER_DATA from "./wpiMasterData.json";

// =========================================================================
// RESPONSIVE DESIGN SYSTEM & TOKENS
// =========================================================================
const FONT_IMPORT = `
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.animate-spin {
  animation: spin 0.9s linear infinite !important;
}

/* Summary Cards Grid: 1 col on mobile (<640px), 2 cols on tablet (640-1023px), 5 cols on desktop (>=1024px) */
.far-summary-cards-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}
@media (max-width: 1023px) {
  .far-summary-cards-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
    gap: 12px;
  }
}
@media (max-width: 639px) {
  .far-summary-cards-grid {
    grid-template-columns: 1fr !important;
    gap: 10px;
  }
}

/* Stepper: Desktop vs Mobile Collapse (<640px) */
.far-stepper-desktop {
  display: flex !important;
}
.far-stepper-mobile {
  display: none !important;
}
@media (max-width: 639px) {
  .far-stepper-desktop {
    display: none !important;
  }
  .far-stepper-mobile {
    display: block !important;
  }
}

/* Base button and responsive container rules */
.far-btn {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  font-weight: 500;
  font-size: 14px;
  border-radius: 6px;
  padding: 10px 20px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.far-btn-hover:hover {
  background: #F1F5F9 !important;
  border-color: #94A3B8 !important;
  color: #0F172A !important;
}


@media (max-width: 639px) {
  .far-btn-container {
    flex-direction: column !important;
    width: 100% !important;
    gap: 10px !important;
  }
  .far-btn-container > button,
  .far-btn-container > a,
  .far-btn {
    width: 100% !important;
    min-height: 44px !important;
    display: flex !important;
    justify-content: center !important;
  }
  .far-header-content {
    padding: 12px 16px !important;
  }
  .far-page-container {
    padding: 20px 14px 60px !important;
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
    box-sizing: border-box !important;
  }
  .far-card-padding {
    padding: 18px 14px !important;
  }
  .far-header-meta {
    display: none !important;
  }
}

/* Wide Tables: Horizontal scroll with sticky header and sticky first column */
.far-table-container {
  overflow-x: auto;
  max-height: 520px;
  position: relative;
  -webkit-overflow-scrolling: touch;
}
.far-table-container table {
  border-collapse: separate;
  border-spacing: 0;
  width: 100%;
}
.far-table-container thead th {
  position: sticky;
  top: 0;
  z-index: 20;
  background: #F8FAFC;
}
.far-table-container th.col-fixed,
.far-table-container td.col-fixed {
  position: sticky;
  left: 0;
  z-index: 10;
  background: #FFFFFF;
  box-shadow: 2px 0 5px -2px rgba(0, 0, 0, 0.08);
}
.far-table-container thead th.col-fixed {
  z-index: 30;
  background: #F8FAFC;
}

/* Responsive Table vs Cards (<768px) */
.far-desktop-table-view {
  display: block;
}
.far-mobile-cards-view {
  display: none;
}
@media (max-width: 767px) {
  .far-desktop-table-view {
    display: none;
  }
  .far-mobile-cards-view {
    display: block;
  }
}

/* When forced to table view on mobile */
.far-force-table .far-desktop-table-view {
  display: block !important;
}
.far-force-table .far-mobile-cards-view {
  display: none !important;
}
`;

const T = {
  navy: "#0A192F",
  blue: "#2563EB",
  blueDark: "#1D4ED8",
  blueTint: "#EFF6FF",
  green: "#10B981",
  greenTint: "#ECFDF5",
  line: "#E5E7EB",
  ink: "#111827",
  mute: "#6B7280",
  red: "#EF4444",
  redTint: "#FEF2F2",
  white: "#FFFFFF",
  bg: "#F9FAFB",
};

const WPI_GROUPS = [
  "Cement, Concrete, Bricks & Structurals",
  "Pharmaceuticals",
  "Plastic & Rubber Products",
  "All Commodities (General Index)",
  "Chemicals & Chemical Products",
  "Motor Vehicles, Trailers & Transport Equip.",
  "Textiles",
  "Electrical & Electronic Equipment",
  "Manufactured Products",
];

const INDUSTRY_LIST = [
  "Information Technology / Software", "Pharmaceuticals", "Chemicals", "Textiles",
  "Plastics & Rubber", "Machinery & Equipment", "Electrical Equipment", "Electronics / Computers",
  "Motor Vehicles", "Logistics / Transportation", "Construction / Infrastructure",
  "Real Estate", "Food Processing", "Healthcare", "Renewable Energy / Solar",
  "Metals", "Furniture", "Manufacturing - General", "Financial Services", "Other / Miscellaneous"
];

// Backend API URL from environment settings with local fallback
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL !== undefined ? import.meta.env.VITE_API_BASE_URL : "http://localhost:8001";

fetch(`${API_BASE_URL}/valid-groups`)
  .then(r => r.json())
  .then(data => {
    if (data.valid_groups && data.valid_groups.length > 0) {
      WPI_GROUPS.splice(0, WPI_GROUPS.length, ...data.valid_groups);
    }
  })
  .catch(console.error);

// Button and Card basic presets
const primaryBtn = { background: T.blue, color: "#fff", border: "none", gap: 8 };
const ghostBtn = { background: "transparent", color: T.mute, border: `1px solid ${T.line}`, gap: 8 };
const cardStyle = { background: "#fff", border: `1px solid ${T.line}`, borderRadius: 12, padding: 24, boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.05)" };
const inputStyle = { width: "100%", padding: "12px 16px", minHeight: 44, border: `1px solid ${T.line}`, borderRadius: 6, fontSize: 14, outline: "none", transition: "0.2s", boxSizing: "border-box" };

const fmtINR = (val) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(val || 0);

// =========================================================================
// PROGRESS BAR MODAL COMPONENT (Long Jobs)
// =========================================================================
function CalculationProgressModal({ jobStatus }) {
  if (!jobStatus) return null;
  const pct = Math.min(100, Math.max(0, jobStatus.progress || 0));

  return (
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: "rgba(10, 25, 47, 0.72)",
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
        padding: "32px 24px",
        maxWidth: 480,
        width: "100%",
        boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 10px 10px -5px rgba(0, 0, 0, 0.1)",
        border: `1px solid ${T.line}`,
        textAlign: "center",
        boxSizing: "border-box"
      }}>
        <div style={{
          width: 56,
          height: 56,
          borderRadius: "50%",
          background: T.blueTint,
          color: T.blue,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          margin: "0 auto 16px"
        }}>
          <Loader2 size={28} className="animate-spin" />
        </div>

        <h3 style={{ fontSize: 18, fontWeight: 700, color: T.ink, margin: "0 0 6px" }}>
          Calculating Replacement Values
        </h3>
        <p style={{ fontSize: 13, color: T.mute, margin: "0 0 20px", lineHeight: 1.4 }}>
          Processing asset register in ASSETRA using multi-stage WPI series
        </p>

        {/* Progress Bar Container */}
        <div style={{
          width: "100%",
          height: 10,
          background: "#E2E8F0",
          borderRadius: 999,
          overflow: "hidden",
          marginBottom: 10,
          position: "relative"
        }}>
          <div style={{
            width: `${pct}%`,
            height: "100%",
            background: "linear-gradient(90deg, #2563EB, #10B981)",
            borderRadius: 999,
            transition: "width 0.4s ease"
          }} />
        </div>

        {/* Percentage and Stage status message */}
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, fontWeight: 600, color: T.navy, marginBottom: 16 }}>
          <span style={{ textAlign: "left", maxWidth: "80%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {jobStatus.message || "Processing..."}
          </span>
          <span>{pct}%</span>
        </div>

        <div style={{ fontSize: 11, color: T.mute, background: "#F8FAFC", padding: "8px 12px", borderRadius: 8 }}>
          Asynchronous background worker handles large files without request timeouts.
        </div>
      </div>
    </div>
  );
}

// =========================================================================
// STEPPER (Responsive: 4 Steps: Upload, Check columns, Results, Download)
// =========================================================================
function Stepper({ currentStep, onStepClick, columnAnalysis }) {
  const steps = ["Upload", "Check columns", "Results", "Download"];
  return (
    <>
      {/* Desktop & Tablet Stepper (>= 640px) */}
      <div className="far-stepper-desktop" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 16, marginBottom: 36, overflowX: "auto", paddingBottom: 10 }}>
        {steps.map((label, idx) => {
          const stepNum = idx + 1;
          const isActive = stepNum === currentStep;
          const isPast = stepNum < currentStep;
          const isCheckColumnsAvailable = stepNum === 2 && currentStep === 1 && Boolean(columnAnalysis);
          const isClickable = (isPast || isCheckColumnsAvailable) && onStepClick;
          return (
            <div 
              key={label} 
              onClick={() => isClickable && onStepClick(stepNum)}
              style={{ 
                display: "flex", 
                alignItems: "center", 
                gap: 12,
                cursor: isClickable ? "pointer" : "default" 
              }}
              title={isClickable ? (isCheckColumnsAvailable ? `Review ${label}` : `Go back to ${label}`) : undefined}
            >
              <div style={{ 
                width: 32, height: 32, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 600,
                background: isActive ? T.blue : isPast ? T.green : "#fff",
                color: isActive || isPast ? "#fff" : T.mute,
                border: `2px solid ${isActive ? T.blue : isPast ? T.green : T.line}`,
                transition: "all 0.2s ease",
                boxShadow: isActive ? "0 0 0 3px rgba(37, 99, 235, 0.15)" : "none"
              }}>
                {isPast ? <Check size={16} /> : stepNum}
              </div>
              <span style={{ fontSize: 14, fontWeight: isActive ? 600 : 500, color: isActive ? T.ink : isPast ? "#374151" : T.mute, whiteSpace: "nowrap" }}>{label}</span>
              {idx < steps.length - 1 && <div style={{ width: 40, height: 2, background: isPast ? T.green : T.line }} />}
            </div>
          );
        })}
      </div>

      {/* Mobile Collapsed Stepper (< 640px) */}
      <div className="far-stepper-mobile" style={{
        background: "#fff",
        border: `1px solid ${T.line}`,
        borderRadius: 12,
        padding: "12px 16px",
        marginBottom: 20,
        boxShadow: "0 1px 3px rgba(0,0,0,0.05)"
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{
              background: T.blue,
              color: "#fff",
              fontSize: 12,
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: 6
            }}>
              Step {currentStep} of {steps.length}
            </span>
            <span style={{ fontSize: 14, fontWeight: 600, color: T.ink }}>
              {steps[currentStep - 1]}
            </span>
          </div>
          <span style={{ fontSize: 12, color: T.mute, fontWeight: 500 }}>
            {Math.round((currentStep / steps.length) * 100)}%
          </span>
        </div>
        <div style={{ width: "100%", height: 6, background: "#E2E8F0", borderRadius: 999, overflow: "hidden" }}>
          <div style={{
            width: `${(currentStep / steps.length) * 100}%`,
            height: "100%",
            background: "linear-gradient(90deg, #2563EB, #10B981)",
            borderRadius: 999,
            transition: "width 0.3s ease"
          }} />
        </div>
      </div>
    </>
  );
}

// -------------------------------------------------------------------------
// STEP 1: Upload (Merged Company Name + Drag-and-Drop + Chips + Calculate)
// -------------------------------------------------------------------------
function UploadStep({
  companyDetails,
  setCompanyDetails,
  selectedFile,
  setSelectedFile,
  columnAnalysis,
  setColumnAnalysis,
  isAnalyzingColumns,
  onUpload,
  onAnalyzeFile,
  onOpenReviewColumns,
  onOpenHelp,
  error,
  setError,
  apiBaseUrl
}) {
  const companyInputRef = useRef(null);
  const fileInputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Focus company name on initial load
  useEffect(() => {
    if (companyInputRef.current) {
      companyInputRef.current.focus();
    }
  }, []);

  const companyName = companyDetails?.name || "";

  const handleCompanyNameChange = (val) => {
    if (setCompanyDetails) {
      setCompanyDetails(prev => ({ ...prev, name: val }));
    }
    if (error) setError("");
  };

  const handleFile = async (file) => {
    if (!file) return;
    const name = file.name.toLowerCase();
    if (!name.endsWith(".xlsx") && !name.endsWith(".xls") && !name.endsWith(".csv") && !name.endsWith(".xlsb")) {
      setError("Invalid file format. Please upload .xlsx, .xls, .xlsb or .csv");
      return;
    }
    setError("");
    setSelectedFile(file);
    if (onAnalyzeFile) {
      await onAnalyzeFile(file);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleCalculate = async () => {
    if (!selectedFile) return;
    if (!companyName.trim()) {
      setError("Please enter a company name.");
      if (companyInputRef.current) companyInputRef.current.focus();
      return;
    }
    setUploading(true);
    try {
      let analysis = columnAnalysis;
      if (!analysis && onAnalyzeFile) {
        analysis = await onAnalyzeFile(selectedFile);
      }
      // Show "Check columns" automatically ONLY when a required field is missing or uncertain
      if (analysis && !analysis.should_skip_review) {
        onOpenReviewColumns();
        return;
      }
      const industryToPass = "All Commodities (General Index)";
      await onUpload(
        selectedFile,
        industryToPass,
        false,
        analysis?.saved_user_mapping || null,
        analysis?.header_row_index ?? 0,
        analysis?.sheet_name || ""
      );
    } finally {
      setUploading(false);
    }
  };

  // Summaries from column analysis
  const summaries = columnAnalysis?.field_summaries || [];
  const summaryByField = summaries.reduce((acc, s) => {
    acc[s.field] = s;
    return acc;
  }, {});

  const getMappedCol = (summary, fieldKey) => {
    if (!summary) return null;
    return (
      summary.mapped_column ||
      summary.detected_column ||
      columnAnalysis?.detection?.suggestions?.[fieldKey]?.mapped_column ||
      null
    );
  };

  const descSummary = summaryByField["asset_description"];
  const dateSummary = summaryByField["capitalized_date"];
  const costSummary = summaryByField["acquisition_value"];
  const catSummary = summaryByField["major_category"];
  const subSummary = summaryByField["sub_category"];

  const descCol = getMappedCol(descSummary, "asset_description");
  const dateCol = getMappedCol(dateSummary, "capitalized_date");
  const costCol = getMappedCol(costSummary, "acquisition_value");
  const catCol = getMappedCol(catSummary, "major_category");
  const subCol = getMappedCol(subSummary, "sub_category");

  // Total rows count
  const totalRowsCount = columnAnalysis?.total_rows ?? (columnAnalysis?.sample_data?.length ? columnAnalysis.sample_data.length : null);

  const isCalculateDisabled = !companyName.trim() || !selectedFile || isAnalyzingColumns || uploading;

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", width: "100%" }}>
      <div style={cardStyle} className="far-card-padding">
        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <h2 style={{ fontSize: 24, fontWeight: 700, color: T.ink, margin: "0 0 8px" }}>Upload Fixed Asset Register</h2>
          <p style={{ fontSize: 14, color: T.mute, margin: "0 0 4px" }}>
            Enter your company name and upload your asset register spreadsheet to calculate replacement values.
          </p>
        </div>

        {/* Form Field: Company Name (Required) */}
        <div style={{ marginBottom: 20 }}>
          <label htmlFor="company-name-input" style={{ display: "block", fontSize: 13, fontWeight: 600, color: T.ink, marginBottom: 6 }}>
            Company name <span style={{ color: "#DC2626" }}>*</span>
          </label>
          <input
            id="company-name-input"
            ref={companyInputRef}
            type="text"
            placeholder="e.g. BCH Electric Limited"
            value={companyName}
            onChange={(e) => handleCompanyNameChange(e.target.value)}
            autoFocus
            required
            aria-required="true"
            className="assetra-input-focus"
            style={{ ...inputStyle }}
          />
        </div>

        {error && (
          <div style={{ padding: "12px 16px", background: T.redTint, border: `1px solid #FECACA`, borderRadius: 8, color: T.red, fontSize: 13, display: "flex", alignItems: "center", gap: 8, marginBottom: 20 }}>
            <AlertTriangle size={18} />
            {error}
          </div>
        )}

        {/* Drag & Drop Zone */}
        {!selectedFile ? (
          <>
            <div 
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click(); }}
              tabIndex={0}
              role="button"
              aria-label="Upload spreadsheet: Click or drag and drop"
              className="assetra-input-focus"
              style={{
                border: `2px dashed ${isDragging ? T.blue : T.line}`,
                borderRadius: 12,
                padding: "36px 20px",
                textAlign: "center",
                background: isDragging ? T.blueTint : T.bg,
                cursor: "pointer",
                marginBottom: 16,
                transition: "all 0.2s ease"
              }}
            >
              <input 
                type="file" 
                ref={fileInputRef} 
                onChange={(e) => handleFile(e.target.files[0])} 
                style={{ display: "none" }} 
                accept=".xlsx,.xls,.csv,.xlsb"
              />
              <div style={{ width: 48, height: 48, borderRadius: "50%", background: "#fff", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 12px", boxShadow: "0 2px 4px rgba(0,0,0,0.06)" }}>
                <Upload size={22} color={T.blue} />
              </div>
              <div style={{ fontSize: 15, fontWeight: 600, color: T.ink, marginBottom: 4 }}>
                Click to upload or drag & drop FAR spreadsheet
              </div>
              <div style={{ fontSize: 13, color: T.mute }}>
                Supported formats: Excel (.xlsx, .xls, .xlsb) or CSV
              </div>
            </div>

            <div style={{ textAlign: "center", marginBottom: 8 }}>
              <button
                type="button"
                id="open-far-columns-help-btn"
                onClick={onOpenHelp}
                style={{
                  background: "none",
                  border: "none",
                  color: T.blue,
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 5,
                  padding: 4,
                  textDecoration: "underline"
                }}
              >
                <HelpCircle size={14} /> What columns are needed?
              </button>
            </div>
          </>
        ) : (
          /* File Selected Card: Progress Bar, Row Count & Found Column Chips */
          <div style={{ padding: "18px 20px", background: "#F8FAFC", border: `1px solid #CBD5E1`, borderRadius: 12, marginBottom: 20 }}>
            {/* File info row */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
                <div style={{ width: 42, height: 42, borderRadius: 8, background: "#EFF6FF", display: "flex", alignItems: "center", justifyContent: "center", color: "#2563EB", flexShrink: 0 }}>
                  <FileSpreadsheet size={24} />
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 15, fontWeight: 700, color: T.ink, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {selectedFile.name}
                  </div>
                  <div style={{ fontSize: 12, color: T.mute }}>
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                  </div>
                </div>
              </div>
              <button 
                onClick={(e) => { e.stopPropagation(); setSelectedFile(null); if (setColumnAnalysis) setColumnAnalysis(null); }} 
                title="Choose another file"
                style={{ background: "#FFFFFF", border: `1px solid #CBD5E1`, borderRadius: 6, cursor: "pointer", color: T.mute, padding: "6px 10px", fontSize: 12, fontWeight: 500, display: "inline-flex", alignItems: "center", gap: 4 }}
              >
                <X size={15} /> Remove
              </button>
            </div>

            {/* Progress Bar & Rows Read */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12, fontWeight: 600, marginBottom: 6 }}>
                <span style={{ color: isAnalyzingColumns ? "#1D4ED8" : "#166534", display: "inline-flex", alignItems: "center", gap: 6 }}>
                  {isAnalyzingColumns ? (
                    <><Loader2 size={14} className="animate-spin" /> Reading spreadsheet rows and inspecting columns...</>
                  ) : (
                    <><CheckCircle2 size={14} color="#16A34A" /> {totalRowsCount ? `${totalRowsCount.toLocaleString()} rows read` : "Spreadsheet rows read successfully"}</>
                  )}
                </span>
                <span style={{ color: isAnalyzingColumns ? "#1D4ED8" : "#166534" }}>
                  {isAnalyzingColumns ? "Analyzing..." : "100%"}
                </span>
              </div>
              <div style={{ width: "100%", height: 8, background: "#E2E8F0", borderRadius: 999, overflow: "hidden", position: "relative" }}>
                {isAnalyzingColumns ? (
                  <div style={{
                    width: "45%",
                    height: "100%",
                    background: "linear-gradient(90deg, #2563EB, #38BDF8)",
                    borderRadius: 999
                  }} className="assetra-progress-indeterminate" />
                ) : (
                  <div style={{
                    width: "100%",
                    height: "100%",
                    background: "linear-gradient(90deg, #2563EB, #10B981)",
                    borderRadius: 999,
                    transition: "width 0.4s ease"
                  }} />
                )}
              </div>
            </div>

            {/* "We found these columns" as Chips */}
            {columnAnalysis && !isAnalyzingColumns && (
              <div style={{ marginTop: 14, paddingTop: 14, borderTop: "1px solid #E2E8F0" }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: "#0F172A", marginBottom: 10 }}>
                  We found these columns:
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
                  {/* Asset Description chip */}
                  {descSummary?.status === "Found" && descCol ? (
                    <span className="assetra-chip chip-green">
                      <CheckCircle2 size={13} /> Description: &ldquo;{descCol}&rdquo;
                    </span>
                  ) : (
                    <span className="assetra-chip chip-amber">
                      <AlertTriangle size={13} /> Description: Not found
                    </span>
                  )}

                  {/* Capitalized Date chip */}
                  {dateSummary?.status === "Found" && dateCol ? (
                    <span className="assetra-chip chip-green">
                      <CheckCircle2 size={13} /> Capitalized Date: &ldquo;{dateCol}&rdquo;
                    </span>
                  ) : (
                    <span className="assetra-chip chip-amber">
                      <AlertTriangle size={13} /> Capitalized Date: Not found
                    </span>
                  )}

                  {/* Acquisition Value chip */}
                  {costSummary?.status === "Found" && costCol ? (
                    <span className="assetra-chip chip-green">
                      <CheckCircle2 size={13} /> Acquisition Value: &ldquo;{costCol}&rdquo;
                    </span>
                  ) : (
                    <span className="assetra-chip chip-amber">
                      <AlertTriangle size={13} /> Acquisition Value: Not found
                    </span>
                  )}

                  {/* Category chip: Green for found, Amber for missing category */}
                  {catSummary?.status === "Found" && catCol && catCol !== "__NO_CATEGORY__" ? (
                    <span className="assetra-chip chip-green">
                      <CheckCircle2 size={13} /> Category: &ldquo;{catCol}&rdquo;
                    </span>
                  ) : (
                    <span className="assetra-chip chip-amber">
                      <AlertTriangle size={13} /> Category: not found, we will use descriptions
                    </span>
                  )}

                  {/* Optional Sub-category chip */}
                  {subSummary?.status === "Found" && subCol && subCol !== catCol && (
                    <span className="assetra-chip chip-green">
                      <CheckCircle2 size={13} /> Sub-category: &ldquo;{subCol}&rdquo;
                    </span>
                  )}
                </div>

                {/* Sub-status notice */}
                <div style={{ marginTop: 12, display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 8 }}>
                  {!columnAnalysis.should_skip_review ? (
                    <span style={{ fontSize: 12, fontWeight: 600, color: "#92400E", display: "inline-flex", alignItems: "center", gap: 5 }}>
                      <AlertTriangle size={14} /> One or more columns need your confirmation in the next step
                    </span>
                  ) : (
                    <span style={{ fontSize: 12, fontWeight: 600, color: "#166534", display: "inline-flex", alignItems: "center", gap: 5 }}>
                      <CheckCircle2 size={14} /> All required columns detected
                    </span>
                  )}

                  <button
                    type="button"
                    id="open-far-columns-help-btn-selected"
                    onClick={onOpenHelp}
                    style={{
                      background: "none",
                      border: "none",
                      color: T.blue,
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: "pointer",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                      textDecoration: "underline",
                      padding: 0
                    }}
                  >
                    <HelpCircle size={13} /> What columns are needed?
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Action Buttons: Choose another file + Review selected columns + Calculate replacement values */}
        <div className="far-btn-container" style={{ display: "flex", gap: 12, width: "100%", marginTop: 12, flexWrap: "wrap" }}>
          {selectedFile && (
            <button 
              type="button"
              onClick={() => {
                setSelectedFile(null);
                if (setColumnAnalysis) setColumnAnalysis(null);
              }}
              style={{ 
                ...ghostBtn, 
                flex: "1 1 140px", 
                justifyContent: "center",
                color: T.ink,
                borderColor: "#CBD5E1",
                background: "#FFFFFF",
                borderRadius: 8,
                fontWeight: 500,
                minHeight: 44
              }} 
              className="far-btn far-btn-hover"
            >
              Choose another file
            </button>
          )}

          {selectedFile && columnAnalysis && (
            <button
              type="button"
              id="review-selected-columns-btn"
              onClick={onOpenReviewColumns}
              style={{
                ...ghostBtn,
                flex: "1 1 180px",
                justifyContent: "center",
                color: "#1E40AF",
                borderColor: "#BFDBFE",
                background: "#EFF6FF",
                borderRadius: 8,
                fontWeight: 600,
                minHeight: 44
              }}
              className="far-btn far-btn-hover"
              title="Inspect or adjust column mappings before calculating"
            >
              Review selected columns
            </button>
          )}

          <button 
            type="button"
            onClick={handleCalculate} 
            disabled={isCalculateDisabled} 
            style={{ 
              ...primaryBtn, 
              flex: selectedFile ? "1.5 1 200px" : "1 1 200px", 
              justifyContent: "center",
              borderRadius: 8,
              fontWeight: 600,
              minHeight: 44,
              boxShadow: !isCalculateDisabled ? "0 4px 12px rgba(37, 99, 235, 0.25)" : "none",
              opacity: isCalculateDisabled ? 0.6 : 1,
              cursor: isCalculateDisabled ? "not-allowed" : "pointer"
            }} 
            className="far-btn"
            title={!companyName.trim() ? "Please enter a Company name above" : (!selectedFile ? "Please select a file to calculate" : undefined)}
          >
            {uploading || isAnalyzingColumns ? (
              <><Loader2 className="animate-spin" size={18} /> Processing...</>
            ) : columnAnalysis && !columnAnalysis.should_skip_review ? (
              <>Check columns & Calculate <ArrowRight size={18} /></>
            ) : (
              <>Calculate replacement values <ArrowRight size={18} /></>
            )}
          </button>
        </div>

        {!companyName.trim() && selectedFile && (
          <div style={{ fontSize: 12, color: "#DC2626", textAlign: "center", marginTop: 8, fontWeight: 500 }}>
            * Please enter Company name above to enable calculation
          </div>
        )}
      </div>
    </div>
  );
}

// -------------------------------------------------------------------------
// STEP 3: Review Assets
// -------------------------------------------------------------------------
function ReviewStep({ assets, onNext, onBack, recalculate }) {
  const [isCalculating, setIsCalculating] = useState(false);
  const [page, setPage] = useState(0);
  const [forceTableMobile, setForceTableMobile] = useState(false);
  const PAGE_SIZE = 100;
  const totalPages = Math.ceil(assets.length / PAGE_SIZE) || 1;
  const visibleAssets = assets.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleNext = async () => {
    setIsCalculating(true);
    try {
      if (recalculate) {
        await recalculate();
      }
      onNext();
    } catch (e) {
      console.error(e);
      setIsCalculating(false);
    }
  };

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", width: "100%" }}>
      {/* Header section */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 20, flexWrap: "wrap", gap: 16 }}>
        <div>
          <h2 style={{ fontSize: 24, fontWeight: 700, color: T.ink, margin: "0 0 6px" }}>Review Asset Mapping</h2>
          <p style={{ fontSize: 13, color: T.mute, margin: 0 }}>Verify or adjust the suggested WPI/Commodity Groups for your assets.</p>
        </div>
        <div className="far-btn-container" style={{ display: "flex", gap: 12 }}>
          <button onClick={onBack} style={{ ...ghostBtn }} className="far-btn"><ArrowLeft size={18} /> Back</button>
          <button onClick={handleNext} disabled={isCalculating} style={{ ...primaryBtn, opacity: isCalculating ? 0.7 : 1 }} className="far-btn">
            {isCalculating ? <><Loader2 size={18} className="animate-spin" /> Calculating...</> : <>Confirm & View Results <ArrowRight size={18} /></>}
          </button>
        </div>
      </div>

      {/* Mobile view toggle button (visible on phones) */}
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <button 
          onClick={() => setForceTableMobile(!forceTableMobile)}
          style={{ ...ghostBtn, padding: "6px 12px", fontSize: 12, minHeight: 36, display: "inline-flex" }}
        >
          {forceTableMobile ? <><LayoutGrid size={14} /> View as Cards</> : <><TableIcon size={14} /> View as Table</>}
        </button>
      </div>

      <div className={`far-card-padding ${forceTableMobile ? "far-force-table" : ""}`} style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
        
        {/* Desktop & Tablet Table (Sticky header + sticky first column) */}
        <div className="far-desktop-table-view far-table-container">
          <table style={{ width: "100%", textAlign: "left", fontSize: 13 }}>
            <thead>
              <tr>
                <th className="col-fixed" style={{ padding: "14px 16px", fontWeight: 600, color: T.mute, width: 50 }}>#</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: T.mute }}>Asset Code</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: T.mute }}>Description</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: T.mute }}>Purchase Year</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: T.mute, textAlign: "right" }}>Acquisition Value</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: T.mute }}>Suggested WPI Group</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: T.mute }}>Mapping Status</th>
              </tr>
            </thead>
            <tbody>
              {visibleAssets.map((a, i) => (
                <tr key={page * PAGE_SIZE + i} style={{ borderBottom: `1px solid ${T.line}`, background: "#fff" }}>
                  <td className="col-fixed" style={{ padding: "14px 16px", color: T.mute, fontSize: 12 }}>{page * PAGE_SIZE + i + 1}</td>
                  <td style={{ padding: "14px 16px", color: T.ink, fontFamily: "monospace" }}>{a.assetCode || "N/A"}</td>
                  <td style={{ padding: "14px 16px", color: T.ink, maxWidth: 220, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={a.description}>{a.description || "-"}</td>
                  <td style={{ padding: "14px 16px", color: T.ink }}>{a.purchaseYear || "-"}</td>
                  <td style={{ padding: "14px 16px", color: T.ink, textAlign: "right" }}>{fmtINR(a.acquisitionValue)}</td>
                  <td style={{ padding: "14px 16px" }}>
                    <select 
                      style={{ ...inputStyle, padding: "6px 10px", minHeight: 36, fontSize: 12, background: T.bg, width: 220 }}
                      defaultValue={WPI_GROUPS.includes(a.wpiGroup) ? a.wpiGroup : "All Commodities (General Index)"}
                      onChange={(e) => {
                        const newGroup = e.target.value;
                        if (a.description) {
                          fetch(`${API_BASE_URL}/save-cache`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ description: a.description, category: newGroup })
                          }).catch(console.error);
                        }
                      }}
                    >
                      {WPI_GROUPS.map(g => <option key={g} value={g}>{g}</option>)}
                    </select>
                  </td>
                  <td style={{ padding: "14px 16px" }}>
                    <span style={{
                      padding: "3px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600, whiteSpace: "nowrap",
                      background: a.status === "Success" ? T.greenTint : "#FEF3C7",
                      color: a.status === "Success" ? "#065F46" : "#92400E"
                    }}>
                      {a.status || "Success"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Mobile Cards View (<768px) */}
        <div className="far-mobile-cards-view" style={{ padding: 12 }}>
          {visibleAssets.map((a, i) => {
            const rowIndex = page * PAGE_SIZE + i + 1;
            return (
              <div key={rowIndex} style={{
                background: "#fff",
                border: `1px solid ${T.line}`,
                borderRadius: 10,
                padding: "14px 14px",
                marginBottom: 10,
                boxShadow: "0 1px 3px rgba(0,0,0,0.04)"
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <span style={{ fontSize: 12, fontWeight: 700, color: T.mute, background: "#F1F5F9", padding: "2px 6px", borderRadius: 4 }}>
                    #{rowIndex} {a.assetCode && `• ${a.assetCode}`}
                  </span>
                  <span style={{
                    padding: "2px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600,
                    background: a.status === "Success" ? T.greenTint : "#FEF3C7",
                    color: a.status === "Success" ? "#065F46" : "#92400E"
                  }}>
                    {a.status || "Success"}
                  </span>
                </div>
                <div style={{ fontSize: 14, fontWeight: 600, color: T.ink, marginBottom: 8 }}>
                  {a.description || "-"}
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, fontSize: 12, background: "#F8FAFC", padding: "8px 10px", borderRadius: 6, marginBottom: 10 }}>
                  <div>
                    <span style={{ color: T.mute, display: "block" }}>Purchase Year</span>
                    <span style={{ fontWeight: 600, color: T.ink }}>{a.purchaseYear || "-"}</span>
                  </div>
                  <div>
                    <span style={{ color: T.mute, display: "block" }}>Acquisition Value</span>
                    <span style={{ fontWeight: 600, color: T.ink }}>{fmtINR(a.acquisitionValue)}</span>
                  </div>
                </div>
                <div>
                  <span style={{ fontSize: 12, color: T.mute, display: "block", marginBottom: 4 }}>WPI Group</span>
                  <select 
                    style={{ ...inputStyle, padding: "8px 10px", fontSize: 13, background: "#fff", width: "100%" }}
                    defaultValue={WPI_GROUPS.includes(a.wpiGroup) ? a.wpiGroup : "All Commodities (General Index)"}
                    onChange={(e) => {
                      const newGroup = e.target.value;
                      if (a.description) {
                        fetch(`${API_BASE_URL}/save-cache`, {
                          method: "POST",
                          headers: { "Content-Type": "application/json" },
                          body: JSON.stringify({ description: a.description, category: newGroup })
                        }).catch(console.error);
                      }
                    }}
                  >
                    {WPI_GROUPS.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                </div>
              </div>
            );
          })}
        </div>

        {/* Pagination Bar */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 18px", borderTop: `1px solid ${T.line}`, background: "#FAFAFA", flexWrap: "wrap", gap: 10 }}>
          <div style={{ fontSize: 13, color: T.mute }}>
            Showing {assets.length === 0 ? 0 : page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, assets.length)} of {assets.length.toLocaleString("en-IN")} assets
          </div>
          {totalPages > 1 && (
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                style={{ ...ghostBtn, padding: "5px 12px", fontSize: 12, minHeight: 32, opacity: page === 0 ? 0.4 : 1 }}
              >
                ← Prev
              </button>
              <span style={{ fontSize: 13, color: T.mute }}>Page {page + 1} / {totalPages}</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page === totalPages - 1}
                style={{ ...primaryBtn, padding: "5px 12px", fontSize: 12, minHeight: 32, opacity: page === totalPages - 1 ? 0.4 : 1 }}
              >
                Next →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// -------------------------------------------------------------------------
// STEP 4: Results Step (Replacement Value Dashboard)
// -------------------------------------------------------------------------
function StatCard({ title, value, sub, highlight, badge, tooltip }) {
  return (
    <div
      style={{
        background: highlight ? T.navy : "#fff",
        color: highlight ? "#fff" : T.ink,
        border: highlight ? `1px solid ${T.navy}` : `1px solid ${T.line}`,
        borderRadius: 14,
        padding: "16px 14px",
        display: "flex",
        flexDirection: "column",
        boxSizing: "border-box",
        minWidth: 0,
        boxShadow: "0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05)",
        height: "100%"
      }}
      title={tooltip || (typeof value === "string" ? value : undefined)}
    >
      <div style={{
        fontSize: 12,
        color: highlight ? "#9CA3AF" : T.mute,
        fontWeight: 600,
        marginBottom: 8,
        whiteSpace: "nowrap",
        overflow: "hidden",
        textOverflow: "ellipsis"
      }}>
        {title}
      </div>
      <div style={{
        fontSize: "clamp(16px, 1.25vw, 19px)",
        fontWeight: 700,
        margin: "0 0 6px",
        color: highlight ? "#fff" : T.ink,
        whiteSpace: "nowrap",
        minWidth: 0,
        fontVariantNumeric: "tabular-nums"
      }} title={tooltip || (typeof value === "string" ? value : undefined)}>
        {value}
      </div>
      <div style={{
        fontSize: 11,
        color: highlight ? "#D1D5DB" : T.mute,
        marginTop: "auto",
        display: "flex",
        alignItems: "center",
        flexWrap: "wrap",
        gap: 6,
        whiteSpace: "nowrap"
      }}>
        {sub && <span>{sub}</span>}
        {badge}
      </div>
    </div>
  );
}

function ResultsStep({ assets, companyDetails, selectedFile, onNext, onBack }) {
  const [page, setPage] = useState(0);
  const [forceTableMobile, setForceTableMobile] = useState(false);
  const PAGE_SIZE = 100;

  const totals = useMemo(() => {
    let acq = 0;
    let rep = 0;
    let wpiCount = 0;
    let buildingCount = 0;
    let calculatedCount = 0;
    let maxYear = 2025;
    
    assets.forEach(a => {
      const aAcq = Number(a.acquisitionValue) || 0;
      const aRep = Number(a.replacementValue) || 0;
      acq += aAcq;
      rep += aRep;
      
      const pYear = Number(a.purchaseYear);
      if (pYear && pYear > maxYear && pYear <= 2030) maxYear = pYear;
      const cYear = Number(a.calculationYear) || Number(a.currentYear);
      if (cYear && cYear > maxYear && cYear <= 2030) maxYear = cYear;

      const m = String(a.calculationMethod || "");
      const isBuilding = a.wpiGroup === "Building" || a.wpiGroup === "Land" || m.includes("5%") || m.includes("Compound") || m.includes("Escalation");
      
      if (isBuilding) {
        buildingCount += 1;
        calculatedCount += 1;
      } else {
        wpiCount += 1;
        calculatedCount += 1;
      }
    });

    const diff = rep - acq;
    const diffPct = acq > 0 ? (diff / acq) * 100 : 0;

    return {
      count: assets.length,
      calculatedCount,
      wpiCount,
      buildingCount,
      acq,
      rep,
      diff,
      diffPct,
      latestYear: maxYear
    };
  }, [assets]);

  const hasAssetCodes = useMemo(() => {
    return assets.some(a => a.assetCode && String(a.assetCode).trim() !== "");
  }, [assets]);

  const displayedAssets = assets;
  const totalPages = Math.ceil(displayedAssets.length / PAGE_SIZE) || 1;
  const pagedAssets = useMemo(() => {
    return displayedAssets.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  }, [displayedAssets, page]);

  const renderMethodPill = (method, status) => {
    const m = String(method || "");
    const s = String(status || "");
    
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

  const getWpiTooltip = (a) => {
    const p = (a.purchaseWpi != null && a.purchaseWpi !== "") ? a.purchaseWpi : "-";
    const c = (a.currentWpi != null && a.currentWpi !== "") ? a.currentWpi : "-";
    return `Series data: Purch WPI ${p}, Curr WPI ${c}`;
  };

  return (
    <div style={{ maxWidth: 1400, margin: "0 auto", width: "100%" }}>
      {/* HEADER SECTION */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 20, flexWrap: "wrap", gap: 16 }}>
        <div>
          <h2 style={{ fontSize: 24, fontWeight: 700, color: T.ink, margin: "0 0 6px" }}>Replacement Value Dashboard</h2>
          <p style={{ fontSize: 13, color: T.mute, margin: 0 }}>Calculated using linked WPI series, 1954 to {totals.latestYear}</p>
        </div>
        <div className="far-btn-container" style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <button onClick={onBack} style={{ ...ghostBtn }} className="far-btn"><ArrowLeft size={18} /> Back</button>
          <button onClick={onNext} style={{ ...primaryBtn }} className="far-btn">Proceed to Download <ArrowRight size={18} /></button>
        </div>
      </div>

      {/* SUMMARY CARDS (1 / 2 / 5 columns responsive) */}
      <div className="far-summary-cards-grid">
        <StatCard 
          title="Total Assets" 
          value={totals.count.toLocaleString("en-IN")} 
          sub="All rows in file" 
        />
        <StatCard 
          title="Calculated Assets" 
          value={totals.calculatedCount.toLocaleString("en-IN")} 
          sub="Incl. all buildings & WPI" 
        />
        <StatCard 
          title="Total Acquisition Value" 
          value={fmtINR(totals.acq)} 
          sub="Historical cost basis" 
        />
        <StatCard 
          title="Total Replacement Value" 
          value={fmtINR(totals.rep)} 
          sub="Current replacement cost" 
          highlight={true} 
        />
        <StatCard 
          title="Total Difference" 
          value={fmtINR(totals.diff)} 
          badge={
            <span style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 4,
              padding: "2px 8px",
              borderRadius: 6,
              fontSize: 11,
              fontWeight: 600,
              background: totals.diff >= 0 ? "#DCFCE7" : "#FEE2E2",
              color: totals.diff >= 0 ? "#15803D" : "#B91C1C",
              border: totals.diff >= 0 ? "1px solid #BBF7D0" : "1px solid #FECACA",
              whiteSpace: "nowrap"
            }}>
              {totals.diff >= 0 ? "+" : ""}{totals.diffPct.toFixed(1)}% vs Acquisition
            </span>
          }
        />
      </div>

      {/* STATUS STRIP */}
      <div style={{
        background: "#fff",
        border: `1px solid ${T.line}`,
        borderRadius: 12,
        padding: "12px 18px",
        marginBottom: 20,
        boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.03)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: 12,
        fontSize: 13,
        color: T.ink
      }}>
        <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: "8px 12px" }}>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <span style={{ color: "#059669", fontSize: 10 }}>●</span>
            <span><strong>{totals.calculatedCount.toLocaleString("en-IN")}</strong> total calculated assets (incl. all buildings)</span>
          </span>
          <span style={{ color: T.line, fontSize: 10 }}>●</span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <span style={{ color: T.blue, fontSize: 10 }}>●</span>
            <span><strong>{totals.wpiCount.toLocaleString("en-IN")}</strong> via WPI</span>
          </span>
          <span style={{ color: T.line, fontSize: 10 }}>●</span>
          <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
            <span style={{ color: "#8B5CF6", fontSize: 10 }}>●</span>
            <span><strong>{totals.buildingCount.toLocaleString("en-IN")}</strong> buildings via 5% compound</span>
          </span>
        </div>
        <div>
          <button 
            onClick={() => setForceTableMobile(!forceTableMobile)}
            style={{ ...ghostBtn, padding: "5px 10px", fontSize: 12, minHeight: 32 }}
          >
            {forceTableMobile ? <><LayoutGrid size={14} /> View as Cards</> : <><TableIcon size={14} /> View as Table</>}
          </button>
        </div>
      </div>

      {/* RESULTS TABLE & MOBILE CARDS CONTAINER */}
      <div className={`far-card-padding ${forceTableMobile ? "far-force-table" : ""}`} style={{ ...cardStyle, padding: 0, overflow: "hidden" }}>
        
        {/* DESKTOP/TABLET TABLE: Horizontal scroll, sticky header and sticky first column */}
        <div className="far-desktop-table-view far-table-container">
          <table style={{ textAlign: "left", fontSize: 13 }}>
            <thead>
              <tr>
                <th className="col-fixed" style={{ padding: "14px 16px", fontWeight: 600, color: T.mute, width: 44 }}>#</th>
                {hasAssetCodes && (
                  <th style={{ padding: "14px 16px", fontWeight: 600, color: T.mute }}>Asset Code</th>
                )}
                <th style={{ padding: "14px 16px", fontWeight: 600, color: T.mute }}>Description</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: T.mute }}>Year</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: T.mute, textAlign: "right" }}>Acq Value</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: T.mute }}>WPI Group</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: T.mute }}>Method</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: T.blue, textAlign: "right" }}>Replacement</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: T.mute, textAlign: "right" }}>Difference</th>
                <th style={{ padding: "14px 16px", fontWeight: 600, color: T.mute, textAlign: "center" }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {pagedAssets.map((a, i) => {
                const diff = (Number(a.replacementValue) || 0) - (Number(a.acquisitionValue) || 0);
                const rowIndex = page * PAGE_SIZE + i + 1;
                return (
                  <tr key={rowIndex} style={{ borderBottom: `1px solid ${T.line}`, background: "#fff" }}>
                    <td className="col-fixed" style={{ padding: "14px 16px", color: T.mute, fontSize: 12 }}>{rowIndex}</td>
                    {hasAssetCodes && (
                      <td style={{ padding: "14px 16px", color: T.ink, fontFamily: "monospace", fontSize: 12 }}>
                        {a.assetCode || "-"}
                      </td>
                    )}
                    <td style={{
                      padding: "14px 16px",
                      color: T.ink,
                      maxWidth: 240,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis"
                    }} title={a.description || "-"}>
                      {a.description || "-"}
                    </td>
                    <td style={{ padding: "14px 16px", color: T.ink, fontVariantNumeric: "tabular-nums" }}>
                      {a.purchaseYear || "-"}
                    </td>
                    <td style={{ padding: "14px 16px", color: T.ink, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                      {fmtINR(a.acquisitionValue)}
                    </td>
                    <td style={{
                      padding: "14px 16px",
                      color: T.mute,
                      maxWidth: 160,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis"
                    }} title={a.wpiGroup || "-"}>
                      {a.wpiGroup || "-"}
                    </td>
                    <td style={{ padding: "14px 16px" }}>
                      {renderMethodPill(a.calculationMethod, a.status)}
                    </td>
                    <td style={{
                      padding: "14px 16px",
                      color: T.ink,
                      fontWeight: 600,
                      textAlign: "right",
                      background: T.blueTint,
                      fontVariantNumeric: "tabular-nums"
                    }} title={getWpiTooltip(a)}>
                      {fmtINR(a.replacementValue)}
                    </td>
                    <td style={{
                      padding: "14px 16px",
                      textAlign: "right",
                      fontVariantNumeric: "tabular-nums",
                      fontWeight: 600,
                      color: diff > 0 ? "#15803D" : diff < 0 ? "#B91C1C" : T.mute
                    }}>
                      {diff !== 0 ? (diff > 0 ? `+${fmtINR(diff)}` : fmtINR(diff)) : "₹0.00"}
                    </td>
                    <td style={{ padding: "14px 16px", color: T.mute, textAlign: "center" }}>
                      <span style={{
                        padding: "3px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600, whiteSpace: "nowrap",
                        background: T.greenTint,
                        color: "#065F46"
                      }}>
                        Success
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* MOBILE CARDS VIEW (<768px): clean card layout */}
        <div className="far-mobile-cards-view" style={{ padding: 12 }}>
          {pagedAssets.map((a, i) => {
            const diff = (Number(a.replacementValue) || 0) - (Number(a.acquisitionValue) || 0);
            const rowIndex = page * PAGE_SIZE + i + 1;
            return (
              <div key={rowIndex} style={{
                background: "#fff",
                border: `1px solid ${T.line}`,
                borderRadius: 10,
                padding: "14px 14px",
                marginBottom: 10,
                boxShadow: "0 1px 3px rgba(0,0,0,0.04)"
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <span style={{ fontSize: 12, fontWeight: 700, color: T.mute, background: "#F1F5F9", padding: "2px 6px", borderRadius: 4 }}>
                      #{rowIndex}
                    </span>
                    {a.assetCode && (
                      <span style={{ fontSize: 12, fontFamily: "monospace", color: T.ink, fontWeight: 600 }}>
                        {a.assetCode}
                      </span>
                    )}
                  </div>
                  {renderMethodPill(a.calculationMethod, a.status)}
                </div>

                <div style={{ fontSize: 14, fontWeight: 600, color: T.ink, marginBottom: 10, lineHeight: 1.4 }}>
                  {a.description || "-"}
                </div>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px 10px", fontSize: 12, background: "#F8FAFC", padding: "10px 12px", borderRadius: 8, marginBottom: 10 }}>
                  <div>
                    <span style={{ color: T.mute, display: "block" }}>Purchase Year</span>
                    <span style={{ fontWeight: 600, color: T.ink }}>{a.purchaseYear || "-"}</span>
                  </div>
                  <div>
                    <span style={{ color: T.mute, display: "block" }}>WPI Group</span>
                    <span style={{ fontWeight: 500, color: T.ink, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "block" }} title={a.wpiGroup}>
                      {a.wpiGroup || "-"}
                    </span>
                  </div>
                  <div>
                    <span style={{ color: T.mute, display: "block" }}>Acquisition Value</span>
                    <span style={{ fontWeight: 600, color: T.ink }}>{fmtINR(a.acquisitionValue)}</span>
                  </div>
                  <div>
                    <span style={{ color: T.mute, display: "block" }}>Replacement Value</span>
                    <span style={{ fontWeight: 700, color: T.blue }}>{fmtINR(a.replacementValue)}</span>
                  </div>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12 }}>
                  <span style={{ color: T.mute }}>Difference:</span>
                  <span style={{ fontWeight: 600, color: diff >= 0 ? "#15803D" : "#B91C1C" }}>
                    {diff >= 0 ? "+" : ""}{fmtINR(diff)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* PAGINATION BAR */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px", borderTop: `1px solid ${T.line}`, background: "#FAFAFA", flexWrap: "wrap", gap: 10 }}>
          <div style={{ fontSize: 13, color: T.mute }}>
            Showing {displayedAssets.length === 0 ? 0 : page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, displayedAssets.length)} of {displayedAssets.length.toLocaleString("en-IN")} assets
          </div>
          {totalPages > 1 && (
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                style={{ ...ghostBtn, padding: "5px 12px", fontSize: 12, minHeight: 32, opacity: page === 0 ? 0.4 : 1 }}
              >
                ← Prev
              </button>
              <span style={{ fontSize: 13, color: T.mute }}>Page {page + 1} / {totalPages}</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page === totalPages - 1}
                style={{ ...primaryBtn, padding: "5px 12px", fontSize: 12, minHeight: 32, opacity: page === totalPages - 1 ? 0.4 : 1 }}
              >
                Next →
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// -------------------------------------------------------------------------
// STEP 5: Download
// -------------------------------------------------------------------------
function DownloadStep({ downloadUrl, onRestart, onBack, onNewCompany }) {
  const handleDownload = () => {
    if (!downloadUrl) return;
    const a = document.createElement("a");
    a.href = `${API_BASE_URL}${downloadUrl}`;
    a.download = `ASSETRA_With_Replacement_Value.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  return (
    <div style={{ maxWidth: 540, margin: "0 auto", width: "100%" }}>
      <div style={{ ...cardStyle, textAlign: "center", padding: "40px 28px" }} className="far-card-padding">
        <div style={{
          width: 76,
          height: 76,
          borderRadius: "50%",
          background: T.greenTint,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          margin: "0 auto 20px",
          border: "2px solid #BBF7D0",
          boxShadow: "0 4px 12px rgba(16, 185, 129, 0.12)"
        }}>
          <CheckCircle2 size={42} color={T.green} />
        </div>
        <h2 style={{ fontSize: 24, fontWeight: 700, color: T.ink, margin: "0 0 10px" }}>Calculation Complete!</h2>
        <p style={{ fontSize: 14, color: T.mute, margin: "0 0 28px", lineHeight: 1.6 }}>
          Your asset register has been successfully processed by ASSETRA. The replacement values, WPI indexes, and calculations have been appended to your report.
        </p>
        
        {downloadUrl ? (
          <button 
            onClick={handleDownload} 
            style={{ 
              ...primaryBtn, 
              width: "100%", 
              justifyContent: "center", 
              padding: "14px 20px", 
              fontSize: 15,
              fontWeight: 600,
              borderRadius: 8,
              boxShadow: "0 4px 12px rgba(37, 99, 235, 0.25)"
            }} 
            className="far-btn"
          >
            <Download size={20} /> Download Updated FAR
          </button>
        ) : (
          <div style={{ padding: "12px", background: T.redTint, color: T.red, borderRadius: 8, fontSize: 14 }}>
            Download link unavailable. Please try calculating again.
          </div>
        )}
        
        <div className="far-btn-container" style={{ display: "flex", gap: 12, marginTop: 16, width: "100%" }}>
          <button 
            onClick={onBack} 
            style={{ 
              ...ghostBtn, 
              flex: 1, 
              justifyContent: "center", 
              color: T.ink, 
              borderColor: "#CBD5E1", 
              background: "#FFFFFF",
              borderRadius: 8,
              fontWeight: 500
            }} 
            className="far-btn far-btn-hover"
            title="Return to Results Dashboard"
          >
            <ArrowLeft size={18} /> Back
          </button>
          <button 
            onClick={onRestart} 
            style={{ 
              ...ghostBtn, 
              flex: 1, 
              justifyContent: "center", 
              color: T.navy, 
              borderColor: "#CBD5E1", 
              background: "#F8FAFC",
              borderRadius: 8,
              fontWeight: 600
            }} 
            className="far-btn far-btn-hover"
            title="Upload and calculate another FAR file"
          >
            <RefreshCw size={16} /> Calculate Another FAR
          </button>
        </div>

        <div style={{ marginTop: 22, paddingTop: 16, borderTop: `1px solid ${T.line}` }}>
          <button
            onClick={onNewCompany}
            style={{
              background: "none",
              border: "none",
              color: T.mute,
              fontSize: 13,
              cursor: "pointer",
              padding: "4px 8px",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              textDecoration: "underline"
            }}
          >
            Or start fresh with a new company
          </button>
        </div>
      </div>
    </div>
  );
}

// -------------------------------------------------------------------------
// MAIN APP COMPONENT
// -------------------------------------------------------------------------
export default function FarCalculatorApp() {
  const [step, setStep] = useState(1);
  const [companyDetails, setCompanyDetails] = useState({});
  const [assets, setAssets] = useState([]);
  const [downloadUrl, setDownloadUrl] = useState(null);
  const [error, setError] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  
  // Phase 2 State: Views & Saved Analyses
  const [currentView, setCurrentView] = useState("calculator"); // "calculator" | "my_analyses" | "admin_dashboard"
  const [currentAnalysisId, setCurrentAnalysisId] = useState(null);
  const [duplicateAnalysis, setDuplicateAnalysis] = useState(null);

  // Authentication & Session State
  const [authScreen, setAuthScreen] = useState(() => {
    if (typeof window !== "undefined" && (window.location.hash === "#signup" || window.location.search.includes("signup"))) {
      return "signup";
    }
    return "login";
  });
  const [token, setToken] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [sessionExpiredMessage, setSessionExpiredMessage] = useState("");
  const [idleTimeoutMinutes, setIdleTimeoutMinutes] = useState(30);
  const lastActivityRef = useRef(Date.now());
  const tokenRef = useRef(null);
  const [showChangePasswordModal, setShowChangePasswordModal] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Dynamic Browser Tab Title per screen/step
  useEffect(() => {
    let pageTitle = "Assetra";
    if (currentView === "my_analyses") {
      pageTitle = "My Analyses | Assetra";
    } else if (currentView === "admin_dashboard") {
      pageTitle = "Admin Dashboard | Assetra";
    } else if (currentView === "account_settings") {
      pageTitle = "Account Settings | Assetra";
    } else if (currentView === "calculator") {
      if (step === 1) pageTitle = "Upload | Assetra";
      else if (step === 2) pageTitle = "Check Columns | Assetra";
      else if (step === 3) pageTitle = "Results | Assetra";
      else if (step === 4) pageTitle = "Download | Assetra";
    }
    document.title = pageTitle;
  }, [currentView, step]);

  // Dedicated Administrator Session State (strictly decoupled from normal user session)
  const [adminToken, setAdminToken] = useState(() => sessionStorage.getItem("far_admin_token") || null);
  const [adminUser, setAdminUser] = useState(() => {
    try {
      const saved = sessionStorage.getItem("far_admin_user");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  useEffect(() => {
    tokenRef.current = token;
  }, [token]);

  const clearAllAuthAndAnalysisState = useCallback(() => {
    tokenRef.current = null;
    localStorage.removeItem("far_auth_token");
    localStorage.removeItem("far_user");
    sessionStorage.removeItem("far_auth_token");
    sessionStorage.removeItem("far_user");
    sessionStorage.removeItem("far_admin_token");
    sessionStorage.removeItem("far_admin_user");
    setToken(null);
    setCurrentUser(null);
    setAdminToken(null);
    setAdminUser(null);
    setCurrentAnalysisId(null);
    setAssets([]);
    setCompanyDetails({});
    setSelectedFile(null);
    setDuplicateAnalysis(null);
    setDownloadUrl(null);
    setError("");
    setStep(1);
    setCurrentView("calculator");
    setAuthScreen("login");
  }, []);

  // Verify auth session on initial load via httpOnly cookie
  useEffect(() => {
    // Clean up any legacy localStorage token so cookie lifetime (session vs REMEMBER_ME_DAYS) governs persistence
    localStorage.removeItem("far_auth_token");
    localStorage.removeItem("far_user");

    const checkAuth = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/auth/me`, {
          credentials: "include"
        });
        if (res.ok) {
          const data = await res.json();
          const userObj = data.user || data;
          const activeToken = data.token || "cookie-session";
          tokenRef.current = activeToken;
          setCurrentUser(userObj);
          setToken(activeToken);
          if (data.idle_timeout_minutes) {
            setIdleTimeoutMinutes(Number(data.idle_timeout_minutes) || 30);
          }
          lastActivityRef.current = Date.now();
          if (userObj.role === "admin") {
            setAdminToken(activeToken);
            setAdminUser(userObj);
            sessionStorage.setItem("far_admin_token", activeToken);
            sessionStorage.setItem("far_admin_user", JSON.stringify(userObj));
            const currentHash = window.location.hash;
            if (!currentHash || currentHash === "#calculator" || currentHash === "#admin") {
              setCurrentView("admin_dashboard");
              window.location.hash = "#admin";
            }
          } else {
            sessionStorage.removeItem("far_admin_token");
            sessionStorage.removeItem("far_admin_user");
            setAdminToken(null);
            setAdminUser(null);
            const currentHash = window.location.hash;
            if (currentHash === "#admin") {
              setCurrentView("calculator");
              window.location.hash = "#calculator";
            }
          }
          setCurrentAnalysisId(null);
          setCompanyDetails({});
          setSelectedFile(null);
          setStep(1);
        } else {
          clearAllAuthAndAnalysisState();
        }
      } catch (e) {
        console.error("Auth check failed:", e);
        clearAllAuthAndAnalysisState();
      } finally {
        setAuthLoading(false);
      }
    };
    checkAuth();
  }, [clearAllAuthAndAnalysisState]);

  const expireSessionDueToIdle = useCallback(async () => {
    const activeToken = tokenRef.current;
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        credentials: "include",
        headers: activeToken ? { Authorization: `Bearer ${activeToken}` } : {}
      });
    } catch (e) {
      // Best effort
    }
    clearAllAuthAndAnalysisState();
    setSessionExpiredMessage("Your session expired, please sign in again.");
    window.history.replaceState({ loggedOut: true }, "", window.location.pathname);
  }, [clearAllAuthAndAnalysisState]);

  // Track user activity and enforce IDLE_TIMEOUT_MINUTES
  useEffect(() => {
    if (!token || !currentUser) return;

    lastActivityRef.current = Date.now();
    const updateActivity = () => {
      lastActivityRef.current = Date.now();
    };

    const activityEvents = ["mousemove", "mousedown", "keydown", "scroll", "touchstart", "click"];
    activityEvents.forEach((evt) => window.addEventListener(evt, updateActivity, { passive: true }));

    const timeoutMs = (Number(idleTimeoutMinutes) || 30) * 60 * 1000;
    const intervalId = setInterval(() => {
      if (Date.now() - lastActivityRef.current >= timeoutMs) {
        clearInterval(intervalId);
        expireSessionDueToIdle();
      }
    }, 1000);

    return () => {
      activityEvents.forEach((evt) => window.removeEventListener(evt, updateActivity));
      clearInterval(intervalId);
    };
  }, [token, currentUser, idleTimeoutMinutes, expireSessionDueToIdle]);

  // Prevent browser Back button or bfcache from showing data after logout
  useEffect(() => {
    const handlePopState = () => {
      if (!tokenRef.current) {
        clearAllAuthAndAnalysisState();
        window.history.replaceState({ loggedOut: true }, "", window.location.pathname);
      }
    };
    const handlePageShow = (event) => {
      if (event.persisted && !tokenRef.current) {
        clearAllAuthAndAnalysisState();
      }
    };
    window.addEventListener("popstate", handlePopState);
    window.addEventListener("pageshow", handlePageShow);
    return () => {
      window.removeEventListener("popstate", handlePopState);
      window.removeEventListener("pageshow", handlePageShow);
    };
  }, [clearAllAuthAndAnalysisState]);

  const handleLoginSuccess = (newToken, user, _rememberMe = false, serverIdleMinutes = 30) => {
    tokenRef.current = newToken || "cookie-session";
    localStorage.removeItem("far_auth_token");
    localStorage.removeItem("far_user");
    setSessionExpiredMessage("");
    setToken(newToken || "cookie-session");
    setCurrentUser(user);
    if (serverIdleMinutes) {
      setIdleTimeoutMinutes(Number(serverIdleMinutes) || 30);
    }
    lastActivityRef.current = Date.now();
    if (user?.role === "admin") {
      const activeAdminTok = newToken || "cookie-session";
      setAdminToken(activeAdminTok);
      setAdminUser(user);
      sessionStorage.setItem("far_admin_token", activeAdminTok);
      sessionStorage.setItem("far_admin_user", JSON.stringify(user));
      setCurrentView("admin_dashboard");
      window.location.hash = "#admin";
    } else {
      sessionStorage.removeItem("far_admin_token");
      sessionStorage.removeItem("far_admin_user");
      setAdminToken(null);
      setAdminUser(null);
      setCurrentView("calculator");
      window.location.hash = "#calculator";
    }
  };

  const refreshUser = async () => {
    if (!token) return;
    try {
      const res = await fetch(`${API_BASE_URL}/auth/me`, {
        credentials: "include",
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      if (res.ok) {
        const data = await res.json();
        const userObj = data.user || data;
        setCurrentUser(userObj);
      } else if (res.status === 401) {
        expireSessionDueToIdle();
      }
    } catch (e) {
      console.error("Failed to refresh user profile:", e);
    }
  };

  const handleLogout = async () => {
    const activeToken = token || adminToken;
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: "POST",
        credentials: "include",
        headers: activeToken ? { Authorization: `Bearer ${activeToken}` } : {}
      });
    } catch (e) {
      // Best effort
    }
    clearAllAuthAndAnalysisState();
    setSessionExpiredMessage("");
    window.location.hash = "";
    window.history.replaceState({ loggedOut: true }, "", window.location.pathname);
    window.history.pushState({ loggedOut: true }, "", window.location.pathname);
  };

  const handlePasswordChanged = () => {
    setShowChangePasswordModal(false);
    if (currentUser) {
      const updated = { ...currentUser, must_change_password: false };
      setCurrentUser(updated);
      localStorage.setItem("far_user", JSON.stringify(updated));
    }
  };

  // Handle Admin Portal navigation / Gate
  const handleAdminClick = () => {
    if (currentView === "admin_dashboard") {
      setCurrentView("calculator");
      window.location.hash = "#calculator";
    } else {
      setCurrentView("admin_dashboard");
      window.location.hash = "#admin";
    }
  };

  // Synchronize route hash with active view and gate admin
  useEffect(() => {
    const handleHashChange = () => {
      const hash = window.location.hash;
      const isDirectAdminRoute = hash === "#admin" || window.location.pathname === "/admin";
      if (isDirectAdminRoute) {
        if ((adminToken && adminUser && adminUser.role === "admin") || (currentUser && currentUser.role === "admin")) {
          setCurrentView("admin_dashboard");
        } else if (token && currentUser) {
          // Normal user accessing admin view directly -> shows Access Denied card
          setCurrentView("admin_dashboard");
        }
      } else if (hash === "#my-analyses") {
        setCurrentView("my_analyses");
      } else if (hash === "#account-settings") {
        setCurrentView("account_settings");
      } else if (hash === "#calculator") {
        setCurrentView("calculator");
      }
    };

    handleHashChange();
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, [adminToken, adminUser, token, currentUser, currentView]);

  // Long Jobs / Background Task State + Column Review State
  const [jobStatus, setJobStatus] = useState(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [columnAnalysis, setColumnAnalysis] = useState(null);
  const [isAnalyzingColumns, setIsAnalyzingColumns] = useState(false);
  const [showColumnsHelpModal, setShowColumnsHelpModal] = useState(false);

  const analyzeFileColumns = useCallback(async (file, customHeaderRowIdx = null) => {
    if (!file) return null;
    setIsAnalyzingColumns(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (customHeaderRowIdx !== null && customHeaderRowIdx !== undefined) {
        formData.append("header_row_index", String(customHeaderRowIdx));
      }
      const res = await fetch(`${API_BASE_URL}/analyze-columns`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Failed to analyze file columns (HTTP ${res.status})`);
      }
      const data = await res.json();
      setColumnAnalysis(data);
      return data;
    } catch (err) {
      console.error("Column analysis error:", err);
      setError(err.message || "Could not analyze spreadsheet columns.");
      return null;
    } finally {
      setIsAnalyzingColumns(false);
    }
  }, [token]);

  const handleUpload = async (
    file,
    industry,
    recalculate = false,
    customUserMapping = null,
    customHeaderRowIndex = null,
    customSheetName = null
  ) => {
    setIsCalculating(true);
    setError("");
    setJobStatus({ progress: 5, message: "Queuing calculation job..." });

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("wpiGroup", industry || "All Commodities (General Index)");
      formData.append("companyName", companyDetails?.name || file.name.replace(/\.[^/.]+$/, ""));
      formData.append("industry", companyDetails?.industry?.[0] || industry || "");
      if (customUserMapping && Object.keys(customUserMapping).length > 0) {
        formData.append("userMapping", JSON.stringify(customUserMapping));
      } else {
        formData.append("userMapping", "{}");
      }
      if (customHeaderRowIndex !== null && customHeaderRowIndex !== undefined) {
        formData.append("headerRowIndex", String(customHeaderRowIndex));
      }
      if (customSheetName) {
        formData.append("sheetName", customSheetName);
      }
      if (recalculate) {
        formData.append("recalculate", "true");
      }

      // 1. Submit calculation job to /calculate-job
      const startRes = await fetch(`${API_BASE_URL}/calculate-job`, {
        method: "POST",
        headers: token ? { "Authorization": `Bearer ${token}` } : {},
        body: formData,
      });

      if (!startRes.ok) {
        const errData = await startRes.json().catch(() => ({}));
        throw new Error(errData.detail || `Upload failed with HTTP ${startRes.status}`);
      }

      const startData = await startRes.json();

      // Handle duplicate file detected shortcut
      if (startData.duplicate_found) {
        setIsCalculating(false);
        setJobStatus(null);
        setDuplicateAnalysis(startData);
        return;
      }

      const { job_id, analysis_id } = startData;
      if (!job_id) {
        throw new Error("Server did not return a valid Job ID.");
      }
      if (analysis_id) {
        setCurrentAnalysisId(analysis_id);
      }

      // 2. Poll for progress updates until finished or error
      let completed = false;
      let finalResult = null;
      let pollCount = 0;
      const maxPolls = 1000;

      while (!completed && pollCount < maxPolls) {
        await new Promise(r => setTimeout(r, 600));
        pollCount++;

        const statusRes = await fetch(`${API_BASE_URL}/calculate-job/${job_id}`);
        if (!statusRes.ok) continue;

        const jobData = await statusRes.json();
        setJobStatus({
          progress: jobData.progress || 0,
          message: jobData.message || "Processing asset data...",
          status: jobData.status
        });

        if (jobData.status === "completed") {
          completed = true;
          finalResult = jobData.result;
          const returnedAnalysisId = jobData.analysis_id || finalResult?.analysis_id || analysis_id;
          if (returnedAnalysisId) {
            setCurrentAnalysisId(returnedAnalysisId);
            setDownloadUrl(`/analyses/${returnedAnalysisId}/download`);
          }
          break;
        }

        if (jobData.status === "failed") {
          throw new Error(jobData.error || jobData.message || "Calculation job failed.");
        }
      }

      if (!finalResult) {
        throw new Error("Calculation did not complete within the expected duration.");
      }

      const finalAssets = (finalResult.mappedData || []).map(a => ({
        ...a,
        wpiGroup: a.wpiGroup || industry || "All Commodities (General Index)"
      }));

      setAssets(finalAssets);
      setStep(3); // Open straight on Results screen
      setIsCalculating(false);
      setJobStatus(null);
      return finalResult;
    } catch (err) {
      console.error("Job calculation error:", err);
      setError(err.message || "Failed to calculate replacement values.");
      setIsCalculating(false);
      setJobStatus(null);
      throw err;
    }
  };

  // Calculate another FAR file: resets file and calculation, goes to Step 1 Upload ready for next file
  const handleCalculateAnother = () => {
    setAssets([]);
    setSelectedFile(null);
    setColumnAnalysis(null);
    setDownloadUrl(null);
    setError("");
    setJobStatus(null);
    setIsCalculating(false);
    setStep(1);
  };

  // Start fresh with a new company: resets everything and goes to Step 1
  const handleNewCompany = () => {
    setAssets([]);
    setSelectedFile(null);
    setColumnAnalysis(null);
    setDownloadUrl(null);
    setCompanyDetails({});
    setError("");
    setJobStatus(null);
    setIsCalculating(false);
    setStep(1);
  };

  // Return to Step 3 Results Dashboard
  const handleBackToResults = () => {
    setStep(3);
  };

  if (authLoading) {
    return (
      <div style={{ minHeight: "100dvh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", background: "#F1F5F9", gap: 12 }}>
        <Loader2 className="animate-spin" size={36} color={T.blue} />
        <span style={{ fontSize: 14, color: T.mute, fontWeight: 500 }}>Initializing ASSETRA...</span>
      </div>
    );
  }

  if (!token || !currentUser) {
    if (authScreen === "signup") {
      return (
        <SignUpScreen
          onNavigateLogin={() => {
            window.location.hash = "";
            setAuthScreen("login");
          }}
          onNavigateForgotPassword={() => {
            window.location.hash = "#forgot-password";
            setAuthScreen("login");
          }}
          onLoginSuccess={handleLoginSuccess}
          apiBaseUrl={API_BASE_URL}
        />
      );
    }
    return (
      <LoginScreen
        onLoginSuccess={handleLoginSuccess}
        onNavigateSignUp={() => {
          window.location.hash = "#signup";
          setAuthScreen("signup");
        }}
        apiBaseUrl={API_BASE_URL}
        sessionExpiredMessage={sessionExpiredMessage}
        onClearSessionExpiredMessage={() => setSessionExpiredMessage("")}
      />
    );
  }

  if (currentUser.must_change_password) {
    return (
      <ChangePasswordScreen
        isForced={true}
        onPasswordChanged={handlePasswordChanged}
        token={token}
        apiBaseUrl={API_BASE_URL}
      />
    );
  }

  return (
    <div className="assetra-app-container">
      <style>{FONT_IMPORT}</style>

      {/* BACKGROUND TASK PROGRESS MODAL */}
      {isCalculating && <CalculationProgressModal jobStatus={jobStatus} />}

      {/* VOLUNTARY CHANGE PASSWORD MODAL */}
      {showChangePasswordModal && (
        <ChangePasswordScreen
          isForced={false}
          onPasswordChanged={handlePasswordChanged}
          onCancel={() => setShowChangePasswordModal(false)}
          token={token}
          apiBaseUrl={API_BASE_URL}
        />
      )}

      {/* HEADER BAR */}
      <div className="far-header-content assetra-header" style={{
        background: "#fff",
        borderBottom: `1px solid ${T.line}`,
        padding: "12px 28px",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        position: "sticky",
        top: 0,
        zIndex: 100,
        boxShadow: "0 1px 2px 0 rgba(0, 0, 0, 0.02)"
      }}>
        {/* Brand Logo & Name */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
          <AssetraBrandLockup theme="light" iconSize={46} fontSize={21} taglineSize={12} />
        </div>

        {/* Right side container */}
        <div style={{ display: "flex", alignItems: "center", gap: 14, minWidth: 0 }}>
          <div className="far-header-meta" style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, color: T.mute, minWidth: 0, justifyContent: "flex-end" }}>
            {companyDetails?.name && (
              <span style={{ fontWeight: 600, color: T.ink, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 160 }} title={companyDetails.name}>
                {companyDetails.name}
              </span>
            )}
            {companyDetails?.name && selectedFile?.name && <span>•</span>}
            {selectedFile?.name && (
              <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 160 }} title={selectedFile.name}>
                {selectedFile.name}
              </span>
            )}
          </div>

          {/* DESKTOP NAVIGATION BUTTONS (Preserved, hidden on mobile <768px via assetra-nav-desktop) */}
          <div className="assetra-nav-desktop" style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button
              onClick={() => {
                if (currentView === "my_analyses") {
                  setCurrentView("calculator");
                  window.location.hash = "#calculator";
                } else {
                  setCurrentView("my_analyses");
                  window.location.hash = "#my-analyses";
                }
              }}
              style={{
                height: 38,
                padding: "0 12px",
                borderRadius: 8,
                border: "1px solid #CBD5E1",
                background: currentView === "my_analyses" ? "#EFF6FF" : "#fff",
                color: currentView === "my_analyses" ? "#1D4ED8" : "#475569",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 13,
                fontWeight: 600
              }}
            >
              <FolderArchive size={15} />
              <span>{currentView === "my_analyses" ? "Calculator" : "My Analyses"}</span>
            </button>

            <button
              onClick={() => {
                setCurrentAnalysisId(null);
                setSelectedFile(null);
                setStep(1);
                setCurrentView("calculator");
                window.location.hash = "#calculator";
              }}
              style={{
                height: 38,
                padding: "0 12px",
                borderRadius: 8,
                border: "none",
                background: "#2563EB",
                color: "#fff",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 6,
                fontSize: 13,
                fontWeight: 600
              }}
            >
              <Plus size={15} />
              <span>New Analysis</span>
            </button>

            {currentUser?.role === "admin" && (
              <button
                id="admin-dashboard-btn"
                onClick={handleAdminClick}
                style={{
                  height: 38,
                  padding: "0 12px",
                  borderRadius: 8,
                  border: "1px solid #CBD5E1",
                  background: currentView === "admin_dashboard" ? "#EEF2FF" : "#fff",
                  color: currentView === "admin_dashboard" ? "#4F46E5" : "#475569",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  fontSize: 13,
                  fontWeight: 600
                }}
                title={currentView === "admin_dashboard" ? "Return to Calculator" : "Access Admin Portal"}
              >
                <ShieldCheck size={15} color={currentView === "admin_dashboard" ? "#4F46E5" : "#475569"} />
                <span>{currentView === "admin_dashboard" ? "Calculator" : "Admin"}</span>
              </button>
            )}

            {/* USER BADGE & ACCOUNT SETTINGS BUTTON */}
            <button
              id="account-settings-btn"
              onClick={() => {
                setCurrentView("account_settings");
                window.location.hash = "#account-settings";
              }}
              title="Account Settings"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                background: currentView === "account_settings" ? "#EFF6FF" : "#F8FAFC",
                border: `1px solid ${currentView === "account_settings" ? "#93C5FD" : T.line}`,
                padding: "4px 10px",
                borderRadius: 8,
                fontSize: 12,
                cursor: "pointer",
                height: 38
              }}
            >
              <div style={{
                width: 24,
                height: 24,
                borderRadius: "50%",
                background: "#F0FDF4",
                color: "#16A34A",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontWeight: 700,
                fontSize: 11
              }}>
                {currentUser?.name ? currentUser.name[0].toUpperCase() : "U"}
              </div>
              <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.1, textAlign: "left" }}>
                <span style={{ fontWeight: 600, color: T.ink, maxWidth: 100, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {currentUser?.name}
                </span>
                <span style={{ fontSize: 9, color: currentUser?.role === "admin" ? "#4F46E5" : "#16A34A", textTransform: "uppercase", fontWeight: 700, letterSpacing: 0.5 }}>
                  {currentUser?.role === "admin" ? "ADMIN" : "USER"}
                </span>
              </div>
              <Settings size={14} color={currentView === "account_settings" ? "#1D4ED8" : T.mute} style={{ marginLeft: 2 }} />
            </button>

            <button
              onClick={() => setShowChangePasswordModal(true)}
              title="Change Password"
              style={{
                background: "transparent",
                border: `1px solid ${T.line}`,
                borderRadius: 8,
                width: 38,
                height: 38,
                cursor: "pointer",
                color: T.mute,
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}
            >
              <KeyRound size={15} />
            </button>

            <button
              onClick={handleLogout}
              title="Log Out"
              style={{
                background: "transparent",
                border: `1px solid ${T.line}`,
                borderRadius: 8,
                width: 38,
                height: 38,
                cursor: "pointer",
                color: "#DC2626",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}
            >
              <LogOut size={15} />
            </button>
          </div>

          {/* MOBILE HAMBURGER BUTTON (Visible on <768px via assetra-hamburger-btn) */}
          <button
            type="button"
            className="assetra-hamburger-btn"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle Navigation Menu"
            aria-expanded={mobileMenuOpen}
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* MOBILE NAVIGATION DRAWER */}
      {mobileMenuOpen && (
        <>
          <div 
            className="assetra-mobile-drawer-backdrop"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="assetra-mobile-drawer" role="dialog" aria-modal="true" aria-label="Mobile Navigation">
            {/* Drawer Header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingBottom: 16, borderBottom: "1px solid #E2E8F0", marginBottom: 16 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <div style={{
                  width: 38,
                  height: 38,
                  borderRadius: "50%",
                  background: "#F0FDF4",
                  color: "#16A34A",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  fontSize: 15
                }}>
                  {currentUser?.name ? currentUser.name[0].toUpperCase() : "U"}
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14, color: "#0F172A", maxWidth: 170, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {currentUser?.name || "User"}
                  </div>
                  <span style={{ fontSize: 10, color: currentUser?.role === "admin" ? "#4F46E5" : "#16A34A", fontWeight: 700, textTransform: "uppercase" }}>
                    {currentUser?.role === "admin" ? "ADMINISTRATOR" : "STANDARD USER"}
                  </span>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setMobileMenuOpen(false)}
                aria-label="Close menu"
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: 8,
                  background: "#F8FAFC",
                  border: "1px solid #E2E8F0",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#475569",
                  cursor: "pointer"
                }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Active Analysis Info if present */}
            {(companyDetails?.name || selectedFile?.name) && (
              <div style={{ background: "#F1F5F9", borderRadius: 8, padding: "10px 12px", marginBottom: 16, fontSize: 12 }}>
                <div style={{ color: "#64748B", fontSize: 10, textTransform: "uppercase", fontWeight: 700, marginBottom: 2 }}>Current File</div>
                <div style={{ fontWeight: 600, color: "#0F172A", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {companyDetails?.name || selectedFile?.name}
                </div>
              </div>
            )}

            {/* Navigation links with 44px+ touch targets */}
            <div style={{ display: "flex", flexDirection: "column", gap: 6, flex: 1 }}>
              <button
                type="button"
                className={`assetra-drawer-item ${currentView === "calculator" ? "active" : ""}`}
                onClick={() => {
                  setCurrentView("calculator");
                  window.location.hash = "#calculator";
                  setMobileMenuOpen(false);
                }}
              >
                <Play size={18} />
                <span>Calculator</span>
              </button>

              <button
                type="button"
                className={`assetra-drawer-item ${currentView === "my_analyses" ? "active" : ""}`}
                onClick={() => {
                  setCurrentView("my_analyses");
                  window.location.hash = "#my-analyses";
                  setMobileMenuOpen(false);
                }}
              >
                <FolderArchive size={18} />
                <span>My Analyses</span>
              </button>

              <button
                type="button"
                className="assetra-drawer-item"
                style={{ background: "#EFF6FF", color: "#1D4ED8" }}
                onClick={() => {
                  setCurrentAnalysisId(null);
                  setSelectedFile(null);
                  setStep(1);
                  setCurrentView("calculator");
                  window.location.hash = "#calculator";
                  setMobileMenuOpen(false);
                }}
              >
                <Plus size={18} />
                <span>New Analysis</span>
              </button>

              {currentUser?.role === "admin" && (
                <button
                  type="button"
                  className={`assetra-drawer-item ${currentView === "admin_dashboard" ? "active" : ""}`}
                  onClick={() => {
                    handleAdminClick();
                    setMobileMenuOpen(false);
                  }}
                >
                  <ShieldCheck size={18} color="#4F46E5" />
                  <span>Admin Portal</span>
                </button>
              )}

              <div style={{ height: 1, background: "#E2E8F0", margin: "8px 0" }} />

              <button
                type="button"
                className={`assetra-drawer-item ${currentView === "account_settings" ? "active" : ""}`}
                onClick={() => {
                  setCurrentView("account_settings");
                  window.location.hash = "#account-settings";
                  setMobileMenuOpen(false);
                }}
              >
                <Settings size={18} />
                <span>Account Settings</span>
              </button>

              <button
                type="button"
                className="assetra-drawer-item"
                onClick={() => {
                  setShowChangePasswordModal(true);
                  setMobileMenuOpen(false);
                }}
              >
                <KeyRound size={18} />
                <span>Change Password</span>
              </button>
            </div>

            {/* Logout button at bottom of drawer */}
            <div style={{ paddingTop: 16, borderTop: "1px solid #E2E8F0" }}>
              <button
                type="button"
                className="assetra-drawer-item"
                style={{ color: "#DC2626", background: "#FEF2F2", borderColor: "#FECACA" }}
                onClick={() => {
                  setMobileMenuOpen(false);
                  handleLogout();
                }}
              >
                <LogOut size={18} />
                <span>Log Out</span>
              </button>
            </div>
          </div>
        </>
      )}

      {/* DUPLICATE FILE SHORTCUT MODAL */}
      {duplicateAnalysis && (
        <DuplicateFileModal
          analysis={duplicateAnalysis.analysis || duplicateAnalysis}
          onOpenSaved={() => {
            const savedId = duplicateAnalysis.analysis_id || duplicateAnalysis.analysis?.id || duplicateAnalysis.id;
            const comp = duplicateAnalysis.company_name || duplicateAnalysis.analysis?.company_name;
            const origFile = duplicateAnalysis.original_filename || duplicateAnalysis.analysis?.original_filename;
            setDuplicateAnalysis(null);
            setCurrentAnalysisId(savedId);
            if (comp) setCompanyDetails(prev => ({ ...prev, name: comp }));
            if (origFile) setSelectedFile({ name: origFile });
            setCurrentView("calculator");
            setStep(3);
          }}
          onRecalculate={() => {
            const file = selectedFile;
            const ind = companyDetails?.industry?.[0] || "All Commodities (General Index)";
            setDuplicateAnalysis(null);
            handleUpload(file, ind, true);
          }}
          onCancel={() => setDuplicateAnalysis(null)}
        />
      )}

      {/* PAGE BODY CONTAINER */}
      <div className="far-page-container" style={{ padding: currentView === "admin_dashboard" ? "24px 28px 80px" : "36px 28px 80px", maxWidth: 1440, width: "100%", minWidth: 0, boxSizing: "border-box", margin: "0 auto" }}>
        {currentView === "admin_dashboard" ? (
          ((adminToken && adminUser && adminUser.role === "admin") || (currentUser && currentUser.role === "admin")) ? (
            <AdminDashboardScreen
              token={adminToken || token}
              adminUser={adminUser || currentUser}
              apiBaseUrl={API_BASE_URL}
              onBackToCalculator={() => {
                setCurrentView("calculator");
                window.location.hash = "#calculator";
              }}
              onOpenAnalysis={(id) => {
                setCurrentAnalysisId(id);
                setCurrentView("calculator");
                setStep(3);
                window.location.hash = "#calculator";
              }}
            />
          ) : (
            <div
              id="admin-access-denied"
              style={{
                maxWidth: 520,
                margin: "60px auto",
                background: "#ffffff",
                border: "1px solid #FECACA",
                borderRadius: 12,
                padding: "36px 28px",
                textAlign: "center",
                boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)"
              }}
            >
              <div style={{
                width: 48,
                height: 48,
                borderRadius: "50%",
                background: "#FEF2F2",
                color: "#DC2626",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 16px"
              }}>
                <ShieldCheck size={24} />
              </div>
              <h2 style={{ fontSize: 20, fontWeight: 700, color: "#991B1B", margin: "0 0 8px" }}>
                Access denied
              </h2>
              <p style={{ fontSize: 14, color: "#64748B", margin: "0 0 24px", lineHeight: 1.5 }}>
                You do not have administrator privileges to view this page. No administrator data has been loaded.
              </p>
              <button
                onClick={() => {
                  setCurrentView("calculator");
                  window.location.hash = "#calculator";
                }}
                style={{
                  background: "#2563EB",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: 8,
                  padding: "10px 20px",
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: "pointer"
                }}
              >
                Back to Calculator
              </button>
            </div>
          )
        ) : currentView === "account_settings" ? (
          <AccountSettingsScreen
            token={token}
            currentUser={currentUser}
            apiBaseUrl={API_BASE_URL}
            onProfileUpdated={(updatedUser) => {
              setCurrentUser(prev => ({ ...prev, ...updatedUser }));
            }}
            onOpenAnalysis={(id) => {
              setCurrentAnalysisId(id);
              setCurrentView("calculator");
              setStep(3);
              window.location.hash = "#calculator";
            }}
            onBackToDashboard={() => {
              if (currentUser?.role === "admin") {
                setCurrentView("admin_dashboard");
                window.location.hash = "#admin";
              } else {
                setCurrentView("calculator");
                window.location.hash = "#calculator";
              }
            }}
            onSignOut={handleLogout}
            onAccountDeleted={(msg) => {
              clearAllAuthAndAnalysisState();
              setSessionExpiredMessage(msg || "Your account and associated personal data have been permanently deleted.");
              window.location.hash = "";
            }}
          />
        ) : currentView === "my_analyses" ? (
          <MyAnalysesScreen
            onOpenAnalysis={(id) => {
              setCurrentAnalysisId(id);
              setCurrentView("calculator");
              setStep(3);
              window.location.hash = "#calculator";
            }}
            onAnalyzeNew={() => {
              setCurrentAnalysisId(null);
              setSelectedFile(null);
              setStep(1);
              setCurrentView("calculator");
              window.location.hash = "#calculator";
            }}
            token={token}
            apiBaseUrl={API_BASE_URL}
            onRefreshProfile={refreshUser}
          />
        ) : (
          <>
            <FarColumnsHelpModal
              isOpen={showColumnsHelpModal}
              onClose={() => setShowColumnsHelpModal(false)}
              apiBaseUrl={API_BASE_URL}
            />

            <Stepper currentStep={step} onStepClick={setStep} columnAnalysis={columnAnalysis} />

            {step === 1 && (
              <UploadStep 
                companyDetails={companyDetails}
                setCompanyDetails={setCompanyDetails}
                selectedFile={selectedFile}
                setSelectedFile={(f) => {
                  setSelectedFile(f);
                  if (!f) setColumnAnalysis(null);
                }}
                columnAnalysis={columnAnalysis}
                setColumnAnalysis={setColumnAnalysis}
                isAnalyzingColumns={isAnalyzingColumns}
                onUpload={handleUpload}
                onAnalyzeFile={(f) => analyzeFileColumns(f)}
                onOpenReviewColumns={() => setStep(2)}
                onOpenHelp={() => setShowColumnsHelpModal(true)}
                error={error}
                setError={setError}
                apiBaseUrl={API_BASE_URL}
              />
            )}
            
            {step === 2 && (
              <CheckColumnsStep
                analysisData={columnAnalysis}
                selectedFile={selectedFile}
                onReanalyzeHeaderRow={(rowIdx) => analyzeFileColumns(selectedFile, rowIdx)}
                onConfirmAndCalculate={(calcMapping, hdrIdx, shName) => {
                  const ind = companyDetails?.industry?.[0] || "All Commodities (General Index)";
                  return handleUpload(selectedFile, ind, true, calcMapping, hdrIdx, shName);
                }}
                onBack={() => setStep(1)}
                onOpenHelp={() => setShowColumnsHelpModal(true)}
                apiBaseUrl={API_BASE_URL}
                token={token}
                isReanalyzing={isAnalyzingColumns}
              />
            )}
            
            {step === 3 && (
              <>
                {selectedFile && columnAnalysis && (
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                      alignItems: "center",
                      gap: 12,
                      marginBottom: 10
                    }}
                  >
                    <button
                      type="button"
                      id="results-review-columns-link"
                      onClick={() => setStep(2)}
                      style={{
                        background: "#EFF6FF",
                        border: "1px solid #BFDBFE",
                        borderRadius: 6,
                        padding: "5px 12px",
                        fontSize: 12,
                        fontWeight: 600,
                        color: "#1D4ED8",
                        cursor: "pointer"
                      }}
                    >
                      Review columns
                    </button>
                  </div>
                )}
                <ResultsStepServer 
                  analysisId={currentAnalysisId}
                  companyDetails={companyDetails}
                  selectedFile={selectedFile}
                  token={token}
                  apiBaseUrl={API_BASE_URL}
                  onNext={() => setStep(4)}
                  onBack={() => {
                    setCurrentView("my_analyses");
                    window.location.hash = "#my-analyses";
                  }}
                  onAnalyzeNew={() => {
                    setCurrentAnalysisId(null);
                    setSelectedFile(null);
                    setColumnAnalysis(null);
                    setStep(1);
                    window.location.hash = "#calculator";
                  }}
                />
              </>
            )}

            {step === 4 && (
              <DownloadStep 
                downloadUrl={downloadUrl}
                companyDetails={companyDetails}
                onRestart={handleCalculateAnother}
                onNewCompany={handleNewCompany}
                onBack={handleBackToResults}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
