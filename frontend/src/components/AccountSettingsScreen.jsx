import React, { useState, useEffect, useMemo } from "react";
import {
  User, Mail, Lock, Shield, Trash2, ArrowLeft, LogOut, CheckCircle2,
  AlertCircle, Loader2, Search, Download, ExternalLink, Calendar,
  FileSpreadsheet, KeyRound, Activity, Eye, EyeOff, RefreshCw
} from "lucide-react";

export default function AccountSettingsScreen({
  user,
  currentUser,
  token,
  apiBaseUrl,
  onProfileUpdated,
  onOpenAnalysis,
  onBackToDashboard,
  onLogout,
  onSignOut,
  onAccountDeleted
}) {
  const activeUser = user || currentUser;
  // Section A: Profile state
  const [firstName, setFirstName] = useState(activeUser?.first_name || (activeUser?.name ? activeUser.name.split(" ")[0] : ""));
  const [surname, setSurname] = useState(
    activeUser?.surname !== undefined
      ? activeUser.surname
      : activeUser?.name && activeUser.name.split(" ").length > 1
      ? activeUser.name.split(" ").slice(1).join(" ")
      : ""
  );
  const [email, setEmail] = useState(activeUser?.email || "");
  const [username, setUsername] = useState(activeUser?.username || "");
  const [pendingEmail, setPendingEmail] = useState(activeUser?.pending_email || "");
  const [emailVerifyCode, setEmailVerifyCode] = useState("");
  const [profileSaving, setProfileSaving] = useState(false);
  const [verifyingEmail, setVerifyingEmail] = useState(false);
  const [profileMsg, setProfileMsg] = useState({ type: "", text: "" });

  // Section B: My Analysis state
  const [analyses, setAnalyses] = useState([]);
  const [analysesLoading, setAnalysesLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [dateFilter, setDateFilter] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 5;

  // Section D: Delete Account Confirmation Modal state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleteChecked, setDeleteChecked] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState("");

  const authHeaders = useMemo(() => {
    const h = { "Content-Type": "application/json" };
    if (token) h["Authorization"] = `Bearer ${token}`;
    return h;
  }, [token]);

  const loadAccountData = async () => {
    try {
      const [profRes, anRes] = await Promise.all([
        fetch(`${apiBaseUrl}/account/profile`, { credentials: "include", headers: authHeaders }),
        fetch(`${apiBaseUrl}/analyses`, { credentials: "include", headers: authHeaders })
      ]);

      if (profRes.ok) {
        const profData = await profRes.json();
        const u = profData.user || profData;
        setFirstName(u.first_name || "");
        setSurname(u.surname || "");
        setEmail(u.email || "");
        setUsername(u.username || "");
        setPendingEmail(u.pending_email || "");
        if (onProfileUpdated) onProfileUpdated(u);
      }

      if (anRes.ok) {
        const anData = await anRes.json();
        setAnalyses(Array.isArray(anData) ? anData : (anData.analyses || anData.items || []));
      }
    } catch (e) {
      console.error("Failed to load account settings data:", e);
    } finally {
      setAnalysesLoading(false);
    }
  };

  useEffect(() => {
    loadAccountData();
  }, []);

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setProfileMsg({ type: "", text: "" });
    if (!firstName.trim()) {
      setProfileMsg({ type: "error", text: "First Name is required." });
      return;
    }
    setProfileSaving(true);
    try {
      const res = await fetch(`${apiBaseUrl}/account/profile`, {
        method: "PUT",
        credentials: "include",
        headers: authHeaders,
        body: JSON.stringify({
          first_name: firstName.trim(),
          surname: surname.trim(),
          email: email.trim()
        })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Failed to update profile.");
      }
      if (data.user) {
        setFirstName(data.user.first_name || "");
        setSurname(data.user.surname || "");
        setEmail(data.user.email || "");
        setUsername(data.user.username || "");
        setPendingEmail(data.user.pending_email || "");
        if (onProfileUpdated) onProfileUpdated(data.user);
      }
      setProfileMsg({ type: "success", text: data.message || "Profile details saved successfully." });
    } catch (err) {
      setProfileMsg({ type: "error", text: err.message || "Could not update profile." });
    } finally {
      setProfileSaving(false);
    }
  };

  const handleVerifyEmailChange = async (e) => {
    e.preventDefault();
    setProfileMsg({ type: "", text: "" });
    if (!emailVerifyCode.trim()) {
      setProfileMsg({ type: "error", text: "Please enter the 6-digit verification code." });
      return;
    }
    setVerifyingEmail(true);
    try {
      const res = await fetch(`${apiBaseUrl}/account/verify-email-change`, {
        method: "POST",
        credentials: "include",
        headers: authHeaders,
        body: JSON.stringify({ code: emailVerifyCode.trim() })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Email verification failed.");
      }
      if (data.user) {
        setEmail(data.user.email || "");
        setPendingEmail("");
        setEmailVerifyCode("");
        if (onProfileUpdated) onProfileUpdated(data.user);
      }
      setProfileMsg({ type: "success", text: data.message || "Email address updated and verified!" });
    } catch (err) {
      setProfileMsg({ type: "error", text: err.message || "Invalid verification code." });
    } finally {
      setVerifyingEmail(false);
    }
  };

  const handleDownloadReport = async (analysisId, companyName) => {
    try {
      const res = await fetch(`${apiBaseUrl}/analyses/${analysisId}/download`, {
        credentials: "include",
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      if (!res.ok) throw new Error("Failed to download report.");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `FAR_Replacement_Report_${(companyName || "FAR").replace(/\s+/g, "_")}_${analysisId}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message || "Could not download report.");
    }
  };

  const handleConfirmDeleteAccount = async (e) => {
    e.preventDefault();
    setDeleteError("");
    if (!deleteChecked || deleteConfirmText.trim() !== "DELETE") {
      setDeleteError("Please check the confirmation box and type DELETE in uppercase.");
      return;
    }
    if (activeUser?.has_password !== false && !deletePassword) {
      setDeleteError("Please enter your password to confirm your identity.");
      return;
    }
    setDeleteLoading(true);
    try {
      const res = await fetch(`${apiBaseUrl}/account/delete`, {
        method: "POST",
        credentials: "include",
        headers: authHeaders,
        body: JSON.stringify({
          password: deletePassword || undefined,
          confirm_text: deleteConfirmText.trim(),
          confirmed: deleteChecked
        })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Account deletion failed.");
      }
      setShowDeleteModal(false);
      if (onAccountDeleted) {
        onAccountDeleted(data.message || "Your account and associated personal data have been permanently deleted.");
      }
    } catch (err) {
      setDeleteError(err.message || "Failed to delete account.");
    } finally {
      setDeleteLoading(false);
    }
  };

  // Filtered and sorted analyses (most recent first)
  const filteredAnalyses = useMemo(() => {
    return analyses
      .filter((a) => {
        if (statusFilter !== "all" && (a.status || "").toLowerCase() !== statusFilter.toLowerCase()) {
          return false;
        }
        if (dateFilter && a.created_at) {
          const itemDate = a.created_at.slice(0, 10);
          if (itemDate !== dateFilter) return false;
        }
        if (searchTerm.trim()) {
          const q = searchTerm.trim().toLowerCase();
          const matchFile = (a.original_filename || "").toLowerCase().includes(q);
          const matchComp = (a.company_name || "").toLowerCase().includes(q);
          const matchId = String(a.id).includes(q);
          if (!matchFile && !matchComp && !matchId) return false;
        }
        return true;
      })
      .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
  }, [analyses, statusFilter, dateFilter, searchTerm]);

  const totalPages = Math.max(1, Math.ceil(filteredAnalyses.length / pageSize));
  const paginatedAnalyses = useMemo(() => {
    const start = (page - 1) * pageSize;
    return filteredAnalyses.slice(start, start + pageSize);
  }, [filteredAnalyses, page]);

  const fmtCurrency = (val) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0
    }).format(val || 0);

  const fmtDateOnly = (iso) => {
    if (!iso) return "-";
    try {
      return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    } catch {
      return iso;
    }
  };

  const fmtDateTime = (iso) => {
    if (!iso) return "-";
    try {
      return new Date(iso).toLocaleString("en-GB", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit"
      });
    } catch {
      return iso;
    }
  };

  const sectionCardStyle = {
    background: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: 12,
    padding: "28px",
    marginBottom: 24,
    boxShadow: "0 1px 3px rgba(0, 0, 0, 0.04)"
  };

  const inputStyle = {
    width: "100%",
    height: 42,
    padding: "0 12px",
    border: "1px solid #cbd5e1",
    borderRadius: 8,
    fontSize: 14,
    color: "#0f172a",
    background: "#ffffff",
    boxSizing: "border-box",
    outline: "none"
  };

  const labelStyle = {
    display: "block",
    fontSize: 13,
    fontWeight: 600,
    color: "#334155",
    marginBottom: 6
  };

  return (
    <div id="account-settings-screen" style={{ maxWidth: 1120, margin: "0 auto", width: "100%", minWidth: 0, boxSizing: "border-box" }}>
      <style>{`
        #account-settings-screen {
          width: 100%;
          max-width: 1120px;
          min-width: 0;
          box-sizing: border-box;
        }
        .far-account-banner {
          background: linear-gradient(135deg, #2563eb 0%, #4f46e5 55%, #6d28d9 100%);
          border-radius: 14px;
          padding: 24px 28px;
          color: #ffffff;
          margin-bottom: 24px;
          box-shadow: 0 10px 25px rgba(79, 70, 229, 0.2);
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 16px;
          box-sizing: border-box;
          width: 100%;
          min-width: 0;
          max-width: 100%;
        }
        .far-account-card {
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          padding: 24px;
          margin-bottom: 24px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
          box-sizing: border-box;
          width: 100%;
          min-width: 0;
          max-width: 100%;
          overflow: hidden;
        }
        .far-account-form-grid {
          display: grid;
          grid-template-columns: repeat(3, minmax(0, 1fr));
          gap: 16px;
          margin-bottom: 20px;
          width: 100%;
          box-sizing: border-box;
        }
        .far-account-form-grid > div {
          min-width: 0;
          width: 100%;
          box-sizing: border-box;
        }
        .far-account-filters {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          margin-bottom: 18px;
          width: 100%;
          box-sizing: border-box;
        }
        .far-account-actions-bar {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 24px;
          background: #ffffff;
          border: 1px solid #e2e8f0;
          border-radius: 12px;
          margin-bottom: 40px;
          box-sizing: border-box;
          gap: 12px;
          width: 100%;
        }
        @media (max-width: 900px) {
          .far-account-form-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
          }
        }
        @media (max-width: 639px) {
          #account-settings-screen {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
          }
          .far-account-banner {
            padding: 18px 16px !important;
            gap: 12px !important;
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
          }
          .far-account-banner h1 {
            font-size: 20px !important;
          }
          .far-account-banner p {
            font-size: 13px !important;
            line-height: 1.4 !important;
          }
          .far-account-banner button {
            width: 100% !important;
            justify-content: center !important;
          }
          .far-account-card {
            padding: 18px 14px !important;
            border-radius: 10px !important;
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            overflow: hidden !important;
          }
          .far-account-form-grid {
            grid-template-columns: 1fr !important;
            gap: 14px !important;
          }
          .far-account-form-grid > div {
            width: 100% !important;
            min-width: 0 !important;
          }
          .far-account-filters {
            flex-direction: column !important;
            gap: 10px !important;
          }
          .far-account-filters > div,
          .far-account-filters > select,
          .far-account-filters > input,
          .far-account-filters > button {
            width: 100% !important;
            flex: 1 1 100% !important;
          }
          .far-account-actions-bar {
            flex-direction: column !important;
            padding: 14px !important;
            gap: 10px !important;
          }
          .far-account-actions-bar > button {
            width: 100% !important;
            justify-content: center !important;
          }
          #save-profile-btn,
          #open-delete-account-modal-btn {
            width: 100% !important;
            justify-content: center !important;
          }
        }
      `}</style>

      {/* PROFESSIONAL BLUE / PURPLE HEADER */}
      <div className="far-account-banner">
        <div style={{ minWidth: 0, flex: "1 1 280px" }}>
          <h1 style={{ fontSize: 24, fontWeight: 700, margin: "0 0 6px 0", letterSpacing: "-0.01em" }}>
            Account Settings
          </h1>
          <p style={{ fontSize: 14, color: "rgba(255,255,255,0.88)", margin: 0, lineHeight: 1.4 }}>
            Manage your profile information, saved FAR analysis history, security settings, and account preferences.
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            type="button"
            onClick={onBackToDashboard}
            style={{
              background: "rgba(255,255,255,0.16)",
              color: "#ffffff",
              border: "1px solid rgba(255,255,255,0.3)",
              borderRadius: 8,
              padding: "10px 16px",
              minHeight: 44,
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6
            }}
          >
            <ArrowLeft size={15} />
            <span>Back to Dashboard</span>
          </button>
        </div>
      </div>

      {/* ===================================================================== */}
      {/* SECTION A: PROFILE INFORMATION                                        */}
      {/* ===================================================================== */}
      <div id="profile-information-section" className="far-account-card">
        <div style={{ borderBottom: "1px solid #e2e8f0", paddingBottom: 14, marginBottom: 20 }}>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", margin: "0 0 4px 0", display: "flex", alignItems: "center", gap: 8 }}>
            <User size={19} color="#4f46e5" />
            <span>Profile Information</span>
          </h2>
          <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
            View and update your personal profile details. Email changes require verification before becoming active.
          </p>
        </div>

        {profileMsg.text && (
          <div
            style={{
              background: profileMsg.type === "error" ? "#fef2f2" : "#ecfdf5",
              border: `1px solid ${profileMsg.type === "error" ? "#fecaca" : "#a7f3d0"}`,
              color: profileMsg.type === "error" ? "#991b1b" : "#065f46",
              borderRadius: 8,
              padding: "12px 14px",
              marginBottom: 18,
              fontSize: 13,
              display: "flex",
              alignItems: "center",
              gap: 8
            }}
          >
            {profileMsg.type === "error" ? <AlertCircle size={17} /> : <CheckCircle2 size={17} />}
            <span>{profileMsg.text}</span>
          </div>
        )}

        <form onSubmit={handleSaveProfile}>
          <div className="far-account-form-grid">
            <div style={{ minWidth: 0 }}>
              <label style={labelStyle}>First Name</label>
              <input
                id="profile-firstname-input"
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                placeholder="First Name"
                required
                className="assetra-input-focus"
                style={{ ...inputStyle, minHeight: 44, fontSize: 15 }}
              />
            </div>

            <div style={{ minWidth: 0 }}>
              <label style={labelStyle}>Surname</label>
              <input
                id="profile-surname-input"
                type="text"
                value={surname}
                onChange={(e) => setSurname(e.target.value)}
                placeholder="Surname"
                className="assetra-input-focus"
                style={{ ...inputStyle, minHeight: 44, fontSize: 15 }}
              />
            </div>

            <div style={{ minWidth: 0 }}>
              <label style={labelStyle}>Email Address</label>
              <input
                id="profile-email-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="assetra-input-focus"
                style={{ ...inputStyle, minHeight: 44, fontSize: 15 }}
              />
            </div>
          </div>

          <button
            id="save-profile-btn"
            type="submit"
            disabled={profileSaving}
            className="far-btn"
            style={{
              background: "linear-gradient(135deg, #2563eb 0%, #4f46e5 100%)",
              color: "#ffffff",
              border: "none",
              borderRadius: 8,
              padding: "10px 22px",
              minHeight: 44,
              fontSize: 14,
              fontWeight: 600,
              cursor: profileSaving ? "not-allowed" : "pointer",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              gap: 8
            }}
          >
            {profileSaving ? <Loader2 size={16} className="animate-spin" /> : null}
            <span>{profileSaving ? "Saving..." : "Save Profile Details"}</span>
          </button>
        </form>

        {pendingEmail && (
          <form
            onSubmit={handleVerifyEmailChange}
            style={{
              marginTop: 18,
              padding: 16,
              background: "#eff6ff",
              border: "1px solid #bfdbfe",
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              gap: 12,
              flexWrap: "wrap"
            }}
          >
            <div style={{ flex: 1, minWidth: 220, fontSize: 13, color: "#1e3a8a" }}>
              Pending email verification for <strong>{pendingEmail}</strong>. Enter the 6-digit code sent to that address:
            </div>
            <input
              type="text"
              value={emailVerifyCode}
              onChange={(e) => setEmailVerifyCode(e.target.value)}
              placeholder="6-digit code"
              maxLength={6}
              style={{ ...inputStyle, width: 140 }}
            />
            <button
              type="submit"
              disabled={verifyingEmail}
              style={{
                background: "#2563eb",
                color: "#ffffff",
                border: "none",
                borderRadius: 8,
                padding: "9px 16px",
                fontSize: 13,
                fontWeight: 600,
                cursor: "pointer"
              }}
            >
              {verifyingEmail ? "Verifying..." : "Verify New Email"}
            </button>
          </form>
        )}
      </div>

      {/* ===================================================================== */}
      {/* SECTION B: MY ANALYSIS                                                */}
      {/* ===================================================================== */}
      <div id="account-my-analysis-section" className="far-account-card">
        <div style={{
          borderBottom: "1px solid #e2e8f0",
          paddingBottom: 14,
          marginBottom: 20,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 12
        }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", margin: "0 0 4px 0", display: "flex", alignItems: "center", gap: 8 }}>
              <FileSpreadsheet size={19} color="#2563eb" />
              <span>My Analysis</span>
            </h2>
            <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
              Complete history of your uploaded asset registers and calculated replacement value reports in Assetra ({filteredAnalyses.length} total).
            </p>
          </div>
          <button
            type="button"
            onClick={loadAccountData}
            style={{
              background: "#f8fafc",
              border: "1px solid #cbd5e1",
              borderRadius: 8,
              padding: "8px 14px",
              fontSize: 13,
              fontWeight: 600,
              color: "#334155",
              cursor: "pointer",
              display: "inline-flex",
              alignItems: "center",
              gap: 6
            }}
          >
            <RefreshCw size={14} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Search & Filters */}
        <div className="far-account-filters">
          <div style={{ position: "relative", flex: "1 1 240px", minWidth: 0 }}>
            <Search size={16} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
            <input
              id="my-analysis-search-input"
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              placeholder="Search by file name, company, or Analysis ID..."
              className="assetra-input-focus"
              style={{ ...inputStyle, paddingLeft: 36, minHeight: 44 }}
            />
          </div>

          <select
            id="my-analysis-status-filter"
            value={statusFilter}
            onChange={(e) => {
              setStatusFilter(e.target.value);
              setPage(1);
            }}
            className="assetra-input-focus"
            style={{ ...inputStyle, width: 170, minHeight: 44 }}
          >
            <option value="all">All Statuses</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="processing">Processing</option>
          </select>

          <input
            id="my-analysis-date-filter"
            type="date"
            value={dateFilter}
            onChange={(e) => {
              setDateFilter(e.target.value);
              setPage(1);
            }}
            className="assetra-input-focus"
            style={{ ...inputStyle, width: 170, minHeight: 44 }}
          />
          {dateFilter && (
            <button
              type="button"
              onClick={() => {
                setDateFilter("");
                setPage(1);
              }}
              style={{
                background: "#f1f5f9",
                border: "1px solid #cbd5e1",
                borderRadius: 8,
                padding: "0 14px",
                fontSize: 13,
                minHeight: 44,
                cursor: "pointer",
                color: "#475569"
              }}
            >
              Clear Date
            </button>
          )}
        </div>

        {analysesLoading ? (
          <div style={{ textAlign: "center", padding: "32px 0", color: "#64748b", fontSize: 14 }}>
            <Loader2 size={24} className="animate-spin" style={{ margin: "0 auto 8px" }} />
            Loading your analysis history...
          </div>
        ) : filteredAnalyses.length === 0 ? (
          <div style={{
            padding: "32px 16px",
            textAlign: "center",
            background: "#f8fafc",
            borderRadius: 8,
            border: "1px dashed #cbd5e1",
            color: "#64748b",
            fontSize: 14
          }}>
            No matching analyses found for your account.
          </div>
        ) : (
          <>
            <div className="assetra-table-container far-table-container" style={{ width: "100%", maxWidth: "100%", minWidth: 0, overflowX: "auto", WebkitOverflowScrolling: "touch", border: "1px solid #e2e8f0", borderRadius: 8, display: "block" }}>
              <table style={{ width: "100%", minWidth: 1000, borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0", textAlign: "left", color: "#475569" }}>
                    <th style={{ padding: "10px 12px" }}>Analysis ID</th>
                    <th style={{ padding: "10px 12px" }}>Uploaded Excel File</th>
                    <th style={{ padding: "10px 12px" }}>Upload Date</th>
                    <th style={{ padding: "10px 12px" }}>Analysis Date & Time</th>
                    <th style={{ padding: "10px 12px", textAlign: "right" }}>Total Assets</th>
                    <th style={{ padding: "10px 12px", textAlign: "right" }}>Calculated</th>
                    <th style={{ padding: "10px 12px", textAlign: "right" }}>Acquisition Value</th>
                    <th style={{ padding: "10px 12px", textAlign: "right" }}>Replacement Value</th>
                    <th style={{ padding: "10px 12px", textAlign: "right" }}>Total Difference</th>
                    <th style={{ padding: "10px 12px" }}>Status</th>
                    <th style={{ padding: "10px 12px", textAlign: "right" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedAnalyses.map((item) => {
                    const acq = Number(item.total_acquisition || 0);
                    const rep = Number(item.total_replacement || 0);
                    const diff = rep - acq;
                    const isCompleted = (item.status || "").toLowerCase() === "completed";
                    return (
                      <tr key={item.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "12px", fontWeight: 700, color: "#1e293b" }}>#{item.id}</td>
                        <td style={{ padding: "12px" }}>
                          <div style={{ fontWeight: 600, color: "#0f172a" }}>{item.original_filename}</div>
                          {item.company_name && (
                            <div style={{ fontSize: 11, color: "#64748b" }}>{item.company_name}</div>
                          )}
                        </td>
                        <td style={{ padding: "12px", color: "#475569", whiteSpace: "nowrap" }}>
                          {fmtDateOnly(item.created_at)}
                        </td>
                        <td style={{ padding: "12px", color: "#475569", whiteSpace: "nowrap" }}>
                          {fmtDateTime(item.completed_at || item.created_at)}
                        </td>
                        <td style={{ padding: "12px", textAlign: "right", fontWeight: 600 }}>{item.rows_total || 0}</td>
                        <td style={{ padding: "12px", textAlign: "right", color: "#16a34a", fontWeight: 600 }}>
                          {item.rows_calculated || 0}
                        </td>
                        <td style={{ padding: "12px", textAlign: "right", whiteSpace: "nowrap" }}>{fmtCurrency(acq)}</td>
                        <td style={{ padding: "12px", textAlign: "right", fontWeight: 700, color: "#1d4ed8", whiteSpace: "nowrap" }}>
                          {fmtCurrency(rep)}
                        </td>
                        <td style={{ padding: "12px", textAlign: "right", fontWeight: 600, color: diff >= 0 ? "#16a34a" : "#dc2626", whiteSpace: "nowrap" }}>
                          {diff >= 0 ? "+" : ""}{fmtCurrency(diff)}
                        </td>
                        <td style={{ padding: "12px" }}>
                          <span style={{
                            display: "inline-block",
                            padding: "3px 8px",
                            borderRadius: 9999,
                            fontSize: 11,
                            fontWeight: 700,
                            textTransform: "uppercase",
                            background: isCompleted ? "#dcfce7" : "#fee2e2",
                            color: isCompleted ? "#166534" : "#991b1b"
                          }}>
                            {isCompleted ? "Completed" : item.status || "Failed"}
                          </span>
                        </td>
                        <td style={{ padding: "12px", textAlign: "right", whiteSpace: "nowrap" }}>
                          <div style={{ display: "inline-flex", gap: 6 }}>
                            <button
                              type="button"
                              onClick={() => onOpenAnalysis(item.id)}
                              style={{
                                background: "#eff6ff",
                                color: "#1d4ed8",
                                border: "1px solid #bfdbfe",
                                borderRadius: 6,
                                padding: "5px 10px",
                                fontSize: 12,
                                fontWeight: 600,
                                cursor: "pointer",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 4
                              }}
                            >
                              <ExternalLink size={13} />
                              <span>Open</span>
                            </button>
                            {isCompleted && (
                              <button
                                type="button"
                                onClick={() => handleDownloadReport(item.id, item.company_name)}
                                style={{
                                  background: "#f8fafc",
                                  color: "#334155",
                                  border: "1px solid #cbd5e1",
                                  borderRadius: 6,
                                  padding: "5px 10px",
                                  fontSize: 12,
                                  fontWeight: 600,
                                  cursor: "pointer",
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: 4
                                }}
                              >
                                <Download size={13} />
                                <span>Excel</span>
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 14, fontSize: 13, color: "#64748b" }}>
                <span>
                  Page {page} of {totalPages} ({filteredAnalyses.length} records)
                </span>
                <div style={{ display: "flex", gap: 8 }}>
                  <button
                    type="button"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    style={{
                      padding: "6px 12px",
                      borderRadius: 6,
                      border: "1px solid #cbd5e1",
                      background: page <= 1 ? "#f1f5f9" : "#ffffff",
                      cursor: page <= 1 ? "not-allowed" : "pointer"
                    }}
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    style={{
                      padding: "6px 12px",
                      borderRadius: 6,
                      border: "1px solid #cbd5e1",
                      background: page >= totalPages ? "#f1f5f9" : "#ffffff",
                      cursor: page >= totalPages ? "not-allowed" : "pointer"
                    }}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* ===================================================================== */}
      {/* SECTION D: PERMANENTLY DELETE MY ACCOUNT                              */}
      {/* ===================================================================== */}
      <div
        id="delete-account-section"
        className="far-account-card"
        style={{
          background: "#fff5f5",
          border: "1px solid #feb2b2"
        }}
      >
        <h2 style={{ fontSize: 18, fontWeight: 700, color: "#991b1b", margin: "0 0 8px 0", display: "flex", alignItems: "center", gap: 8 }}>
          <Trash2 size={19} color="#dc2626" />
          <span>Delete Account</span>
        </h2>
        <p style={{ fontSize: 14, color: "#7f1d1d", margin: "0 0 18px 0", lineHeight: 1.5 }}>
          Once you delete your account, there is no going back. Your account and associated personal data will be permanently deleted.
        </p>
        <button
          id="open-delete-account-modal-btn"
          type="button"
          onClick={() => {
            setDeleteError("");
            setDeletePassword("");
            setDeleteConfirmText("");
            setDeleteChecked(false);
            setShowDeleteModal(true);
          }}
          style={{
            background: "#dc2626",
            color: "#ffffff",
            border: "none",
            borderRadius: 8,
            padding: "12px 22px",
            minHeight: 44,
            fontSize: 13,
            fontWeight: 700,
            letterSpacing: "0.03em",
            cursor: "pointer",
            boxShadow: "0 4px 12px rgba(220, 38, 38, 0.25)"
          }}
        >
          PERMANENTLY DELETE MY ACCOUNT
        </button>
      </div>

      {/* ===================================================================== */}
      {/* SECTION E: DASHBOARD AND LOGOUT                                       */}
      {/* ===================================================================== */}
      <div className="far-account-actions-bar">
        <button
          id="settings-back-to-dashboard-btn"
          type="button"
          onClick={onBackToDashboard}
          style={{
            background: "#f8fafc",
            color: "#1e293b",
            border: "1px solid #cbd5e1",
            borderRadius: 8,
            padding: "10px 18px",
            minHeight: 44,
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: 8
          }}
        >
          <ArrowLeft size={16} />
          <span>Back to Dashboard</span>
        </button>

        <button
          id="settings-sign-out-btn"
          type="button"
          onClick={onLogout || onSignOut}
          style={{
            background: "#fef2f2",
            color: "#dc2626",
            border: "1px solid #fecaca",
            borderRadius: 8,
            padding: "10px 18px",
            minHeight: 44,
            fontSize: 14,
            fontWeight: 600,
            cursor: "pointer",
            display: "inline-flex",
            alignItems: "center",
            gap: 8
          }}
        >
          <LogOut size={16} />
          <span>Sign Out</span>
        </button>
      </div>

      {/* ===================================================================== */}
      {/* PERMANENT ACCOUNT DELETION CONFIRMATION MODAL                         */}
      {/* ===================================================================== */}
      {showDeleteModal && (
        <div
          id="delete-account-modal"
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 10000,
            background: "rgba(15, 23, 42, 0.7)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: 16
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: 460,
              maxHeight: "calc(100dvh - 32px)",
              overflowY: "auto",
              WebkitOverflowScrolling: "touch",
              background: "#ffffff",
              borderRadius: 14,
              padding: "28px 26px",
              boxShadow: "0 25px 50px rgba(0, 0, 0, 0.35)",
              boxSizing: "border-box"
            }}
          >
            <h3 style={{ fontSize: 19, fontWeight: 700, color: "#991b1b", margin: "0 0 8px 0" }}>
              Confirm Permanent Account Deletion
            </h3>
            <p style={{ fontSize: 13, color: "#475569", margin: "0 0 16px 0", lineHeight: 1.5 }}>
              This action is <strong>permanent and irreversible</strong>. All of your profile information, uploaded FAR files, and saved analysis reports will be permanently deleted.
            </p>

            {deleteError && (
              <div style={{
                background: "#fef2f2",
                border: "1px solid #fecaca",
                color: "#991b1b",
                borderRadius: 8,
                padding: "10px 12px",
                marginBottom: 14,
                fontSize: 13
              }}>
                {deleteError}
              </div>
            )}

            <form onSubmit={handleConfirmDeleteAccount}>
              {activeUser?.has_password !== false && (
                <div style={{ marginBottom: 14 }}>
                  <label style={labelStyle}>Enter your password to verify your identity</label>
                  <input
                    id="delete-account-password-input"
                    type="password"
                    value={deletePassword}
                    onChange={(e) => setDeletePassword(e.target.value)}
                    placeholder="Current password"
                    required
                    style={inputStyle}
                  />
                </div>
              )}

              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>
                  Type <strong>DELETE</strong> to confirm
                </label>
                <input
                  id="delete-account-confirm-text-input"
                  type="text"
                  value={deleteConfirmText}
                  onChange={(e) => setDeleteConfirmText(e.target.value)}
                  placeholder="DELETE"
                  required
                  style={inputStyle}
                />
              </div>

              <label style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 8,
                fontSize: 13,
                color: "#334155",
                marginBottom: 20,
                cursor: "pointer"
              }}>
                <input
                  id="delete-account-checkbox"
                  type="checkbox"
                  checked={deleteChecked}
                  onChange={(e) => setDeleteChecked(e.target.checked)}
                  style={{ marginTop: 3 }}
                />
                <span>I understand that my account and all associated analyses will be permanently deleted.</span>
              </label>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
                <button
                  type="button"
                  onClick={() => setShowDeleteModal(false)}
                  disabled={deleteLoading}
                  style={{
                    background: "#f1f5f9",
                    color: "#334155",
                    border: "1px solid #cbd5e1",
                    borderRadius: 8,
                    padding: "9px 16px",
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: "pointer"
                  }}
                >
                  Cancel
                </button>
                <button
                  id="confirm-permanent-delete-btn"
                  type="submit"
                  disabled={deleteLoading}
                  style={{
                    background: "#dc2626",
                    color: "#ffffff",
                    border: "none",
                    borderRadius: 8,
                    padding: "9px 18px",
                    fontSize: 13,
                    fontWeight: 700,
                    cursor: deleteLoading ? "not-allowed" : "pointer"
                  }}
                >
                  {deleteLoading ? "Deleting Account..." : "Permanently Delete"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

