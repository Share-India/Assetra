import React, { useState, useEffect, useMemo } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Download,
  ArrowLeft,
  ArrowRight,
  Loader2,
  Table as TableIcon,
  ChevronDown,
  ChevronUp,
  Info,
  Sparkles
} from "lucide-react";

const PRIMARY_FIELDS = [
  {
    field: "asset_description",
    label: "Asset Description",
    shortLabel: "Description",
    requirement: "required",
    badgeText: "Required",
    badgeBg: "#FEE2E2",
    badgeColor: "#991B1B",
    hint: "Name or description of each asset"
  },
  {
    field: "capitalized_date",
    label: "Capitalized Date or Year",
    shortLabel: "Date / Year",
    requirement: "required",
    badgeText: "Required",
    badgeBg: "#FEE2E2",
    badgeColor: "#991B1B",
    hint: "Purchase date, capitalization date, or 4-digit year"
  },
  {
    field: "acquisition_value",
    label: "Acquisition Value (Original Cost)",
    shortLabel: "Acquisition Value",
    requirement: "required",
    badgeText: "Required",
    badgeBg: "#FEE2E2",
    badgeColor: "#991B1B",
    hint: "Original purchase cost (must be numeric)"
  },
  {
    field: "major_category",
    label: "Category (Major Category / Asset Group)",
    shortLabel: "Category",
    requirement: "recommended",
    badgeText: "Recommended",
    badgeBg: "#DBEAFE",
    badgeColor: "#1E40AF",
    hint: "Asset group or block of assets (or classify from description)"
  },
  {
    field: "sub_category",
    label: "Second Category Column (Optional)",
    shortLabel: "2nd Category",
    requirement: "optional",
    badgeText: "Optional",
    badgeBg: "#F1F5F9",
    badgeColor: "#475569",
    hint: "Sub-category or asset class if your file has two category columns"
  }
];

const EXTRA_OPTIONAL_FIELDS = [
  {
    field: "asset_code",
    label: "Asset Code / Tag No.",
    shortLabel: "Asset Code",
    requirement: "optional",
    badgeText: "Optional",
    badgeBg: "#F1F5F9",
    badgeColor: "#475569",
    hint: "Unique identifier or tag number"
  },
  {
    field: "location",
    label: "Location / Plant",
    shortLabel: "Location",
    requirement: "optional",
    badgeText: "Optional",
    badgeBg: "#F1F5F9",
    badgeColor: "#475569",
    hint: "Plant, site, or branch"
  },
  {
    field: "accumulated_depreciation",
    label: "Accumulated Depreciation",
    shortLabel: "Accum. Dep.",
    requirement: "optional",
    badgeText: "Optional",
    badgeBg: "#F1F5F9",
    badgeColor: "#475569",
    hint: "Total depreciation to date"
  },
  {
    field: "book_value",
    label: "Net Book Value (WDV)",
    shortLabel: "Book Value",
    requirement: "optional",
    badgeText: "Optional",
    badgeBg: "#F1F5F9",
    badgeColor: "#475569",
    hint: "Written down value / net block"
  }
];

export default function CheckColumnsStep({
  analysisData,
  selectedFile,
  onReanalyzeHeaderRow,
  onConfirmAndCalculate,
  onBack,
  onOpenHelp,
  apiBaseUrl,
  token,
  isReanalyzing
}) {
  const [mapping, setMapping] = useState({});
  const [initialConfidence, setInitialConfidence] = useState({});
  const [showOptionalFields, setShowOptionalFields] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [requireAdminApproval, setRequireAdminApproval] = useState(false);

  // Sync mapping state whenever analysisData arrives or changes (e.g. after changing header row N)
  useEffect(() => {
    if (!analysisData) return;
    const summaries = analysisData.field_summaries || [];
    const nextMap = {};
    const nextConf = {};
    summaries.forEach((item) => {
      nextMap[item.field] = item.detected_column || "";
      nextConf[item.field] = {
        detected_column: item.detected_column || "",
        confidence: item.confidence || "NONE",
        status: item.status || "Not found"
      };
    });
    setMapping(nextMap);
    setInitialConfidence(nextConf);
    setSubmitError("");
  }, [analysisData]);

  const availableColumns = analysisData?.available_columns || [];
  const headers = analysisData?.headers || [];
  const columnSamples = analysisData?.column_samples || {};
  const columnValidations = analysisData?.column_validations || {};
  const sampleData = analysisData?.sample_data || [];
  const headerRowNumber = analysisData?.header_row_number || (analysisData?.header_row_index ?? 0) + 1;
  const maxHeaderRowOptions = analysisData?.max_header_row_options || 15;

  // Compute live row state (Sample values, Status: Found / Please check / Not found, Validation warning, Plain-language message)
  const evaluateFieldRow = (fieldMeta) => {
    const fKey = fieldMeta.field;
    const chosenCol = mapping[fKey] || "";

    if (fKey === "major_category" && chosenCol === "__NO_CATEGORY__") {
      return {
        chosenCol,
        samples: [],
        status: "Found",
        valid: true,
        warning: null,
        message: "No category column selected — assets will be classified automatically from their description."
      };
    }

    if (!chosenCol) {
      let msg = "Optional column — not selected.";
      if (fKey === "asset_description") {
        msg = "We couldn’t find an Asset Description column. Please pick the column that describes each asset.";
      } else if (fKey === "capitalized_date") {
        msg = "We couldn’t find a Date or Year column. Please pick the column with the purchase or capitalization date/year.";
      } else if (fKey === "acquisition_value") {
        msg = "We couldn’t find an Acquisition Value (Cost) column. Please pick the column containing the original purchase cost.";
      } else if (fKey === "major_category") {
        msg = "We couldn’t find a Category column. Pick it from the list, or choose ‘No category column’.";
      }
      return {
        chosenCol: "",
        samples: [],
        status: "Not found",
        valid: fieldMeta.requirement === "optional",
        warning: null,
        message: msg
      };
    }

    const samples = (columnSamples[chosenCol] || []).slice(0, 5);
    const valInfo = columnValidations[chosenCol]?.[fKey] || { valid: true, warning: null };
    const initInfo = initialConfidence[fKey] || {};
    const isUnchangedLowConfidence =
      initInfo.detected_column === chosenCol &&
      (initInfo.confidence === "MEDIUM" || initInfo.confidence === "LOW");

    if (!valInfo.valid) {
      return {
        chosenCol,
        samples,
        status: "Please check",
        valid: false,
        warning: valInfo.warning || `The column '${chosenCol}' does not look valid for ${fieldMeta.label}.`,
        message: valInfo.warning || `Please check '${chosenCol}'.`
      };
    }

    if (isUnchangedLowConfidence) {
      return {
        chosenCol,
        samples,
        status: "Please check",
        valid: true,
        warning: null,
        message: `Matched '${chosenCol}' with ${initInfo.confidence.toLowerCase()} confidence. Please verify the sample values below.`
      };
    }

    return {
      chosenCol,
      samples,
      status: "Found",
      valid: true,
      warning: null,
      message: `Using '${chosenCol}'.`
    };
  };

  const primaryEvaluations = useMemo(() => {
    const map = {};
    PRIMARY_FIELDS.forEach((fm) => {
      map[fm.field] = evaluateFieldRow(fm);
    });
    return map;
  }, [mapping, columnSamples, columnValidations, initialConfidence]);

  const optionalEvaluations = useMemo(() => {
    const map = {};
    EXTRA_OPTIONAL_FIELDS.forEach((fm) => {
      map[fm.field] = evaluateFieldRow(fm);
    });
    return map;
  }, [mapping, columnSamples, columnValidations, initialConfidence]);

  // Continue button gate:
  // 1. All 3 required fields (asset_description, capitalized_date, acquisition_value) must be chosen and pass validation
  // 2. Category (major_category) must be chosen (or '__NO_CATEGORY__') and pass validation
  // 3. If second category is chosen, it must pass validation
  const canContinue = useMemo(() => {
    const reqFields = ["asset_description", "capitalized_date", "acquisition_value"];
    for (const rk of reqFields) {
      const ev = primaryEvaluations[rk];
      if (!ev || !ev.chosenCol || !ev.valid) return false;
    }
    const catEv = primaryEvaluations["major_category"];
    if (!catEv || !catEv.chosenCol || !catEv.valid) return false;
    const subEv = primaryEvaluations["sub_category"];
    if (subEv && subEv.chosenCol && !subEv.valid) return false;
    return true;
  }, [primaryEvaluations]);

  // Active warnings list for top summary banner
  const activeValidationWarnings = useMemo(() => {
    const list = [];
    PRIMARY_FIELDS.forEach((fm) => {
      const ev = primaryEvaluations[fm.field];
      if (ev?.warning) {
        list.push({ field: fm.label, warning: ev.warning });
      }
    });
    return list;
  }, [primaryEvaluations]);

  const missingMessages = useMemo(() => {
    const list = [];
    ["asset_description", "capitalized_date", "acquisition_value", "major_category"].forEach((fk) => {
      const ev = primaryEvaluations[fk];
      if (ev && !ev.chosenCol) {
        list.push(ev.message);
      }
    });
    return list;
  }, [primaryEvaluations]);

  // Map column header -> role badge for the 5-row preview
  const chosenColRoles = useMemo(() => {
    const roles = {};
    [...PRIMARY_FIELDS, ...EXTRA_OPTIONAL_FIELDS].forEach((fm) => {
      const col = mapping[fm.field];
      if (col && col !== "__NO_CATEGORY__") {
        if (!roles[col]) roles[col] = [];
        roles[col].push({
          label: fm.shortLabel,
          requirement: fm.requirement
        });
      }
    });
    return roles;
  }, [mapping]);

  // Columns to display in the 5-row preview: show chosen columns first, then remaining columns
  const previewColumns = useMemo(() => {
    const chosenSet = new Set(Object.keys(chosenColRoles));
    const chosenList = [];
    const otherList = [];
    headers.forEach((h, idx) => {
      if (!h || String(h).trim() === "") return;
      if (chosenSet.has(h)) {
        chosenList.push({ name: h, idx, isChosen: true, roles: chosenColRoles[h] });
      } else {
        otherList.push({ name: h, idx, isChosen: false, roles: [] });
      }
    });
    return [...chosenList, ...otherList];
  }, [headers, chosenColRoles]);

  const handleSelectChange = (fieldKey, newCol) => {
    setMapping((prev) => ({
      ...prev,
      [fieldKey]: newCol
    }));
    setSubmitError("");
  };

  const handleContinueClick = async () => {
    if (!canContinue || submitting) return;
    setSubmitting(true);
    setSubmitError("");

    try {
      const payload = {
        headers,
        header_row_index: analysisData?.header_row_index ?? 0,
        mapping,
        sample_data: sampleData,
        require_admin_approval: requireAdminApproval
      };

      const res = await fetch(`${apiBaseUrl}/confirm-mapping`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (!res.ok || !data.valid) {
        const firstWarn =
          data.warnings && Object.values(data.warnings)[0]
            ? Object.values(data.warnings)[0]
            : data.detail || "Please fix the highlighted column warnings before continuing.";
        setSubmitError(firstWarn);
        setSubmitting(false);
        return;
      }

      const calcMap = data.calculator_mapping || {
        ...mapping,
        purchase_date: mapping.capitalized_date || "",
        major_category: mapping.major_category === "__NO_CATEGORY__" ? "" : mapping.major_category || "",
        asset_class: mapping.sub_category || ""
      };

      await onConfirmAndCalculate(
        calcMap,
        analysisData?.header_row_index ?? 0,
        analysisData?.sheet_name || ""
      );
    } catch (err) {
      setSubmitError(err.message || "Failed to confirm column mapping.");
    } finally {
      setSubmitting(false);
    }
  };

  const renderStatusBadge = (statusStr, valid) => {
    if (statusStr === "Found" && valid) {
      return (
        <span
          className="status-badge-found"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
            padding: "4px 10px",
            borderRadius: 999,
            fontSize: 12,
            fontWeight: 700,
            background: "#DCFCE7",
            color: "#166534",
            border: "1px solid #BBF7D0",
            whiteSpace: "nowrap"
          }}
        >
          <CheckCircle2 size={14} /> Found
        </span>
      );
    }
    if (statusStr === "Please check") {
      return (
        <span
          className="status-badge-check"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
            padding: "4px 10px",
            borderRadius: 999,
            fontSize: 12,
            fontWeight: 700,
            background: valid ? "#FEF3C7" : "#FEE2E2",
            color: valid ? "#92400E" : "#991B1B",
            border: `1px solid ${valid ? "#FDE68A" : "#FECACA"}`,
            whiteSpace: "nowrap"
          }}
        >
          <AlertTriangle size={14} /> Please check
        </span>
      );
    }
    return (
      <span
        className="status-badge-not-found"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 5,
          padding: "4px 10px",
          borderRadius: 999,
          fontSize: 12,
          fontWeight: 700,
          background: "#FEE2E2",
          color: "#991B1B",
          border: "1px solid #FECACA",
          whiteSpace: "nowrap"
        }}
      >
        <XCircle size={14} /> Not found
      </span>
    );
  };

  const renderFieldRowDesktop = (fm, ev) => {
    const isCat = fm.field === "major_category";
    const isOptional = fm.requirement === "optional";

    return (
      <tr
        key={fm.field}
        data-field={fm.field}
        style={{
          borderBottom: "1px solid #E2E8F0",
          background: !ev.valid && ev.chosenCol ? "#FFF5F5" : "#FFFFFF"
        }}
      >
        {/* 1. Field */}
        <td style={{ padding: "14px 16px", verticalAlign: "top", width: "26%" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
            <span style={{ fontSize: 14, fontWeight: 700, color: "#0F172A" }}>{fm.label}</span>
            <span
              style={{
                fontSize: 10,
                fontWeight: 700,
                padding: "2px 7px",
                borderRadius: 999,
                background: fm.badgeBg,
                color: fm.badgeColor,
                textTransform: "uppercase",
                letterSpacing: 0.3
              }}
            >
              {fm.badgeText}
            </span>
          </div>
          <div style={{ fontSize: 12, color: "#64748B", lineHeight: 1.35 }}>{fm.hint}</div>
        </td>

        {/* 2. Detected Column Dropdown */}
        <td style={{ padding: "14px 16px", verticalAlign: "top", width: "28%" }}>
          <select
            id={`col-select-${fm.field}`}
            aria-label={`Select column for ${fm.label}`}
            value={ev.chosenCol}
            onChange={(e) => handleSelectChange(fm.field, e.target.value)}
            style={{
              width: "100%",
              minHeight: 40,
              padding: "8px 12px",
              borderRadius: 8,
              border: `1.5px solid ${
                !ev.valid && ev.chosenCol
                  ? "#EF4444"
                  : ev.status === "Found"
                  ? "#CBD5E1"
                  : "#F59E0B"
              }`,
              background: "#FFFFFF",
              fontSize: 13,
              fontWeight: 600,
              color: ev.chosenCol ? "#0F172A" : "#64748B",
              outline: "none",
              cursor: "pointer"
            }}
          >
            <option value="">
              {isOptional ? "— None (Do not map) —" : "— Select a column from your file —"}
            </option>
            {isCat && (
              <option value="__NO_CATEGORY__">
                No category column (classify from description)
              </option>
            )}
            {availableColumns.map((colName) => (
              <option key={colName} value={colName}>
                {colName}
              </option>
            ))}
          </select>
        </td>

        {/* 3. 3 to 5 Sample Values */}
        <td style={{ padding: "14px 16px", verticalAlign: "top", width: "24%" }}>
          {ev.chosenCol === "__NO_CATEGORY__" ? (
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                fontSize: 12,
                color: "#1D4ED8",
                background: "#EFF6FF",
                padding: "4px 10px",
                borderRadius: 6,
                fontWeight: 500
              }}
            >
              <Sparkles size={13} /> Classified from Asset Description
            </span>
          ) : ev.samples.length > 0 ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {ev.samples.slice(0, 5).map((val, idx) => (
                <span
                  key={idx}
                  style={{
                    fontSize: 12,
                    background: "#F1F5F9",
                    color: "#1E293B",
                    border: "1px solid #E2E8F0",
                    borderRadius: 6,
                    padding: "3px 8px",
                    maxWidth: 180,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    fontFamily: "Inter, monospace"
                  }}
                  title={String(val)}
                >
                  {String(val)}
                </span>
              ))}
            </div>
          ) : (
            <span style={{ fontSize: 12, color: "#94A3B8", fontStyle: "italic" }}>
              {ev.chosenCol ? "No non-empty sample values in first rows" : "Select a column to preview 3–5 values"}
            </span>
          )}
        </td>

        {/* 4. Status & Plain-Language Message */}
        <td style={{ padding: "14px 16px", verticalAlign: "top", width: "22%" }}>
          <div style={{ marginBottom: 6 }}>{renderStatusBadge(ev.status, ev.valid)}</div>
          <div
            style={{
              fontSize: 12,
              lineHeight: 1.4,
              color: !ev.valid
                ? "#B91C1C"
                : ev.status === "Please check"
                ? "#92400E"
                : ev.status === "Not found"
                ? "#991B1B"
                : "#475569",
              fontWeight: !ev.valid || ev.status !== "Found" ? 600 : 400
            }}
          >
            {ev.message}
          </div>
        </td>
      </tr>
    );
  };

  const renderFieldCardMobile = (fm, ev) => {
    const isCat = fm.field === "major_category";
    const isOptional = fm.requirement === "optional";

    return (
      <div
        key={fm.field}
        data-field-mobile={fm.field}
        style={{
          background: !ev.valid && ev.chosenCol ? "#FFF5F5" : "#FFFFFF",
          border: `1px solid ${!ev.valid && ev.chosenCol ? "#FECACA" : "#E2E8F0"}`,
          borderRadius: 12,
          padding: "14px",
          marginBottom: 12,
          boxShadow: "0 1px 2px rgba(0,0,0,0.03)"
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, marginBottom: 8 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 6, flexWrap: "wrap" }}>
              <span style={{ fontSize: 14, fontWeight: 700, color: "#0F172A" }}>{fm.label}</span>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: 700,
                  padding: "2px 6px",
                  borderRadius: 999,
                  background: fm.badgeBg,
                  color: fm.badgeColor,
                  textTransform: "uppercase"
                }}
              >
                {fm.badgeText}
              </span>
            </div>
            <div style={{ fontSize: 12, color: "#64748B", marginTop: 2 }}>{fm.hint}</div>
          </div>
          {renderStatusBadge(ev.status, ev.valid)}
        </div>

        <div style={{ marginBottom: 10 }}>
          <label
            style={{ display: "block", fontSize: 11, fontWeight: 600, color: "#475569", marginBottom: 4 }}
          >
            Detected / Chosen Column
          </label>
          <select
            value={ev.chosenCol}
            onChange={(e) => handleSelectChange(fm.field, e.target.value)}
            style={{
              width: "100%",
              minHeight: 42,
              padding: "8px 10px",
              borderRadius: 8,
              border: `1.5px solid ${
                !ev.valid && ev.chosenCol ? "#EF4444" : ev.status === "Found" ? "#CBD5E1" : "#F59E0B"
              }`,
              background: "#FFFFFF",
              fontSize: 13,
              fontWeight: 600,
              color: ev.chosenCol ? "#0F172A" : "#64748B"
            }}
          >
            <option value="">
              {isOptional ? "— None (Do not map) —" : "— Select a column from your file —"}
            </option>
            {isCat && (
              <option value="__NO_CATEGORY__">
                No category column (classify from description)
              </option>
            )}
            {availableColumns.map((colName) => (
              <option key={colName} value={colName}>
                {colName}
              </option>
            ))}
          </select>
        </div>

        <div style={{ marginBottom: 8 }}>
          <span style={{ display: "block", fontSize: 11, fontWeight: 600, color: "#475569", marginBottom: 4 }}>
            Sample Values (3 to 5)
          </span>
          {ev.chosenCol === "__NO_CATEGORY__" ? (
            <span style={{ fontSize: 12, color: "#1D4ED8", fontWeight: 500 }}>
              Classified automatically from Asset Description
            </span>
          ) : ev.samples.length > 0 ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
              {ev.samples.slice(0, 5).map((val, idx) => (
                <span
                  key={idx}
                  style={{
                    fontSize: 11,
                    background: "#F1F5F9",
                    color: "#1E293B",
                    border: "1px solid #E2E8F0",
                    borderRadius: 5,
                    padding: "2px 7px"
                  }}
                >
                  {String(val)}
                </span>
              ))}
            </div>
          ) : (
            <span style={{ fontSize: 12, color: "#94A3B8", fontStyle: "italic" }}>
              No column selected
            </span>
          )}
        </div>

        <div
          style={{
            fontSize: 12,
            lineHeight: 1.4,
            padding: "8px 10px",
            borderRadius: 8,
            background: !ev.valid
              ? "#FEE2E2"
              : ev.status === "Please check"
              ? "#FEF3C7"
              : ev.status === "Not found"
              ? "#FEF2F2"
              : "#F8FAFC",
            color: !ev.valid
              ? "#991B1B"
              : ev.status === "Please check"
              ? "#92400E"
              : ev.status === "Not found"
              ? "#991B1B"
              : "#475569",
            fontWeight: !ev.valid || ev.status !== "Found" ? 600 : 400
          }}
        >
          {ev.message}
        </div>
      </div>
    );
  };

  return (
    <div id="check-your-columns-step" style={{ maxWidth: 1240, margin: "0 auto", width: "100%" }}>
      {/* Top Header & Controls Bar */}
      <div
        style={{
          background: "#FFFFFF",
          border: "1px solid #E2E8F0",
          borderRadius: 14,
          padding: "20px 22px",
          marginBottom: 18,
          boxShadow: "0 2px 4px rgba(0,0,0,0.03)"
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: 16
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <h2 style={{ fontSize: 22, fontWeight: 700, color: "#0F172A", margin: 0 }}>
                Check your columns
              </h2>
              {selectedFile?.name && (
                <span
                  style={{
                    fontSize: 12,
                    fontWeight: 600,
                    background: "#EFF6FF",
                    color: "#1D4ED8",
                    border: "1px solid #BFDBFE",
                    padding: "3px 10px",
                    borderRadius: 999
                  }}
                >
                  {selectedFile.name}
                </span>
              )}
            </div>
            <p style={{ fontSize: 13, color: "#64748B", margin: "6px 0 0", lineHeight: 1.45 }}>
              Review how your spreadsheet columns match the required fields. Pick any missing column from the dropdowns below before continuing.
            </p>
          </div>

          {/* Right Controls: Help */}
          <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
            <button
              type="button"
              onClick={onOpenHelp}
              style={{
                background: "#FFFFFF",
                border: "1px solid #CBD5E1",
                borderRadius: 8,
                padding: "8px 12px",
                fontSize: 13,
                fontWeight: 600,
                color: "#1E293B",
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                cursor: "pointer"
              }}
            >
              <HelpCircle size={15} color="#2563EB" />
              What columns are needed?
            </button>
          </div>
        </div>

        {/* Plain-language guidance / warning banners */}
        {activeValidationWarnings.length > 0 && (
          <div
            id="column-validation-warning-banner"
            style={{
              marginTop: 16,
              padding: "12px 16px",
              background: "#FEF2F2",
              border: "1px solid #FECACA",
              borderRadius: 10,
              color: "#991B1B",
              fontSize: 13,
              display: "flex",
              alignItems: "flex-start",
              gap: 10
            }}
          >
            <AlertTriangle size={18} style={{ flexShrink: 0, marginTop: 1 }} />
            <div>
              <div style={{ fontWeight: 700, marginBottom: 3 }}>
                Please fix the highlighted column choice before continuing:
              </div>
              {activeValidationWarnings.map((w, i) => (
                <div key={i} style={{ marginTop: 2 }}>
                  • <strong>{w.field}:</strong> {w.warning}
                </div>
              ))}
            </div>
          </div>
        )}

        {activeValidationWarnings.length === 0 && missingMessages.length > 0 && (
          <div
            id="column-missing-info-banner"
            style={{
              marginTop: 16,
              padding: "12px 16px",
              background: "#FFFBEB",
              border: "1px solid #FDE68A",
              borderRadius: 10,
              color: "#92400E",
              fontSize: 13,
              display: "flex",
              alignItems: "flex-start",
              gap: 10
            }}
          >
            <Info size={18} style={{ flexShrink: 0, marginTop: 1 }} />
            <div>
              {missingMessages.map((m, idx) => (
                <div key={idx} style={{ fontWeight: 600, marginBottom: idx < missingMessages.length - 1 ? 4 : 0 }}>
                  {m}
                </div>
              ))}
            </div>
          </div>
        )}

        {submitError && (
          <div
            style={{
              marginTop: 12,
              padding: "12px 16px",
              background: "#FEF2F2",
              border: "1px solid #FECACA",
              borderRadius: 10,
              color: "#991B1B",
              fontSize: 13,
              fontWeight: 600
            }}
          >
            {submitError}
          </div>
        )}
      </div>

      {/* Main Column Mapping Table (Desktop/Tablet >= 768px) & Cards (Mobile < 768px) */}
      <div
        style={{
          background: "#FFFFFF",
          border: "1px solid #E2E8F0",
          borderRadius: 14,
          overflow: "hidden",
          marginBottom: 20,
          boxShadow: "0 2px 4px rgba(0,0,0,0.03)"
        }}
      >
        <div className="far-desktop-table-view" style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left" }}>
            <thead>
              <tr style={{ background: "#F8FAFC", borderBottom: "1px solid #E2E8F0" }}>
                <th style={{ padding: "12px 16px", fontSize: 12, fontWeight: 700, color: "#475569", textTransform: "uppercase" }}>
                  Field
                </th>
                <th style={{ padding: "12px 16px", fontSize: 12, fontWeight: 700, color: "#475569", textTransform: "uppercase" }}>
                  Detected Column
                </th>
                <th style={{ padding: "12px 16px", fontSize: 12, fontWeight: 700, color: "#475569", textTransform: "uppercase" }}>
                  Sample Values (3 to 5)
                </th>
                <th style={{ padding: "12px 16px", fontSize: 12, fontWeight: 700, color: "#475569", textTransform: "uppercase" }}>
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {PRIMARY_FIELDS.map((fm) => renderFieldRowDesktop(fm, primaryEvaluations[fm.field]))}
              {showOptionalFields &&
                EXTRA_OPTIONAL_FIELDS.map((fm) => renderFieldRowDesktop(fm, optionalEvaluations[fm.field]))}
            </tbody>
          </table>
        </div>

        {/* Mobile Cards View (< 768px) */}
        <div className="far-mobile-cards-view" style={{ padding: 14 }}>
          {PRIMARY_FIELDS.map((fm) => renderFieldCardMobile(fm, primaryEvaluations[fm.field]))}
          {showOptionalFields &&
            EXTRA_OPTIONAL_FIELDS.map((fm) => renderFieldCardMobile(fm, optionalEvaluations[fm.field]))}
        </div>

        {/* Toggle Additional Optional Columns Footer */}
        <div
          style={{
            padding: "10px 16px",
            background: "#F8FAFC",
            borderTop: "1px solid #E2E8F0",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 10
          }}
        >
          <button
            type="button"
            onClick={() => setShowOptionalFields((v) => !v)}
            style={{
              background: "none",
              border: "none",
              color: "#2563EB",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "4px 0"
            }}
          >
            {showOptionalFields ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            {showOptionalFields
              ? "Hide additional optional fields (Asset Code, Location, Depreciation, Book Value)"
              : "Show additional optional fields (Asset Code, Location, Depreciation, Book Value)"}
          </button>

          <label
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              fontSize: 12,
              color: "#475569",
              cursor: "pointer"
            }}
            title="When checked, any new column names are queued for administrator approval before joining the shared alias cache"
          >
            <input
              type="checkbox"
              checked={requireAdminApproval}
              onChange={(e) => setRequireAdminApproval(e.target.checked)}
            />
            Submit new column names for admin review before sharing globally
          </label>
        </div>
      </div>

      {/* Preview of the First 5 Rows with Chosen Columns */}
      <div
        id="first-5-rows-preview"
        style={{
          background: "#FFFFFF",
          border: "1px solid #E2E8F0",
          borderRadius: 14,
          overflow: "hidden",
          marginBottom: 22,
          boxShadow: "0 2px 4px rgba(0,0,0,0.03)"
        }}
      >
        <div
          style={{
            padding: "14px 18px",
            borderBottom: "1px solid #E2E8F0",
            background: "#F8FAFC",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: 8
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <TableIcon size={17} color="#2563EB" />
            <span style={{ fontSize: 14, fontWeight: 700, color: "#0F172A" }}>
              Preview of first 5 rows
            </span>
          </div>
          <span style={{ fontSize: 12, color: "#64748B" }}>
            Highlighted columns show your chosen fields
          </span>
        </div>

        {sampleData.length === 0 ? (
          <div style={{ padding: 24, textAlign: "center", color: "#64748B", fontSize: 13 }}>
            No data rows found in this spreadsheet.
          </div>
        ) : (
          <div style={{ overflowX: "auto", WebkitOverflowScrolling: "touch" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, textAlign: "left" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #E2E8F0" }}>
                  <th
                    style={{
                      padding: "10px 12px",
                      background: "#F1F5F9",
                      color: "#64748B",
                      fontWeight: 700,
                      width: 44
                    }}
                  >
                    Row
                  </th>
                  {previewColumns.map((col) => (
                    <th
                      key={`${col.name}-${col.idx}`}
                      style={{
                        padding: "10px 14px",
                        background: col.isChosen ? "#EFF6FF" : "#F8FAFC",
                        borderLeft: "1px solid #E2E8F0",
                        minWidth: 130,
                        verticalAlign: "bottom"
                      }}
                    >
                      {col.isChosen && (
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 4 }}>
                          {col.roles.map((r, rIdx) => (
                            <span
                              key={rIdx}
                              style={{
                                fontSize: 10,
                                fontWeight: 700,
                                padding: "2px 6px",
                                borderRadius: 4,
                                background:
                                  r.requirement === "required"
                                    ? "#2563EB"
                                    : r.requirement === "recommended"
                                    ? "#0D9488"
                                    : "#64748B",
                                color: "#FFFFFF",
                                textTransform: "uppercase"
                              }}
                            >
                              {r.label}
                            </span>
                          ))}
                        </div>
                      )}
                      <div style={{ fontSize: 12, fontWeight: 700, color: "#0F172A" }}>{col.name}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sampleData.slice(0, 5).map((row, rIdx) => (
                  <tr key={rIdx} style={{ borderBottom: "1px solid #F1F5F9" }}>
                    <td
                      style={{
                        padding: "10px 12px",
                        background: "#F8FAFC",
                        color: "#64748B",
                        fontWeight: 600
                      }}
                    >
                      {headerRowNumber + rIdx + 1}
                    </td>
                    {previewColumns.map((col) => {
                      const cellVal = col.idx < row.length ? row[col.idx] : "";
                      return (
                        <td
                          key={`${col.name}-${col.idx}-${rIdx}`}
                          style={{
                            padding: "10px 14px",
                            background: col.isChosen ? "#F8FAFF" : "#FFFFFF",
                            borderLeft: "1px solid #F1F5F9",
                            color: "#1E293B",
                            maxWidth: 220,
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap"
                          }}
                          title={String(cellVal ?? "")}
                        >
                          {cellVal !== "" && cellVal !== null && cellVal !== undefined ? String(cellVal) : "—"}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Bottom Action Buttons */}
      <div
        className="far-btn-container"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12
        }}
      >
        <button
          type="button"
          onClick={onBack}
          className="far-btn far-btn-hover"
          style={{
            background: "#FFFFFF",
            color: "#0F172A",
            border: "1px solid #CBD5E1",
            borderRadius: 8,
            padding: "12px 22px",
            fontSize: 14,
            fontWeight: 600,
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            cursor: "pointer"
          }}
        >
          <ArrowLeft size={18} /> Back to Upload
        </button>

        <button
          id="check-columns-continue-btn"
          type="button"
          disabled={!canContinue || submitting}
          onClick={handleContinueClick}
          className="far-btn"
          style={{
            background: canContinue ? "#2563EB" : "#94A3B8",
            color: "#FFFFFF",
            border: "none",
            borderRadius: 8,
            padding: "12px 26px",
            fontSize: 14,
            fontWeight: 700,
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            cursor: canContinue && !submitting ? "pointer" : "not-allowed",
            opacity: canContinue && !submitting ? 1 : 0.65,
            boxShadow: canContinue ? "0 4px 12px rgba(37, 99, 235, 0.25)" : "none"
          }}
        >
          {submitting ? (
            <>
              <Loader2 size={18} className="animate-spin" /> Saving & Calculating...
            </>
          ) : (
            <>
              Continue <ArrowRight size={18} />
            </>
          )}
        </button>
      </div>
    </div>
  );
}

