import React, { useState, useEffect, useMemo } from "react";
import {
  ShieldCheck, Users, Clock, Check, X, RefreshCw, AlertCircle,
  CheckCircle2, ArrowLeft, History, Lock, UserCheck, UserX, Search,
  FolderArchive, LogIn, ExternalLink, Download, FileSpreadsheet, Play,
  Settings, Sliders, Database, Layers, UserPlus, UserMinus, Crown, Shield, Trash2
} from "lucide-react";

export default function AdminDashboardScreen({ token, adminUser, apiBaseUrl, onBackToCalculator, onOpenAnalysis }) {
  // Main tabs: "users" | "activity" | "analyses" | "settings" | "pending"
  const [activeTab, setActiveTab] = useState("users");
  const [settingsSubTab, setSettingsSubTab] = useState("general"); // "general" | "advanced"
  const [pendingRequests, setPendingRequests] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [auditTotal, setAuditTotal] = useState(0);
  const [auditPage, setAuditPage] = useState(1);
  const [auditPageSize, setAuditPageSize] = useState(25);
  const [auditTotalPages, setAuditTotalPages] = useState(1);
  const [auditSearch, setAuditSearch] = useState("");
  const [auditUserFilter, setAuditUserFilter] = useState("");
  const [auditActionTypeFilter, setAuditActionTypeFilter] = useState("ALL");
  const [auditStatusFilter, setAuditStatusFilter] = useState("ALL");
  const [auditDateFrom, setAuditDateFrom] = useState("");
  const [auditDateTo, setAuditDateTo] = useState("");
  const [allUsers, setAllUsers] = useState([]);
  const [allAnalyses, setAllAnalyses] = useState([]);
  const [columnAliases, setColumnAliases] = useState([]);
  const [adminStats, setAdminStats] = useState(null);
  const [adminsList, setAdminsList] = useState([]);
  const [loadingAdmins, setLoadingAdmins] = useState(false);
  const [showAddAdminModal, setShowAddAdminModal] = useState(false);
  const [newAdminEmail, setNewAdminEmail] = useState("");
  const [addAdminLoading, setAddAdminLoading] = useState(false);
  const [addAdminError, setAddAdminError] = useState("");
  const [addAdminSuccess, setAddAdminSuccess] = useState("");
  const [demoteConfirmUser, setDemoteConfirmUser] = useState(null);
  const [demoteLoading, setDemoteLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState({});
  const [message, setMessage] = useState({ type: "", text: "" });
  const [searchQuery, setSearchQuery] = useState("");
  const [aliasStatusFilter, setAliasStatusFilter] = useState("all");

  const isPrimaryAdmin = Boolean(
    adminStats?.is_primary_admin ||
    adminUser?.is_primary_admin ||
    (adminStats?.primary_admin_email && adminUser?.email && adminStats.primary_admin_email.toLowerCase() === adminUser.email.toLowerCase()) ||
    adminUser?.email?.toLowerCase() === "communication.ins@shareindia.co.in"
  );

  const authHeaders = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {})
  };

  const fetchPendingRequests = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/admin/pending-requests`, { headers: authHeaders, credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        setPendingRequests(data);
      }
    } catch (e) {
      console.error("Failed to fetch pending requests:", e);
    }
  };

  const fetchAuditLogs = async (overrides = {}) => {
    try {
      const p = overrides.page ?? auditPage;
      const ps = overrides.pageSize ?? auditPageSize;
      const s = overrides.search !== undefined ? overrides.search : auditSearch;
      const u = overrides.user !== undefined ? overrides.user : auditUserFilter;
      const act = overrides.actionType !== undefined ? overrides.actionType : auditActionTypeFilter;
      const st = overrides.status !== undefined ? overrides.status : auditStatusFilter;
      const df = overrides.dateFrom !== undefined ? overrides.dateFrom : auditDateFrom;
      const dt = overrides.dateTo !== undefined ? overrides.dateTo : auditDateTo;

      const params = new URLSearchParams();
      params.set("page", String(p));
      params.set("page_size", String(ps));
      if (s && s.trim()) params.set("search", s.trim());
      if (u && u.trim()) params.set("user", u.trim());
      if (act && act !== "ALL") params.set("action_type", act);
      if (st && st !== "ALL") params.set("status", st);
      if (df) params.set("date_from", df);
      if (dt) params.set("date_to", dt);

      const res = await fetch(`${apiBaseUrl}/admin/audit-logs?${params.toString()}`, {
        headers: authHeaders,
        credentials: "include"
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data)) {
          setAuditLogs(data);
          setAuditTotal(data.length);
          setAuditTotalPages(1);
        } else {
          setAuditLogs(Array.isArray(data.items) ? data.items : []);
          setAuditTotal(typeof data.total === "number" ? data.total : (data.items?.length || 0));
          setAuditPage(typeof data.page === "number" ? data.page : p);
          setAuditTotalPages(typeof data.total_pages === "number" ? data.total_pages : 1);
        }
      }
    } catch (e) {
      console.error("Failed to fetch audit logs:", e);
    }
  };

  const fetchAllUsers = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/admin/users`, { headers: authHeaders, credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        setAllUsers(data);
      }
    } catch (e) {
      console.error("Failed to fetch users:", e);
    }
  };

  const fetchAllAnalyses = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/admin/analyses`, { headers: authHeaders, credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        setAllAnalyses(data);
      }
    } catch (e) {
      console.error("Failed to fetch all analyses:", e);
    }
  };

  const fetchAdminStats = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/admin/stats`, { headers: authHeaders, credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        setAdminStats(data);
      }
    } catch (e) {
      console.error("Failed to fetch admin stats:", e);
    }
  };

  const fetchColumnAliases = async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/admin/column-aliases`, { headers: authHeaders, credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        setColumnAliases(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.error("Failed to fetch column aliases:", e);
    }
  };

  const handleApproveAlias = async (aliasId) => {
    setActionLoading(prev => ({ ...prev, [`alias_${aliasId}`]: "approving" }));
    setMessage({ type: "", text: "" });
    try {
      const res = await fetch(`${apiBaseUrl}/admin/column-aliases/${aliasId}/approve`, {
        method: "POST",
        headers: authHeaders
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to approve column alias");
      setMessage({ type: "success", text: data.message || "Column alias approved and added to canonical cache." });
      await Promise.all([fetchColumnAliases(), fetchAuditLogs()]);
    } catch (err) {
      setMessage({ type: "error", text: err.message || "Failed to approve column alias." });
    } finally {
      setActionLoading(prev => ({ ...prev, [`alias_${aliasId}`]: null }));
    }
  };

  const handleRejectAlias = async (aliasId) => {
    setActionLoading(prev => ({ ...prev, [`alias_${aliasId}`]: "rejecting" }));
    setMessage({ type: "", text: "" });
    try {
      const res = await fetch(`${apiBaseUrl}/admin/column-aliases/${aliasId}/reject`, {
        method: "POST",
        headers: authHeaders
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to reject column alias");
      setMessage({ type: "success", text: data.message || "Column alias rejected." });
      await Promise.all([fetchColumnAliases(), fetchAuditLogs()]);
    } catch (err) {
      setMessage({ type: "error", text: err.message || "Failed to reject column alias." });
    } finally {
      setActionLoading(prev => ({ ...prev, [`alias_${aliasId}`]: null }));
    }
  };

  const handleRemoveAlias = async (aliasId) => {
    if (!window.confirm(`Are you sure you want to permanently remove column alias #${aliasId}?`)) {
      return;
    }
    setActionLoading(prev => ({ ...prev, [`alias_${aliasId}`]: "removing" }));
    setMessage({ type: "", text: "" });
    try {
      const res = await fetch(`${apiBaseUrl}/admin/column-aliases/${aliasId}`, {
        method: "DELETE",
        headers: authHeaders
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to remove column alias");
      setMessage({ type: "success", text: data.message || `Column alias #${aliasId} removed.` });
      await Promise.all([fetchColumnAliases(), fetchAuditLogs()]);
    } catch (err) {
      setMessage({ type: "error", text: err.message || "Failed to remove column alias." });
    } finally {
      setActionLoading(prev => ({ ...prev, [`alias_${aliasId}`]: null }));
    }
  };

  const fetchAdminsList = async () => {
    setLoadingAdmins(true);
    try {
      const res = await fetch(`${apiBaseUrl}/admin/admins`, {
        headers: authHeaders,
        credentials: "include"
      });
      if (res.ok) {
        const data = await res.json();
        setAdminsList(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      console.error("Failed to fetch admins list:", e);
    } finally {
      setLoadingAdmins(false);
    }
  };

  const handlePromoteAdmin = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    setAddAdminError("");
    setAddAdminSuccess("");
    const emailClean = (newAdminEmail || "").trim();
    if (!emailClean) {
      setAddAdminError("Please enter a valid registered user email address.");
      return;
    }
    setAddAdminLoading(true);
    try {
      const res = await fetch(`${apiBaseUrl}/admin/admins/promote`, {
        method: "POST",
        headers: authHeaders,
        credentials: "include",
        body: JSON.stringify({ email: emailClean })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Failed to promote user to Administrator.");
      }
      setAddAdminSuccess(data.message || `Successfully promoted ${emailClean} to Administrator.`);
      setNewAdminEmail("");
      await Promise.all([fetchAdminsList(), fetchAllUsers(), fetchAdminStats(), fetchAuditLogs()]);
      setTimeout(() => {
        setShowAddAdminModal(false);
        setAddAdminSuccess("");
      }, 1400);
    } catch (err) {
      setAddAdminError(err.message || "Failed to promote user.");
    } finally {
      setAddAdminLoading(false);
    }
  };

  const handleDemoteAdmin = async (userId) => {
    if (!userId) return;
    setDemoteLoading(true);
    setMessage({ type: "", text: "" });
    try {
      const res = await fetch(`${apiBaseUrl}/admin/admins/${userId}/demote`, {
        method: "POST",
        headers: authHeaders,
        credentials: "include"
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Failed to remove administrator privileges.");
      }
      setMessage({ type: "success", text: data.message || "Administrator privileges removed successfully." });
      setDemoteConfirmUser(null);
      await Promise.all([fetchAdminsList(), fetchAllUsers(), fetchAdminStats(), fetchAuditLogs()]);
    } catch (err) {
      setMessage({ type: "error", text: err.message || "Failed to remove administrator." });
    } finally {
      setDemoteLoading(false);
    }
  };

  const isAuthorizedAdmin = Boolean(token && adminUser && adminUser.role === "admin");
  const [accessDenied, setAccessDenied] = useState(!isAuthorizedAdmin);

  const loadAllData = async () => {
    if (!isAuthorizedAdmin) {
      setAccessDenied(true);
      return;
    }
    setLoading(true);
    await Promise.all([
      fetchPendingRequests(),
      fetchAuditLogs(),
      fetchAllUsers(),
      fetchAdminsList(),
      fetchAllAnalyses(),
      fetchAdminStats(),
      fetchColumnAliases()
    ]);
    setLoading(false);
  };

  useEffect(() => {
    if (!isAuthorizedAdmin) {
      setAccessDenied(true);
      return;
    }
    loadAllData();
  }, [isAuthorizedAdmin]);

  if (accessDenied || !isAuthorizedAdmin) {
    return (
      <div
        id="admin-access-denied"
        style={{
          maxWidth: 520,
          margin: "40px auto",
          width: "calc(100% - 32px)",
          boxSizing: "border-box",
          background: "#ffffff",
          border: "1px solid #FECACA",
          borderRadius: 12,
          padding: "36px 20px",
          textAlign: "center",
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)"
        }}
      >
        <h2 style={{ fontSize: 20, fontWeight: 700, color: "#991B1B", margin: "0 0 8px" }}>
          Access denied
        </h2>
        <p style={{ fontSize: 14, color: "#64748B", margin: "0 0 24px", lineHeight: 1.5 }}>
          You do not have administrator privileges to view this page. No administrator data has been loaded.
        </p>
        {onBackToCalculator && (
          <button
            onClick={onBackToCalculator}
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
        )}
      </div>
    );
  }

  const handleApprove = async (userId, userEmail) => {
    setActionLoading(prev => ({ ...prev, [userId]: "approving" }));
    setMessage({ type: "", text: "" });
    try {
      const res = await fetch(`${apiBaseUrl}/admin/users/${userId}/approve`, {
        method: "POST",
        headers: authHeaders
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Approval failed");
      setMessage({ type: "success", text: data.message || `User #${userId} approved.` });
      await Promise.all([fetchPendingRequests(), fetchAllUsers(), fetchAuditLogs()]);
    } catch (err) {
      setMessage({ type: "error", text: err.message || "Failed to approve user." });
    } finally {
      setActionLoading(prev => ({ ...prev, [userId]: null }));
    }
  };

  const handleReject = async (userId, userEmail) => {
    setActionLoading(prev => ({ ...prev, [userId]: "rejecting" }));
    setMessage({ type: "", text: "" });
    try {
      const res = await fetch(`${apiBaseUrl}/admin/users/${userId}/reject`, {
        method: "POST",
        headers: authHeaders
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Rejection failed");
      setMessage({ type: "success", text: data.message || `User #${userId} rejected.` });
      await Promise.all([fetchPendingRequests(), fetchAllUsers(), fetchAuditLogs()]);
    } catch (err) {
      setMessage({ type: "error", text: err.message || "Failed to reject user." });
    } finally {
      setActionLoading(prev => ({ ...prev, [userId]: null }));
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "—";
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return dateStr;
      return d.toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true
      });
    } catch {
      return dateStr;
    }
  };

  const ACTION_PLAIN_WORDS = {
    LOGIN_SUCCESS: "Signed in",
    LOGIN_FAILED: "Sign-in failed",
    GOOGLE_LOGIN: "Google sign-in",
    LOGOUT: "Signed out",
    FILE_UPLOAD: "Uploaded FAR file",
    UPLOAD_FAILED: "Upload failed",
    ANALYSIS_STARTED: "Analysis started",
    ANALYSIS_COMPLETED: "Analysis completed",
    ANALYSIS_FAILED: "Analysis failed",
    PROFILE_UPDATED: "Profile updated",
    PASSWORD_CHANGED: "Password changed",
    ACCOUNT_DELETED: "Account deleted",
    USER_CREATED: "User account created",
    USER_APPROVED: "User account approved",
    USER_REJECTED: "User account rejected",
    USER_ENABLED: "User account enabled",
    USER_DISABLED: "User account disabled",
    PASSWORD_RESET_REQUESTED: "Password reset requested",
  };

  const getPlainAction = (log) => {
    if (log.action_plain) return log.action_plain;
    const act = (log.activity_type || log.action || "").toUpperCase();
    return ACTION_PLAIN_WORDS[act] || act.replace(/_/g, " ").toLowerCase();
  };

  const getActionBadgeColor = (actionType) => {
    const act = (actionType || "").toUpperCase();
    if (act.includes("FAILED") || act.includes("REJECTED") || act.includes("BLOCKED") || act.includes("LOCKOUT")) {
      return { bg: "#fee2e2", color: "#991b1b", border: "#fecaca" };
    }
    if (act.includes("SUCCESS") || act.includes("APPROVED") || act.includes("COMPLETED")) {
      return { bg: "#dcfce7", color: "#166534", border: "#bbf7d0" };
    }
    if (act.includes("UPLOAD") || act.includes("STARTED")) {
      return { bg: "#eff6ff", color: "#1d4ed8", border: "#bfdbfe" };
    }
    if (act.includes("PROFILE") || act.includes("PASSWORD") || act.includes("USER_") || act.includes("ACCOUNT")) {
      return { bg: "#f3e8ff", color: "#6b21a8", border: "#e9d5ff" };
    }
    return { bg: "#f1f5f9", color: "#475569", border: "#e2e8f0" };
  };

  const fmtCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0
    }).format(val || 0);
  };

  const getUserDisplay = (userId) => {
    const u = allUsers.find(x => x.id === userId);
    if (!u) return `User #${userId}`;
    return u.name ? `${u.name} (#${u.id})` : `User #${u.id}`;
  };

  const handleDownloadAnalysis = async (id, company, e) => {
    if (e) e.stopPropagation();
    try {
      const res = await fetch(`${apiBaseUrl}/analyses/${id}/download`, {
        headers: { Authorization: `Bearer ${token}` }
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
      alert("Failed to download analysis report.");
    }
  };

  const filteredAnalyses = allAnalyses.filter(a => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    const userStr = getUserDisplay(a.user_id).toLowerCase();
    const companyStr = (a.company_name || "").toLowerCase();
    const fileStr = (a.original_filename || "").toLowerCase();
    const industryStr = (a.industry || "").toLowerCase();
    return companyStr.includes(q) || fileStr.includes(q) || userStr.includes(q) || industryStr.includes(q);
  });

  const filteredUsers = allUsers.filter(u => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (u.email || "").toLowerCase().includes(q) || (u.name || "").toLowerCase().includes(q) || String(u.id).includes(q);
  });

  const conflictHeaderSet = useMemo(() => {
    const map = {};
    (columnAliases || []).forEach(a => {
      const norm = (a.normalized_header || "").trim().toLowerCase();
      if (!norm) return;
      if (!map[norm]) map[norm] = new Set();
      map[norm].add(a.canonical_field);
    });
    const s = new Set();
    Object.entries(map).forEach(([k, set]) => {
      if (set.size > 1) s.add(k);
    });
    return s;
  }, [columnAliases]);

  const pendingOrConflictingAliases = useMemo(() => {
    return (columnAliases || []).filter(a => {
      if (a.status === "pending" || a.status === "conflict") return true;
      const norm = (a.normalized_header || "").trim().toLowerCase();
      if (norm && conflictHeaderSet.has(norm)) return true;
      return false;
    });
  }, [columnAliases, conflictHeaderSet]);

  const filteredAliases = columnAliases.filter(a => {
    if (aliasStatusFilter === "conflict") {
      const norm = (a.normalized_header || "").trim().toLowerCase();
      const isConflict = a.status === "conflict" || (norm && conflictHeaderSet.has(norm));
      if (!isConflict) return false;
    } else if (aliasStatusFilter !== "all" && a.status !== aliasStatusFilter) {
      return false;
    }
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (a.original_header || "").toLowerCase().includes(q) || (a.canonical_field || "").toLowerCase().includes(q);
  });

  const showPendingTab = Boolean(adminStats?.require_admin_approval || pendingRequests.length > 0);

  return (
    <div className="admin-dashboard-container" style={{ maxWidth: 1200, margin: "0 auto", padding: "0 16px 60px", boxSizing: "border-box", width: "100%" }}>
      <style>{`
        /* Responsive styles for Admin Dashboard */
        .admin-dashboard-container {
          max-width: 1200px;
          margin: 0 auto;
          padding: 0 16px 60px;
          box-sizing: border-box;
          width: 100%;
        }

        .admin-top-banner {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          justify-content: space-between;
          gap: 14px;
          margin-bottom: 20px;
        }

        .admin-header-left {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
        }

        .admin-title-wrap {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .admin-stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 14px;
          margin-bottom: 24px;
        }

        .admin-stat-card {
          background: #ffffff;
          border-radius: 12px;
          padding: 16px 18px;
          border: 1px solid #e2e8f0;
          box-shadow: 0 1px 3px rgba(0,0,0,0.04);
          display: flex;
          align-items: center;
          gap: 14px;
          min-width: 0;
        }

        .admin-stat-card-icon {
          width: 42px;
          height: 42px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .admin-stat-card-label {
          font-size: 11px;
          font-weight: 600;
          color: #64748b;
          text-transform: uppercase;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .admin-stat-card-value {
          font-size: 22px;
          font-weight: 800;
          color: #0f172a;
          margin-top: 2px;
        }

        .admin-nav-tabs {
          display: flex;
          gap: 8px;
          border-bottom: 1px solid #e2e8f0;
          margin-bottom: 20px;
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
          scrollbar-width: none;
          -ms-overflow-style: none;
          padding-bottom: 2px;
        }

        .admin-nav-tabs::-webkit-scrollbar {
          display: none;
        }

        .admin-tab-btn {
          flex-shrink: 0;
          white-space: nowrap;
        }

        .admin-panel-header {
          padding: 16px 20px;
          border-bottom: 1px solid #e2e8f0;
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }

        .admin-panel-search {
          position: relative;
          min-width: 260px;
        }

        .admin-activity-filters {
          padding: 14px 20px;
          background: #f8fafc;
          border-bottom: 1px solid #e2e8f0;
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
          gap: 10px;
          align-items: end;
        }

        .admin-table-scroll-container {
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
          width: 100%;
          scrollbar-width: thin;
        }

        .admin-table-scroll-container::-webkit-scrollbar {
          height: 6px;
        }

        .admin-table-scroll-container::-webkit-scrollbar-track {
          background: #f1f5f9;
        }

        .admin-table-scroll-container::-webkit-scrollbar-thumb {
          background: #cbd5e1;
          border-radius: 3px;
        }

        .admin-pagination-footer {
          padding: 12px 20px;
          border-top: 1px solid #e2e8f0;
          background: #f8fafc;
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
          font-size: 12px;
          color: #475569;
        }

        .admin-settings-subtabs {
          display: flex;
          gap: 10px;
          border-bottom: 1px solid #e2e8f0;
          padding-bottom: 12px;
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
          scrollbar-width: none;
        }

        .admin-settings-subtabs::-webkit-scrollbar {
          display: none;
        }

        .admin-subtab-btn {
          flex-shrink: 0;
          white-space: nowrap;
        }

        .admin-config-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
          gap: 16px;
        }

        .admin-modal-card {
          background: #ffffff;
          border-radius: 16px;
          width: 100%;
          max-width: 480px;
          max-height: 90vh;
          overflow-y: auto;
          padding: 24px;
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.25);
          border: 1px solid #e2e8f0;
          box-sizing: border-box;
        }

        /* Breakpoint: Tablets and below (<= 768px) */
        @media (max-width: 768px) {
          .admin-stats-grid {
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
          }
          .admin-stats-grid > .admin-stat-card:last-child {
            grid-column: span 2;
          }
          .admin-activity-filters {
            grid-template-columns: repeat(2, 1fr);
            padding: 12px 14px;
          }
        }

        /* Breakpoint: Mobile screens (<= 640px) */
        @media (max-width: 640px) {
          .admin-dashboard-container {
            padding: 0 12px 40px;
          }
          .admin-top-banner {
            flex-direction: column;
            align-items: stretch;
            gap: 12px;
          }
          .admin-header-left {
            flex-direction: column;
            align-items: stretch;
            gap: 10px;
          }
          .admin-title-wrap {
            width: 100%;
          }
          .admin-header-right {
            width: 100%;
          }
          .admin-header-right button {
            width: 100%;
            justify-content: center;
          }
          .admin-panel-header {
            flex-direction: column;
            align-items: stretch;
            padding: 12px 14px;
            gap: 10px;
          }
          .admin-panel-search {
            min-width: 0 !important;
            width: 100% !important;
          }
          .admin-pagination-footer {
            flex-direction: column;
            align-items: stretch;
            padding: 12px 14px;
            text-align: center;
          }
          .admin-pagination-controls {
            justify-content: center !important;
            width: 100%;
          }
          .admin-config-grid {
            grid-template-columns: 1fr;
          }
          .admin-modal-card {
            padding: 18px 14px;
            border-radius: 12px;
          }
        }

        /* Breakpoint: Small Mobile screens (<= 480px) */
        @media (max-width: 480px) {
          .admin-stat-card {
            padding: 10px 12px;
            gap: 10px;
          }
          .admin-stat-card-icon {
            width: 34px;
            height: 34px;
          }
          .admin-stat-card-icon svg {
            width: 16px;
            height: 16px;
          }
          .admin-stat-card-label {
            font-size: 10px;
          }
          .admin-stat-card-value {
            font-size: 18px;
          }
          .admin-activity-filters {
            grid-template-columns: 1fr;
          }
        }

        /* Breakpoint: Very small screens (<= 360px) */
        @media (max-width: 360px) {
          .admin-stats-grid {
            grid-template-columns: 1fr;
          }
          .admin-stats-grid > .admin-stat-card:last-child {
            grid-column: span 1;
          }
        }
      `}</style>

      {/* Top Banner Navigation */}
      <div className="admin-top-banner">
        <div className="admin-header-left">
          <button
            onClick={onBackToCalculator}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "#ffffff",
              border: "1px solid #cbd5e1",
              borderRadius: 8,
              padding: "8px 14px",
              fontSize: 13,
              fontWeight: 600,
              color: "#334155",
              cursor: "pointer",
              flexShrink: 0
            }}
          >
            <ArrowLeft size={16} />
            <span>Back to Calculator</span>
          </button>
          <div className="admin-title-wrap">
            <div style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: "#4f46e5",
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0
            }}>
              <ShieldCheck size={20} />
            </div>
            <div>
              <h1 style={{ fontSize: 20, fontWeight: 700, color: "#0f172a", margin: 0 }}>
                Admin Dashboard
              </h1>
              <p style={{ fontSize: 12, color: "#64748b", margin: 0 }}>
                Manage users, monitor unified activity timeline, review analyses and settings
              </p>
            </div>
          </div>
        </div>

        <div className="admin-header-right" style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <button
            onClick={loadAllData}
            disabled={loading}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              background: "#ffffff",
              border: "1px solid #cbd5e1",
              borderRadius: 8,
              padding: "8px 14px",
              fontSize: 13,
              fontWeight: 600,
              color: "#334155",
              cursor: loading ? "not-allowed" : "pointer",
              flexShrink: 0
            }}
          >
            <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
            <span>{loading ? "Refreshing..." : "Refresh"}</span>
          </button>
        </div>
      </div>

      {/* Message Banner */}
      {message.text && (
        <div style={{
          padding: "12px 16px",
          borderRadius: 8,
          marginBottom: 20,
          display: "flex",
          alignItems: "center",
          gap: 10,
          background: message.type === "success" ? "#f0fdf4" : "#fef2f2",
          border: `1px solid ${message.type === "success" ? "#bbf7d0" : "#fecaca"}`,
          color: message.type === "success" ? "#166534" : "#991b1b",
          fontSize: 13
        }}>
          {message.type === "success" ? <CheckCircle2 size={18} /> : <AlertCircle size={18} />}
          <span style={{ flex: 1 }}>{message.text}</span>
          <button
            onClick={() => setMessage({ type: "", text: "" })}
            style={{ background: "none", border: "none", cursor: "pointer", color: "inherit", padding: 2 }}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Admin KPI Summary Stat Cards */}
      <div className="admin-stats-grid">
        {/* Card 1: Total Users */}
        <div className="admin-stat-card">
          <div className="admin-stat-card-icon" style={{
            background: "#eff6ff",
            color: "#2563eb"
          }}>
            <Users size={20} />
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div className="admin-stat-card-label">
              Registered Users
            </div>
            <div className="admin-stat-card-value">
              {adminStats?.total_registered_users ?? allUsers.length}
            </div>
          </div>
        </div>

        {/* Card 2: Total Activity Records */}
        <div className="admin-stat-card">
          <div className="admin-stat-card-icon" style={{
            background: "#e0e7ff",
            color: "#4f46e5"
          }}>
            <History size={20} />
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div className="admin-stat-card-label">
              Total Activity Events
            </div>
            <div className="admin-stat-card-value">
              {auditTotal || auditLogs.length}
            </div>
          </div>
        </div>

        {/* Card 3: Total Uploaded Files */}
        <div className="admin-stat-card">
          <div className="admin-stat-card-icon" style={{
            background: "#fef3c7",
            color: "#d97706"
          }}>
            <FolderArchive size={20} />
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div className="admin-stat-card-label">
              Total Uploaded Files
            </div>
            <div className="admin-stat-card-value">
              {adminStats?.total_uploaded_files ?? allAnalyses.length}
            </div>
          </div>
        </div>

        {/* Card 4: Total Completed Analyses */}
        <div className="admin-stat-card">
          <div className="admin-stat-card-icon" style={{
            background: "#dcfce7",
            color: "#16a34a"
          }}>
            <CheckCircle2 size={20} />
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div className="admin-stat-card-label">
              Completed Analyses
            </div>
            <div className="admin-stat-card-value">
              {adminStats?.total_completed_analyses ?? allAnalyses.filter(a => a.status === "completed").length}
            </div>
          </div>
        </div>

        {/* Card 5: Total Failed Analyses */}
        <div className="admin-stat-card">
          <div className="admin-stat-card-icon" style={{
            background: "#fee2e2",
            color: "#dc2626"
          }}>
            <AlertCircle size={20} />
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div className="admin-stat-card-label">
              Failed Analyses
            </div>
            <div className="admin-stat-card-value" style={{ color: "#dc2626" }}>
              {adminStats?.total_failed_analyses ?? allAnalyses.filter(a => (a.rows_calculated || 0) === 0).length}
            </div>
          </div>
        </div>
      </div>

      {/* Main Navigation Tabs */}
      <div className="admin-nav-tabs">
        {/* Main Tab 1: Users */}
        <button
          id="admin-tab-users"
          className="admin-tab-btn"
          onClick={() => setActiveTab("users")}
          style={{
            padding: "10px 16px",
            border: "none",
            borderBottom: activeTab === "users" ? "2px solid #4f46e5" : "2px solid transparent",
            background: "none",
            fontSize: 14,
            fontWeight: 600,
            color: activeTab === "users" ? "#4f46e5" : "#64748b",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
            whiteSpace: "nowrap"
          }}
        >
          <Users size={16} />
          <span>Users ({allUsers.length})</span>
        </button>

        {/* Main Tab 2: Activity (Unified Timeline) */}
        <button
          id="admin-tab-activity"
          className="admin-tab-btn"
          onClick={() => setActiveTab("activity")}
          style={{
            padding: "10px 16px",
            border: "none",
            borderBottom: activeTab === "activity" ? "2px solid #4f46e5" : "2px solid transparent",
            background: "none",
            fontSize: 14,
            fontWeight: 600,
            color: activeTab === "activity" ? "#4f46e5" : "#64748b",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
            whiteSpace: "nowrap"
          }}
        >
          <History size={16} />
          <span>Activity ({auditTotal || auditLogs.length})</span>
        </button>

        {/* Main Tab 3: Analyses */}
        <button
          id="admin-tab-analyses"
          className="admin-tab-btn"
          onClick={() => setActiveTab("analyses")}
          style={{
            padding: "10px 16px",
            border: "none",
            borderBottom: activeTab === "analyses" ? "2px solid #4f46e5" : "2px solid transparent",
            background: "none",
            fontSize: 14,
            fontWeight: 600,
            color: activeTab === "analyses" ? "#4f46e5" : "#64748b",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
            whiteSpace: "nowrap"
          }}
        >
          <FolderArchive size={16} />
          <span>Analyses ({allAnalyses.length})</span>
        </button>

        {/* Main Tab 4: Settings (Houses Column Aliases & System Config) */}
        <button
          id="admin-tab-settings"
          className="admin-tab-btn"
          onClick={() => setActiveTab("settings")}
          style={{
            padding: "10px 16px",
            border: "none",
            borderBottom: activeTab === "settings" ? "2px solid #4f46e5" : "2px solid transparent",
            background: "none",
            fontSize: 14,
            fontWeight: 600,
            color: activeTab === "settings" ? "#4f46e5" : "#64748b",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
            whiteSpace: "nowrap"
          }}
        >
          <Settings size={16} />
          <span>Settings</span>
          {pendingOrConflictingAliases.length > 0 && (
            <span
              id="settings-alias-badge"
              title={`${pendingOrConflictingAliases.length} pending or conflicting alias${pendingOrConflictingAliases.length > 1 ? "es" : ""}`}
              style={{
                background: "#dc2626",
                color: "#ffffff",
                fontSize: 11,
                fontWeight: 700,
                padding: "2px 8px",
                borderRadius: 12
              }}
            >
              {pendingOrConflictingAliases.length}
            </span>
          )}
        </button>

        {/* Tab 5: Pending Requests (Shown ONLY if approval required or requests exist) */}
        {showPendingTab && (
          <button
            id="admin-tab-pending"
            className="admin-tab-btn"
            onClick={() => setActiveTab("pending")}
            style={{
              padding: "10px 16px",
              border: "none",
              borderBottom: activeTab === "pending" ? "2px solid #4f46e5" : "2px solid transparent",
              background: "none",
              fontSize: 14,
              fontWeight: 600,
              color: activeTab === "pending" ? "#4f46e5" : "#64748b",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 8,
              whiteSpace: "nowrap"
            }}
          >
            <Clock size={16} />
            <span>Pending Requests</span>
            {pendingRequests.length > 0 && (
              <span style={{
                background: "#ef4444",
                color: "#ffffff",
                fontSize: 11,
                fontWeight: 700,
                padding: "2px 8px",
                borderRadius: 12
              }}>
                {pendingRequests.length}
              </span>
            )}
          </button>
        )}
      </div>

      {/* =========================================================================
          PANEL 1: USERS
          ========================================================================= */}
      {activeTab === "users" && (
        <div
          id="admin-users-panel"
          style={{
            background: "#ffffff",
            borderRadius: 12,
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
            overflow: "hidden"
          }}
        >
          <div className="admin-panel-header">
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1e293b", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                <Users size={18} color="#4f46e5" />
                System Users ({filteredUsers.length})
              </h2>
              <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0 0" }}>
                Inspect registered user accounts, role authorizations, account status, and login timestamps
              </p>
            </div>
            <div className="admin-panel-search">
              <Search size={15} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search user by name, email, or ID..."
                style={{
                  width: "100%",
                  padding: "8px 12px 8px 34px",
                  fontSize: 13,
                  border: "1px solid #cbd5e1",
                  borderRadius: 6,
                  outline: "none",
                  boxSizing: "border-box"
                }}
              />
            </div>
          </div>

          <div className="admin-table-scroll-container">
            <table style={{ width: "100%", minWidth: 850, borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f8fafc", textAlign: "left", color: "#475569", borderBottom: "1px solid #e2e8f0" }}>
                  <th style={{ padding: "12px 16px", fontWeight: 600 }}>ID</th>
                  <th style={{ padding: "12px 16px", fontWeight: 600 }}>Name</th>
                  <th style={{ padding: "12px 16px", fontWeight: 600 }}>Email Address</th>
                  <th style={{ padding: "12px 16px", fontWeight: 600 }}>Role</th>
                  <th style={{ padding: "12px 16px", fontWeight: 600 }}>Status</th>
                  <th style={{ padding: "12px 16px", fontWeight: 600 }}>Analyses</th>
                  <th style={{ padding: "12px 16px", fontWeight: 600 }}>Last Login</th>
                  <th style={{ padding: "12px 16px", fontWeight: 600 }}>Registered On</th>
                  <th style={{ padding: "12px 16px", fontWeight: 600, textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map(user => {
                  const userAnalysesCount = allAnalyses.filter(a => a.user_id === user.id).length;
                  const isPrimary = (user.email || "").toLowerCase() === (adminStats?.primary_admin_email || "communication.ins@shareindia.co.in").toLowerCase();
                  return (
                    <tr key={user.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "12px 16px", color: "#94a3b8", fontWeight: 600 }}>#{user.id}</td>
                      <td style={{ padding: "12px 16px", fontWeight: 600, color: "#1e293b" }}>{user.name}</td>
                      <td style={{ padding: "12px 16px", color: "#475569" }}><code>{user.email}</code></td>
                      <td style={{ padding: "12px 16px" }}>
                        <span style={{
                          background: user.role === "admin" ? (isPrimary ? "#fef3c7" : "#e0e7ff") : "#f1f5f9",
                          color: user.role === "admin" ? (isPrimary ? "#b45309" : "#4338ca") : "#475569",
                          padding: "2px 8px",
                          borderRadius: 6,
                          fontSize: 11,
                          fontWeight: 700,
                          textTransform: "uppercase",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4
                        }}>
                          {user.role === "admin" && (isPrimary ? <Crown size={11} /> : <Shield size={11} />)}
                          {isPrimary ? "Primary Admin" : user.role}
                        </span>
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <span style={{
                          background: user.status === "active" ? "#dcfce7" : user.status === "pending" ? "#fef3c7" : "#fee2e2",
                          color: user.status === "active" ? "#15803d" : user.status === "pending" ? "#b45309" : "#b91c1c",
                          padding: "2px 8px",
                          borderRadius: 6,
                          fontSize: 11,
                          fontWeight: 600,
                          textTransform: "uppercase"
                        }}>
                          {user.status || (user.is_active ? "active" : "disabled")}
                        </span>
                      </td>
                      <td style={{ padding: "12px 16px", color: "#0f172a", fontWeight: 600 }}>
                        {userAnalysesCount} file{userAnalysesCount === 1 ? "" : "s"}
                      </td>
                      <td style={{ padding: "12px 16px", color: user.last_login_at ? "#0f172a" : "#94a3b8", fontWeight: user.last_login_at ? 600 : 400, whiteSpace: "nowrap" }}>
                        {user.last_login_at ? formatDate(user.last_login_at) : <span style={{ fontStyle: "italic" }}>Never logged in</span>}
                      </td>
                      <td style={{ padding: "12px 16px", color: "#64748b", whiteSpace: "nowrap" }}>
                        {formatDate(user.created_at)}
                      </td>
                      <td style={{ padding: "12px 16px", textAlign: "right" }}>
                        {user.role === "admin" ? (
                          adminsList.length <= 1 ? (
                            <span style={{ fontSize: 11, color: "#94a3b8", fontStyle: "italic" }}>Only Admin</span>
                          ) : (
                            <button
                              onClick={() => setDemoteConfirmUser(user)}
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 4,
                                background: "#fee2e2",
                                color: "#b91c1c",
                                border: "1px solid #fecaca",
                                borderRadius: 6,
                                padding: "4px 8px",
                                fontSize: 11,
                                fontWeight: 600,
                                cursor: "pointer"
                              }}
                            >
                              <UserMinus size={12} />
                              <span>Remove Admin</span>
                            </button>
                          )
                        ) : (
                          <button
                            onClick={() => {
                              setNewAdminEmail(user.email);
                              setAddAdminError("");
                              setAddAdminSuccess("");
                              setShowAddAdminModal(true);
                            }}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 4,
                              background: "#eff6ff",
                              color: "#1d4ed8",
                              border: "1px solid #bfdbfe",
                              borderRadius: 6,
                              padding: "4px 8px",
                              fontSize: 11,
                              fontWeight: 600,
                              cursor: "pointer"
                            }}
                          >
                            <UserPlus size={12} />
                            <span>Make Admin</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* =========================================================================
          PANEL 2: ACTIVITY (UNIFIED TIMELINE)
          ========================================================================= */}
      {activeTab === "activity" && (
        <div
          id="admin-activity-panel"
          style={{
            background: "#ffffff",
            borderRadius: 12,
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
            overflow: "hidden"
          }}
        >
          <div className="admin-panel-header">
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1e293b", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                <History size={18} color="#4f46e5" />
                Activity Timeline ({auditTotal})
              </h2>
              <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0 0" }}>
                Unified timeline merging sign-in attempts, file uploads, calculation analyses, and account actions
              </p>
            </div>
            <button
              onClick={() => {
                setAuditSearch("");
                setAuditUserFilter("");
                setAuditActionTypeFilter("ALL");
                setAuditStatusFilter("ALL");
                setAuditDateFrom("");
                setAuditDateTo("");
                setAuditPage(1);
                fetchAuditLogs({
                  page: 1,
                  search: "",
                  user: "",
                  actionType: "ALL",
                  status: "ALL",
                  dateFrom: "",
                  dateTo: ""
                });
              }}
              style={{
                background: "#f8fafc",
                border: "1px solid #cbd5e1",
                borderRadius: 6,
                padding: "7px 12px",
                fontSize: 12,
                fontWeight: 600,
                color: "#475569",
                cursor: "pointer",
                flexShrink: 0
              }}
            >
              Reset Filters
            </button>
          </div>

          {/* Search & Filters Bar */}
          <div className="admin-activity-filters">
            {/* Filter 1: Search Keyword */}
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: "#475569", marginBottom: 4 }}>
                Search Keyword
              </label>
              <div style={{ position: "relative" }}>
                <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
                <input
                  id="activity-search-input"
                  type="text"
                  value={auditSearch}
                  onChange={(e) => {
                    const val = e.target.value;
                    setAuditSearch(val);
                    setAuditPage(1);
                    fetchAuditLogs({ page: 1, search: val });
                  }}
                  placeholder="Name, file, IP, or details..."
                  style={{
                    width: "100%",
                    padding: "7px 10px 7px 30px",
                    fontSize: 12,
                    border: "1px solid #cbd5e1",
                    borderRadius: 6,
                    background: "#ffffff",
                    boxSizing: "border-box"
                  }}
                />
              </div>
            </div>

            {/* Filter 2: Filter by User */}
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: "#475569", marginBottom: 4 }}>
                Filter by User
              </label>
              <select
                id="activity-user-filter"
                value={auditUserFilter}
                onChange={(e) => {
                  const val = e.target.value;
                  setAuditUserFilter(val);
                  setAuditPage(1);
                  fetchAuditLogs({ page: 1, user: val });
                }}
                style={{
                  width: "100%",
                  padding: "7px 10px",
                  fontSize: 12,
                  border: "1px solid #cbd5e1",
                  borderRadius: 6,
                  background: "#ffffff"
                }}
              >
                <option value="">All Users</option>
                {allUsers.map((u) => (
                  <option key={u.id} value={String(u.id)}>
                    {u.name || `User #${u.id}`} (#{u.id})
                  </option>
                ))}
              </select>
            </div>

            {/* Filter 3: Action Type (sign-in, upload, analysis, account) */}
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: "#475569", marginBottom: 4 }}>
                Action Type
              </label>
              <select
                id="activity-action-type-filter"
                value={auditActionTypeFilter}
                onChange={(e) => {
                  const val = e.target.value;
                  setAuditActionTypeFilter(val);
                  setAuditPage(1);
                  fetchAuditLogs({ page: 1, actionType: val });
                }}
                style={{
                  width: "100%",
                  padding: "7px 10px",
                  fontSize: 12,
                  border: "1px solid #cbd5e1",
                  borderRadius: 6,
                  background: "#ffffff"
                }}
              >
                <option value="ALL">All Actions</option>
                <option value="sign-in">Sign-in (Logins, Google, Logouts)</option>
                <option value="upload">Upload (FAR Files & Failures)</option>
                <option value="analysis">Analysis (Started, Completed, Failed)</option>
                <option value="account">Account (Creation, Approval, Updates)</option>
              </select>
            </div>

            {/* Filter 4: Status Filter */}
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: "#475569", marginBottom: 4 }}>
                Status
              </label>
              <select
                id="activity-status-filter"
                value={auditStatusFilter}
                onChange={(e) => {
                  const val = e.target.value;
                  setAuditStatusFilter(val);
                  setAuditPage(1);
                  fetchAuditLogs({ page: 1, status: val });
                }}
                style={{
                  width: "100%",
                  padding: "7px 10px",
                  fontSize: 12,
                  border: "1px solid #cbd5e1",
                  borderRadius: 6,
                  background: "#ffffff"
                }}
              >
                <option value="ALL">All Statuses</option>
                <option value="SUCCESS">Success</option>
                <option value="FAILED">Failed</option>
              </select>
            </div>

            {/* Filter 5: From Date */}
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: "#475569", marginBottom: 4 }}>
                From Date
              </label>
              <input
                id="activity-date-from"
                type="date"
                value={auditDateFrom}
                onChange={(e) => {
                  const val = e.target.value;
                  setAuditDateFrom(val);
                  setAuditPage(1);
                  fetchAuditLogs({ page: 1, dateFrom: val });
                }}
                style={{
                  width: "100%",
                  padding: "6px 10px",
                  fontSize: 12,
                  border: "1px solid #cbd5e1",
                  borderRadius: 6,
                  background: "#ffffff",
                  boxSizing: "border-box"
                }}
              />
            </div>

            {/* Filter 6: To Date */}
            <div>
              <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: "#475569", marginBottom: 4 }}>
                To Date
              </label>
              <input
                id="activity-date-to"
                type="date"
                value={auditDateTo}
                onChange={(e) => {
                  const val = e.target.value;
                  setAuditDateTo(val);
                  setAuditPage(1);
                  fetchAuditLogs({ page: 1, dateTo: val });
                }}
                style={{
                  width: "100%",
                  padding: "6px 10px",
                  fontSize: 12,
                  border: "1px solid #cbd5e1",
                  borderRadius: 6,
                  background: "#ffffff",
                  boxSizing: "border-box"
                }}
              />
            </div>
          </div>

          {auditLogs.length === 0 ? (
            <div style={{ padding: "48px 20px", textAlign: "center", color: "#64748b" }}>
              <History size={36} style={{ margin: "0 auto 8px auto", color: "#94a3b8" }} />
              <div>No matching activity records found.</div>
            </div>
          ) : (
            <div className="admin-table-scroll-container">
              <table style={{ width: "100%", minWidth: 720, borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#f8fafc", textAlign: "left", color: "#475569", borderBottom: "1px solid #e2e8f0" }}>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>Time</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>User (Name & ID)</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>Action</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>File Name</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>Status</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>IP</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.map(log => {
                    const actType = log.activity_type || log.action || "EVENT";
                    const badge = getActionBadgeColor(actType);
                    const statusVal = String(log.status || "SUCCESS").toUpperCase();
                    const isFailed = statusVal === "FAILED";
                    const plainAction = getPlainAction(log);
                    const userName = log.user_name || (log.user_id ? `User #${log.user_id}` : "System");

                    return (
                      <tr key={log.id} style={{ borderBottom: "1px solid #f1f5f9", background: isFailed ? "#fffafa" : "#ffffff" }}>
                        {/* 1. Time */}
                        <td style={{ padding: "12px 16px", color: "#64748b", whiteSpace: "nowrap", fontSize: 12 }}>
                          {formatDate(log.created_at || log.time)}
                        </td>

                        {/* 2. User (Name & ID only - NO email) */}
                        <td style={{ padding: "12px 16px", color: "#1e293b" }}>
                          <div style={{ fontWeight: 600, color: "#0f172a" }}>
                            {userName}
                          </div>
                          <div style={{ fontSize: 11, color: "#64748b" }}>
                            {log.user_id ? `User ID #${log.user_id}` : "System / Automated"}
                          </div>
                        </td>

                        {/* 3. Action (Plain Words) */}
                        <td style={{ padding: "12px 16px" }}>
                          <span style={{
                            background: badge.bg,
                            color: badge.color,
                            border: `1px solid ${badge.border}`,
                            padding: "3px 8px",
                            borderRadius: 6,
                            fontSize: 11,
                            fontWeight: 700,
                            whiteSpace: "nowrap"
                          }}>
                            {plainAction}
                          </span>
                          {log.details && (
                            <div style={{ fontSize: 11, color: "#64748b", marginTop: 4, maxWidth: 320, wordBreak: "break-word" }}>
                              {log.details}
                            </div>
                          )}
                        </td>

                        {/* 4. File Name */}
                        <td style={{ padding: "12px 16px", color: "#1e293b" }}>
                          {log.file_name && log.file_name !== "—" ? (
                            <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontWeight: 500 }}>
                              <FileSpreadsheet size={14} style={{ color: "#2563eb", flexShrink: 0 }} />
                              <span>{log.file_name}</span>
                            </span>
                          ) : (
                            <span style={{ color: "#94a3b8" }}>—</span>
                          )}
                        </td>

                        {/* 5. Status */}
                        <td style={{ padding: "12px 16px", whiteSpace: "nowrap" }}>
                          <span style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: 4,
                            padding: "3px 8px",
                            borderRadius: 999,
                            fontSize: 11,
                            fontWeight: 700,
                            background: isFailed ? "#fee2e2" : "#dcfce7",
                            color: isFailed ? "#b91c1c" : "#15803d"
                          }}>
                            {isFailed ? <X size={12} /> : <Check size={12} />}
                            {isFailed ? "Failed" : "Success"}
                          </span>
                        </td>

                        {/* 6. IP */}
                        <td style={{ padding: "12px 16px", color: "#475569", fontSize: 12, whiteSpace: "nowrap" }}>
                          {log.ip_address && log.ip_address !== "—" ? (
                            <code>{log.ip_address}</code>
                          ) : (
                            <span style={{ color: "#94a3b8" }}>—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Footer */}
          <div className="admin-pagination-footer">
            <div>
              Showing{" "}
              <strong>
                {auditTotal === 0 ? 0 : (auditPage - 1) * auditPageSize + 1}
              </strong>
              {" – "}
              <strong>
                {Math.min(auditPage * auditPageSize, auditTotal)}
              </strong>{" "}
              of <strong>{auditTotal}</strong> activity records
            </div>

            <div className="admin-pagination-controls" style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <label style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <span>Page Size:</span>
                <select
                  value={auditPageSize}
                  onChange={(e) => {
                    const newSize = Number(e.target.value);
                    setAuditPageSize(newSize);
                    setAuditPage(1);
                    fetchAuditLogs({ page: 1, pageSize: newSize });
                  }}
                  style={{
                    padding: "4px 8px",
                    fontSize: 12,
                    border: "1px solid #cbd5e1",
                    borderRadius: 6,
                    background: "#ffffff"
                  }}
                >
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={200}>200</option>
                  <option value={500}>500</option>
                  <option value={1000}>All (1000)</option>
                </select>
              </label>

              <span>
                Page <strong>{auditPage}</strong> of <strong>{auditTotalPages}</strong>
              </span>

              <button
                id="activity-prev-page"
                disabled={auditPage <= 1}
                onClick={() => {
                  const prev = Math.max(1, auditPage - 1);
                  setAuditPage(prev);
                  fetchAuditLogs({ page: prev });
                }}
                style={{
                  padding: "5px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  background: auditPage <= 1 ? "#f1f5f9" : "#ffffff",
                  color: auditPage <= 1 ? "#94a3b8" : "#1e293b",
                  fontWeight: 600,
                  cursor: auditPage <= 1 ? "not-allowed" : "pointer"
                }}
              >
                Previous
              </button>

              <button
                id="activity-next-page"
                disabled={auditPage >= auditTotalPages}
                onClick={() => {
                  const next = Math.min(auditTotalPages, auditPage + 1);
                  setAuditPage(next);
                  fetchAuditLogs({ page: next });
                }}
                style={{
                  padding: "5px 12px",
                  borderRadius: 6,
                  border: "1px solid #cbd5e1",
                  background: auditPage >= auditTotalPages ? "#f1f5f9" : "#ffffff",
                  color: auditPage >= auditTotalPages ? "#94a3b8" : "#1e293b",
                  fontWeight: 600,
                  cursor: auditPage >= auditTotalPages ? "not-allowed" : "pointer"
                }}
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          PANEL 3: ANALYSES
          ========================================================================= */}
      {activeTab === "analyses" && (
        <div
          id="admin-analyses-panel"
          style={{
            background: "#ffffff",
            borderRadius: 12,
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
            overflow: "hidden"
          }}
        >
          <div className="admin-panel-header">
            <div>
              <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1e293b", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                <FolderArchive size={18} color="#4f46e5" />
                All Analyses in ASSETRA ({filteredAnalyses.length})
              </h2>
              <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0 0" }}>
                Inspect and analyze valuation reports uploaded by any user across the organization
              </p>
            </div>

            <div className="admin-panel-search">
              <Search size={15} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search company, file, or user..."
                style={{
                  width: "100%",
                  padding: "8px 12px 8px 34px",
                  fontSize: 13,
                  border: "1px solid #cbd5e1",
                  borderRadius: 6,
                  outline: "none",
                  boxSizing: "border-box"
                }}
              />
            </div>
          </div>

          {filteredAnalyses.length === 0 ? (
            <div style={{ padding: "48px 20px", textAlign: "center", color: "#64748b" }}>
              <FolderArchive size={40} style={{ margin: "0 auto 12px auto", color: "#94a3b8" }} />
              <div style={{ fontSize: 15, fontWeight: 600, color: "#334155" }}>
                {searchQuery ? "No analyses match your search" : "No analyses in the system"}
              </div>
              <div style={{ fontSize: 13, marginTop: 4 }}>
                {searchQuery ? "Try searching by another term or clear the search query." : "When users upload asset registers to ASSETRA, they will appear here."}
              </div>
            </div>
          ) : (
            <div className="admin-table-scroll-container">
              <table style={{ width: "100%", minWidth: 880, borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#f8fafc", textAlign: "left", color: "#475569", borderBottom: "1px solid #e2e8f0" }}>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>Company & Industry</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>Uploaded File</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>Uploaded By</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>Rows</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>Acquisition Cost</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>Replacement Value</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>Date</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600, textAlign: "right" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredAnalyses.map(a => (
                    <tr key={a.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "14px 16px" }}>
                        <div style={{ fontWeight: 600, color: "#1e293b", fontSize: 14 }}>
                          {a.company_name}
                        </div>
                        <div style={{ fontSize: 12, color: "#64748b", marginTop: 2 }}>
                          {a.industry || "General Index"}
                        </div>
                      </td>
                      <td style={{ padding: "14px 16px", color: "#475569" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                          <FileSpreadsheet size={15} color="#059669" />
                          <span style={{ fontWeight: 500 }}>{a.original_filename}</span>
                        </div>
                      </td>
                      <td style={{ padding: "14px 16px" }}>
                        <div style={{ color: "#1e293b", fontWeight: 500 }}>
                          {getUserDisplay(a.user_id)}
                        </div>
                      </td>
                      <td style={{ padding: "14px 16px", color: "#475569", whiteSpace: "nowrap" }}>
                        <span style={{ fontWeight: 600, color: "#1e293b" }}>{a.rows_calculated?.toLocaleString() || a.rows_total?.toLocaleString() || 0}</span>
                        <span style={{ color: "#94a3b8", fontSize: 11 }}> / {a.rows_total?.toLocaleString() || 0}</span>
                      </td>
                      <td style={{ padding: "14px 16px", color: "#334155", fontWeight: 600, whiteSpace: "nowrap" }}>
                        {fmtCurrency(a.total_acquisition)}
                      </td>
                      <td style={{ padding: "14px 16px", color: "#059669", fontWeight: 700, whiteSpace: "nowrap" }}>
                        {fmtCurrency(a.total_replacement)}
                      </td>
                      <td style={{ padding: "14px 16px", color: "#64748b", whiteSpace: "nowrap" }}>
                        {formatDate(a.created_at)}
                      </td>
                      <td style={{ padding: "14px 16px", textAlign: "right", whiteSpace: "nowrap" }}>
                        <div style={{ display: "inline-flex", gap: 8, alignItems: "center" }}>
                          <button
                            id={`analyze-in-app-${a.id}`}
                            onClick={() => onOpenAnalysis(a.id)}
                            title="Open full interactive calculation dashboard in Step 4"
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 6,
                              background: "#4f46e5",
                              color: "#ffffff",
                              border: "none",
                              borderRadius: 6,
                              padding: "6px 12px",
                              fontSize: 12,
                              fontWeight: 600,
                              cursor: "pointer",
                              boxShadow: "0 1px 2px rgba(79, 70, 229, 0.2)"
                            }}
                          >
                            <Play size={13} fill="#ffffff" />
                            <span>Analyze in Calculator</span>
                          </button>
                          <button
                            id={`download-analysis-${a.id}`}
                            onClick={(e) => handleDownloadAnalysis(a.id, a.company_name, e)}
                            title="Download calculated Excel report"
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: 6,
                              background: "#ffffff",
                              color: "#2563eb",
                              border: "1px solid #cbd5e1",
                              borderRadius: 6,
                              padding: "6px 10px",
                              fontSize: 12,
                              fontWeight: 500,
                              cursor: "pointer"
                            }}
                          >
                            <Download size={13} />
                            <span>Excel</span>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          PANEL 4: SETTINGS (General & Advanced (Admin Only))
          ========================================================================= */}
      {activeTab === "settings" && (
        <div id="admin-settings-panel" style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {/* Settings Sub-Navigation Tabs */}
          <div className="admin-settings-subtabs">
            <button
              id="settings-subtab-general"
              className="admin-subtab-btn"
              onClick={() => setSettingsSubTab("general")}
              style={{
                padding: "8px 18px",
                borderRadius: 8,
                border: "none",
                background: settingsSubTab === "general" ? "#4f46e5" : "#f1f5f9",
                color: settingsSubTab === "general" ? "#ffffff" : "#475569",
                fontWeight: 600,
                fontSize: 13,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 6
              }}
            >
              <Settings size={15} />
              General Settings
            </button>
            <button
              id="settings-subtab-advanced"
              className="admin-subtab-btn"
              onClick={() => setSettingsSubTab("advanced")}
              style={{
                padding: "8px 18px",
                borderRadius: 8,
                border: "none",
                background: settingsSubTab === "advanced" ? "#4f46e5" : "#f1f5f9",
                color: settingsSubTab === "advanced" ? "#ffffff" : "#475569",
                fontWeight: 600,
                fontSize: 13,
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: 6
              }}
            >
              <Sliders size={15} />
              Advanced (Admin Only)
              {pendingOrConflictingAliases.length > 0 && (
                <span style={{
                  background: settingsSubTab === "advanced" ? "#dc2626" : "#ef4444",
                  color: "#ffffff",
                  fontSize: 10,
                  fontWeight: 700,
                  padding: "1px 6px",
                  borderRadius: 10
                }}>
                  {pendingOrConflictingAliases.length}
                </span>
              )}
            </button>
          </div>

          {settingsSubTab === "general" && (
            <>
          {/* Settings Section 1: Dynamic Admin Role Management */}
          <div style={{
            background: "#ffffff",
            borderRadius: 12,
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
            overflow: "hidden"
          }}>
            <div className="admin-panel-header">
              <div>
                <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1e293b", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                  <ShieldCheck size={18} color="#1e3e62" />
                  Administrator Role Management ({adminsList.length})
                </h2>
                <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0 0" }}>
                  All administrators have equal dashboard permissions and full data visibility, including promoting and managing administrators.
                </p>
              </div>

              <button
                id="add-admin-btn"
                onClick={() => {
                  setNewAdminEmail("");
                  setAddAdminError("");
                  setAddAdminSuccess("");
                  setShowAddAdminModal(true);
                }}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  background: "linear-gradient(135deg, #1e3e62 0%, #0b192c 100%)",
                  color: "#ffffff",
                  border: "none",
                  borderRadius: 8,
                  padding: "9px 16px",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: "pointer",
                  boxShadow: "0 2px 6px rgba(30, 62, 98, 0.25)",
                  flexShrink: 0
                }}
              >
                <UserPlus size={16} />
                <span>Add Admin</span>
              </button>
            </div>

            <div className="admin-table-scroll-container">
              <table style={{ width: "100%", minWidth: 760, borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#f8fafc", textAlign: "left", color: "#475569", borderBottom: "1px solid #e2e8f0" }}>
                    <th style={{ padding: "12px 20px", fontWeight: 600 }}>Administrator</th>
                    <th style={{ padding: "12px 20px", fontWeight: 600 }}>Email Address</th>
                    <th style={{ padding: "12px 20px", fontWeight: 600 }}>Role / Authority</th>
                    <th style={{ padding: "12px 20px", fontWeight: 600 }}>Status</th>
                    <th style={{ padding: "12px 20px", fontWeight: 600 }}>Member Since</th>
                    <th style={{ padding: "12px 20px", fontWeight: 600 }}>Last Login</th>
                    <th style={{ padding: "12px 20px", fontWeight: 600, textAlign: "right" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {loadingAdmins ? (
                    <tr>
                      <td colSpan={7} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>
                        Loading administrators...
                      </td>
                    </tr>
                  ) : adminsList.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ padding: 24, textAlign: "center", color: "#64748b" }}>
                        No administrators found.
                      </td>
                    </tr>
                  ) : (
                    adminsList.map((admin) => {
                      const isPrimary = admin.is_primary_admin;
                      return (
                        <tr key={admin.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                          <td style={{ padding: "12px 20px", fontWeight: 600, color: "#1e293b" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                              <div style={{
                                width: 30,
                                height: 30,
                                borderRadius: "50%",
                                background: isPrimary ? "#fef3c7" : "#e0e7ff",
                                color: isPrimary ? "#b45309" : "#4338ca",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                fontWeight: 700,
                                fontSize: 12
                              }}>
                                {isPrimary ? <Crown size={15} /> : <ShieldCheck size={15} />}
                              </div>
                              <div>
                                <div>{admin.name}</div>
                                <div style={{ fontSize: 11, color: "#94a3b8", fontWeight: 400 }}>User ID #{admin.id}</div>
                              </div>
                            </div>
                          </td>
                          <td style={{ padding: "12px 20px", color: "#475569" }}>
                            <code>{admin.email}</code>
                          </td>
                          <td style={{ padding: "12px 20px" }}>
                            {isPrimary ? (
                              <span style={{
                                background: "#fef3c7",
                                color: "#b45309",
                                border: "1px solid #fde68a",
                                padding: "3px 10px",
                                borderRadius: 6,
                                fontSize: 11,
                                fontWeight: 700,
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 4
                              }}>
                                <Crown size={12} /> Primary Admin
                              </span>
                            ) : (
                              <span style={{
                                background: "#e0e7ff",
                                color: "#4338ca",
                                border: "1px solid #c7d2fe",
                                padding: "3px 10px",
                                borderRadius: 6,
                                fontSize: 11,
                                fontWeight: 700,
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 4
                              }}>
                                <ShieldCheck size={12} /> Administrator
                              </span>
                            )}
                          </td>
                          <td style={{ padding: "12px 20px" }}>
                            <span style={{
                              background: admin.status === "active" ? "#dcfce7" : "#fee2e2",
                              color: admin.status === "active" ? "#15803d" : "#b91c1c",
                              padding: "2px 8px",
                              borderRadius: 6,
                              fontSize: 11,
                              fontWeight: 600,
                              textTransform: "uppercase"
                            }}>
                              {admin.status || (admin.is_active ? "active" : "disabled")}
                            </span>
                          </td>
                          <td style={{ padding: "12px 20px", color: "#64748b", whiteSpace: "nowrap" }}>
                            {formatDate(admin.created_at)}
                          </td>
                          <td style={{ padding: "12px 20px", color: admin.last_login_at ? "#0f172a" : "#94a3b8", fontWeight: admin.last_login_at ? 600 : 400, whiteSpace: "nowrap" }}>
                            {admin.last_login_at ? formatDate(admin.last_login_at) : <span style={{ fontStyle: "italic" }}>Never logged in</span>}
                          </td>
                          <td style={{ padding: "12px 20px", textAlign: "right" }}>
                            {adminsList.length <= 1 ? (
                              <span style={{ fontSize: 12, color: "#94a3b8", fontStyle: "italic" }} title="The system must retain at least one administrator">
                                Only Admin
                              </span>
                            ) : (
                              <button
                                onClick={() => setDemoteConfirmUser(admin)}
                                disabled={demoteLoading}
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: 6,
                                  background: "#fee2e2",
                                  color: "#b91c1c",
                                  border: "1px solid #fecaca",
                                  borderRadius: 6,
                                  padding: "5px 10px",
                                  fontSize: 12,
                                  fontWeight: 600,
                                  cursor: "pointer"
                                }}
                              >
                                <UserMinus size={13} />
                                <span>Remove Admin</span>
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Settings Section 2: System Configuration Card */}
          <div style={{
            background: "#ffffff",
            borderRadius: 12,
            border: "1px solid #e2e8f0",
            padding: "20px 24px",
            boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)"
          }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1e293b", margin: "0 0 4px 0", display: "flex", alignItems: "center", gap: 8 }}>
              <Settings size={18} color="#4f46e5" />
              Administrative Settings & System Policies
            </h2>
            <p style={{ fontSize: 13, color: "#64748b", margin: "0 0 16px 0" }}>
              Core system behavior, approval gates, and authorization policies
            </p>

            <div className="admin-config-grid">
              <div style={{ padding: "14px 16px", background: "#f8fafc", borderRadius: 8, border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: 12, color: "#64748b", fontWeight: 600 }}>ADMIN APPROVAL REQUIREMENT</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", marginTop: 4 }}>
                  {adminStats?.require_admin_approval ? "Enabled (New users await approval)" : "Disabled (Direct user registration)"}
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
                  Controlled via <code>REQUIRE_ADMIN_APPROVAL</code> in backend config
                </div>
              </div>

              <div style={{ padding: "14px 16px", background: "#f8fafc", borderRadius: 8, border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: 12, color: "#64748b", fontWeight: 600 }}>PRIMARY ADMINISTRATOR</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#0f172a", marginTop: 4 }}>
                  {adminStats?.primary_admin_email || "communication.ins@shareindia.co.in"}
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
                  Permanent authority with permissions to manage administrator roles
                </div>
              </div>

              <div style={{ padding: "14px 16px", background: "#f8fafc", borderRadius: 8, border: "1px solid #e2e8f0" }}>
                <div style={{ fontSize: 12, color: "#64748b", fontWeight: 600 }}>DYNAMIC ROLE RBAC</div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#16a34a", marginTop: 4 }}>
                  Active ({adminsList.length || 1} Total Admins)
                </div>
                <div style={{ fontSize: 11, color: "#94a3b8", marginTop: 2 }}>
                  Equal administrative dashboard permissions for all promoted admins
                </div>
              </div>
            </div>
          </div>
          </>
          )}

          {/* Settings Section 2: Shared Column Aliases - Advanced (Admin Only) */}
          {settingsSubTab === "advanced" && (
          <div style={{
            background: "#ffffff",
            borderRadius: 12,
            border: "1px solid #e2e8f0",
            boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
            overflow: "hidden"
          }}>
            <div className="admin-panel-header">
              <div>
                <h3 style={{ fontSize: 16, fontWeight: 700, color: "#1e293b", margin: 0, display: "flex", alignItems: "center", gap: 8 }}>
                  <FileSpreadsheet size={18} color="#4f46e5" />
                  ASSETRA Column Aliases ({filteredAliases.length})
                </h3>
                <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0 0" }}>
                  Learned column aliases mapped to canonical valuation fields. Content validation summaries are cached globally (raw user sample values are never stored).
                </p>
              </div>

              <div className="admin-alias-filter" style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                <select
                  value={aliasStatusFilter}
                  onChange={(e) => setAliasStatusFilter(e.target.value)}
                  style={{
                    padding: "6px 12px",
                    fontSize: 12,
                    border: "1px solid #cbd5e1",
                    borderRadius: 6,
                    background: "#ffffff",
                    fontWeight: 500
                  }}
                >
                  <option value="all">All Statuses ({columnAliases.length})</option>
                  <option value="pending">Pending ({columnAliases.filter(a => a.status === "pending").length})</option>
                  <option value="conflict">Conflicts ({pendingOrConflictingAliases.filter(a => a.status === "conflict" || ((a.normalized_header || "").trim().toLowerCase() && conflictHeaderSet.has((a.normalized_header || "").trim().toLowerCase()))).length})</option>
                  <option value="approved">Approved ({columnAliases.filter(a => a.status === "approved").length})</option>
                  <option value="rejected">Rejected ({columnAliases.filter(a => a.status === "rejected").length})</option>
                </select>
              </div>
            </div>

            {filteredAliases.length === 0 ? (
              <div style={{ padding: 36, textAlign: "center", color: "#64748b", fontSize: 14 }}>
                No custom column aliases found matching filter.
              </div>
            ) : (
              <div className="admin-table-scroll-container">
                <table style={{ width: "100%", minWidth: 820, borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: "#f8fafc", textAlign: "left", color: "#475569", borderBottom: "1px solid #e2e8f0" }}>
                      <th style={{ padding: "12px 16px", fontWeight: 600 }}>Original Header</th>
                      <th style={{ padding: "12px 16px", fontWeight: 600 }}>Canonical Field</th>
                      <th style={{ padding: "12px 16px", fontWeight: 600 }}>Validation Summary</th>
                      <th style={{ padding: "12px 16px", fontWeight: 600 }}>Content Validated</th>
                      <th style={{ padding: "12px 16px", fontWeight: 600 }}>Status</th>
                      <th style={{ padding: "12px 16px", fontWeight: 600 }}>Submitted By</th>
                      <th style={{ padding: "12px 16px", fontWeight: 600 }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAliases.map((alias) => {
                      const norm = (alias.normalized_header || "").trim().toLowerCase();
                      const isConflict = alias.status === "conflict" || (norm && conflictHeaderSet.has(norm));
                      return (
                      <tr key={alias.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "12px 16px", fontWeight: 700, color: "#0f172a" }}>
                          {alias.original_header}
                          <div style={{ fontSize: 11, color: "#64748b", fontWeight: 400 }}>
                            normalized: <code>{alias.normalized_header}</code>
                          </div>
                        </td>
                        <td style={{ padding: "12px 16px", fontWeight: 600, color: "#1d4ed8" }}>
                          <code>{alias.canonical_field}</code>
                        </td>
                        <td style={{ padding: "12px 16px" }}>
                          {alias.validation_summary ? (
                            <span
                              style={{
                                display: "inline-block",
                                background: "#f8fafc",
                                border: "1px solid #e2e8f0",
                                borderRadius: 6,
                                padding: "3px 8px",
                                fontSize: 11,
                                fontFamily: "monospace",
                                color: "#334155"
                              }}
                            >
                              {alias.validation_summary}
                            </span>
                          ) : (
                            <span style={{ color: "#94a3b8", fontSize: 12 }}>—</span>
                          )}
                        </td>
                        <td style={{ padding: "12px 16px" }}>
                          <span
                            style={{
                              padding: "2px 8px",
                              borderRadius: 6,
                              fontSize: 11,
                              fontWeight: 700,
                              background: alias.validation_passed ? "#dcfce7" : "#fee2e2",
                              color: alias.validation_passed ? "#166534" : "#991b1b"
                            }}
                          >
                            {alias.validation_passed ? "Passed" : "Unvalidated"}
                          </span>
                        </td>
                        <td style={{ padding: "12px 16px" }}>
                          <div style={{ display: "flex", gap: 4, alignItems: "center", flexWrap: "wrap" }}>
                            <span
                              style={{
                                padding: "2px 8px",
                                borderRadius: 6,
                                fontSize: 11,
                                fontWeight: 700,
                                textTransform: "uppercase",
                                background:
                                  alias.status === "approved"
                                    ? "#dcfce7"
                                    : alias.status === "pending"
                                    ? "#fef3c7"
                                    : "#fee2e2",
                                color:
                                  alias.status === "approved"
                                    ? "#15803d"
                                    : alias.status === "pending"
                                    ? "#b45309"
                                    : "#b91c1c"
                              }}
                            >
                              {alias.status}
                            </span>
                            {isConflict && (
                              <span
                                style={{
                                  padding: "2px 6px",
                                  borderRadius: 6,
                                  fontSize: 10,
                                  fontWeight: 800,
                                  background: "#fee2e2",
                                  color: "#b91c1c",
                                  border: "1px solid #fca5a5"
                                }}
                              >
                                CONFLICT
                              </span>
                            )}
                          </div>
                        </td>
                        {/* Submitted By (Name and ID only - NO email) */}
                        <td style={{ padding: "12px 16px", fontSize: 12, color: "#475569" }}>
                          {alias.submitted_by_display || alias.submitted_by_name || (alias.submitted_by ? `User #${alias.submitted_by}` : "System")}
                        </td>
                        <td style={{ padding: "12px 16px" }}>
                          <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                            {alias.status !== "approved" && (
                              <button
                                onClick={() => handleApproveAlias(alias.id)}
                                disabled={Boolean(actionLoading[`alias_${alias.id}`])}
                                style={{
                                  background: "#16a34a",
                                  color: "#ffffff",
                                  border: "none",
                                  borderRadius: 6,
                                  padding: "5px 10px",
                                  fontSize: 12,
                                  fontWeight: 600,
                                  cursor: "pointer"
                                }}
                              >
                                Approve
                              </button>
                            )}
                            {alias.status !== "rejected" && (
                              <button
                                onClick={() => handleRejectAlias(alias.id)}
                                disabled={Boolean(actionLoading[`alias_${alias.id}`])}
                                style={{
                                  background: "#ef4444",
                                  color: "#ffffff",
                                  border: "none",
                                  borderRadius: 6,
                                  padding: "5px 10px",
                                  fontSize: 12,
                                  fontWeight: 600,
                                  cursor: "pointer"
                                }}
                              >
                                Reject
                              </button>
                            )}
                            <button
                              onClick={() => handleRemoveAlias(alias.id)}
                              disabled={Boolean(actionLoading[`alias_${alias.id}`])}
                              style={{
                                background: "#ffffff",
                                color: "#dc2626",
                                border: "1px solid #fecaca",
                                borderRadius: 6,
                                padding: "5px 10px",
                                fontSize: 12,
                                fontWeight: 600,
                                cursor: "pointer",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 4
                              }}
                              title="Permanently remove column alias"
                            >
                              <Trash2 size={12} />
                              <span>Remove</span>
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          )}
        </div>
      )}

      {/* =========================================================================
          PANEL 5: PENDING REQUESTS (Conditionally shown if approval enabled)
          ========================================================================= */}
      {showPendingTab && activeTab === "pending" && (
        <div style={{
          background: "#ffffff",
          borderRadius: 12,
          border: "1px solid #e2e8f0",
          boxShadow: "0 1px 3px rgba(0, 0, 0, 0.05)",
          overflow: "hidden"
        }}>
          <div className="admin-panel-header">
            <h2 style={{ fontSize: 16, fontWeight: 700, color: "#1e293b", margin: 0 }}>
              Account Creation Requests ({pendingRequests.length})
            </h2>
            <p style={{ fontSize: 13, color: "#64748b", margin: "4px 0 0 0" }}>
              Users who submitted a sign-up request awaiting administrator approval
            </p>
          </div>

          {pendingRequests.length === 0 ? (
            <div style={{ padding: "48px 20px", textAlign: "center", color: "#64748b" }}>
              <UserCheck size={40} style={{ margin: "0 auto 12px auto", color: "#94a3b8" }} />
              <div style={{ fontSize: 15, fontWeight: 600, color: "#334155" }}>
                No pending requests
              </div>
              <div style={{ fontSize: 13, marginTop: 4 }}>
                All user account requests have been reviewed and processed.
              </div>
            </div>
          ) : (
            <div className="admin-table-scroll-container">
              <table style={{ width: "100%", minWidth: 650, borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#f8fafc", textAlign: "left", color: "#475569", borderBottom: "1px solid #e2e8f0" }}>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>Name</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>Email address</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>Requested On</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600 }}>Status</th>
                    <th style={{ padding: "12px 16px", fontWeight: 600, textAlign: "right" }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingRequests.map(user => {
                    const isBusy = actionLoading[user.id];
                    return (
                      <tr key={user.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                        <td style={{ padding: "14px 16px", fontWeight: 600, color: "#1e293b" }}>
                          {user.name}
                        </td>
                        <td style={{ padding: "14px 16px", color: "#475569" }}>
                          <code>{user.email}</code>
                        </td>
                        <td style={{ padding: "14px 16px", color: "#64748b" }}>
                          {formatDate(user.created_at)}
                        </td>
                        <td style={{ padding: "14px 16px" }}>
                          <span style={{
                            background: "#fef3c7",
                            color: "#b45309",
                            border: "1px solid #fde68a",
                            padding: "3px 8px",
                            borderRadius: 6,
                            fontSize: 11,
                            fontWeight: 600,
                            textTransform: "uppercase"
                          }}>
                            {user.status}
                          </span>
                        </td>
                        <td style={{ padding: "14px 16px", textAlign: "right" }}>
                          <div style={{ display: "inline-flex", gap: 8 }}>
                            <button
                              id={`approve-user-${user.id}`}
                              disabled={!!isBusy}
                              onClick={() => handleApprove(user.id, user.email)}
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 6,
                                background: "#16a34a",
                                color: "#ffffff",
                                border: "none",
                                borderRadius: 6,
                                padding: "6px 14px",
                                fontSize: 12,
                                fontWeight: 600,
                                cursor: isBusy ? "not-allowed" : "pointer"
                              }}
                            >
                              <Check size={14} />
                              <span>{isBusy === "approving" ? "Approving..." : "Approve"}</span>
                            </button>
                            <button
                              id={`reject-user-${user.id}`}
                              disabled={!!isBusy}
                              onClick={() => handleReject(user.id, user.email)}
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: 6,
                                background: "#ef4444",
                                color: "#ffffff",
                                border: "none",
                                borderRadius: 6,
                                padding: "6px 12px",
                                fontSize: 12,
                                fontWeight: 600,
                                cursor: isBusy ? "not-allowed" : "pointer"
                              }}
                            >
                              <X size={14} />
                              <span>{isBusy === "rejecting" ? "Rejecting..." : "Reject"}</span>
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* =========================================================================
          MODAL: ADD / PROMOTE ADMIN
          ========================================================================= */}
      {showAddAdminModal && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(15, 23, 42, 0.6)",
          backdropFilter: "blur(4px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 9999,
          padding: 16
        }}>
          <div className="admin-modal-card" style={{
            background: "#ffffff",
            borderRadius: 16,
            width: "100%",
            maxWidth: 480,
            maxHeight: "90vh",
            overflowY: "auto",
            boxSizing: "border-box",
            padding: 24,
            boxShadow: "0 20px 40px rgba(0, 0, 0, 0.25)",
            border: "1px solid #e2e8f0"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 16 }}>
              <div>
                <h3 style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", margin: "0 0 4px" }}>
                  Promote User to Administrator
                </h3>
                <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
                  Enter the registered email of the user you want to grant full administrator privileges.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowAddAdminModal(false)}
                style={{ background: "none", border: "none", color: "#94a3b8", cursor: "pointer", padding: 4 }}
              >
                <X size={20} />
              </button>
            </div>

            <div style={{
              background: "#eff6ff",
              border: "1px solid #bfdbfe",
              borderRadius: 8,
              padding: "10px 14px",
              marginBottom: 16,
              fontSize: 12,
              color: "#1e40af",
              lineHeight: 1.5
            }}>
              <strong>Equal Permissions Policy:</strong> Promoted administrators have complete access to all registered users, activity timelines, uploaded files, analyses, and column aliases.
            </div>

            {addAdminError && (
              <div style={{
                background: "#fef2f2",
                border: "1px solid #fecaca",
                borderRadius: 8,
                padding: "10px 14px",
                marginBottom: 16,
                display: "flex",
                alignItems: "center",
                gap: 8,
                color: "#991b1b",
                fontSize: 13
              }}>
                <AlertCircle size={16} style={{ flexShrink: 0 }} />
                <span>{addAdminError}</span>
              </div>
            )}

            {addAdminSuccess && (
              <div style={{
                background: "#ecfdf5",
                border: "1px solid #a7f3d0",
                borderRadius: 8,
                padding: "10px 14px",
                marginBottom: 16,
                display: "flex",
                alignItems: "center",
                gap: 8,
                color: "#065f46",
                fontSize: 13
              }}>
                <CheckCircle2 size={16} style={{ flexShrink: 0 }} />
                <span>{addAdminSuccess}</span>
              </div>
            )}

            <form onSubmit={handlePromoteAdmin}>
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6 }}>
                  Registered User Email
                </label>
                <input
                  id="promote-admin-email-input"
                  type="email"
                  value={newAdminEmail}
                  onChange={(e) => setNewAdminEmail(e.target.value)}
                  placeholder="user@example.com"
                  autoFocus
                  required
                  disabled={addAdminLoading}
                  style={{
                    width: "100%",
                    height: 42,
                    padding: "0 12px",
                    border: "1px solid #cbd5e1",
                    borderRadius: 8,
                    fontSize: 14,
                    outline: "none",
                    boxSizing: "border-box"
                  }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
                <button
                  type="button"
                  disabled={addAdminLoading}
                  onClick={() => setShowAddAdminModal(false)}
                  style={{
                    padding: "9px 16px",
                    borderRadius: 8,
                    border: "1px solid #cbd5e1",
                    background: "#ffffff",
                    color: "#475569",
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: addAdminLoading ? "not-allowed" : "pointer"
                  }}
                >
                  Cancel
                </button>
                <button
                  id="confirm-promote-admin-btn"
                  type="submit"
                  disabled={addAdminLoading}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "9px 18px",
                    borderRadius: 8,
                    border: "none",
                    background: "linear-gradient(135deg, #1e3e62 0%, #0b192c 100%)",
                    color: "#ffffff",
                    fontSize: 13,
                    fontWeight: 600,
                    cursor: addAdminLoading ? "not-allowed" : "pointer"
                  }}
                >
                  <UserPlus size={15} />
                  <span>{addAdminLoading ? "Promoting..." : "Promote to Admin"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL: CONFIRM REMOVE ADMIN
          ========================================================================= */}
      {demoteConfirmUser && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(15, 23, 42, 0.6)",
          backdropFilter: "blur(4px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 9999,
          padding: 16
        }}>
          <div className="admin-modal-card" style={{
            background: "#ffffff",
            borderRadius: 16,
            width: "100%",
            maxWidth: 460,
            maxHeight: "90vh",
            overflowY: "auto",
            boxSizing: "border-box",
            padding: 24,
            boxShadow: "0 20px 40px rgba(0, 0, 0, 0.25)",
            border: "1px solid #e2e8f0"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
              <div style={{
                width: 40,
                height: 40,
                borderRadius: "50%",
                background: "#fee2e2",
                color: "#b91c1c",
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              }}>
                <UserMinus size={20} />
              </div>
              <h3 style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", margin: 0 }}>
                Remove Admin Privileges?
              </h3>
            </div>

            <p style={{ fontSize: 13, color: "#475569", lineHeight: 1.5, margin: "0 0 16px" }}>
              Are you sure you want to remove administrator privileges from <strong>{demoteConfirmUser.name}</strong> (<code>{demoteConfirmUser.email}</code>)?
            </p>

            <div style={{
              background: "#fffbeb",
              border: "1px solid #fde68a",
              borderRadius: 8,
              padding: "10px 12px",
              fontSize: 12,
              color: "#92400e",
              marginBottom: 20,
              lineHeight: 1.4
            }}>
              Their account will revert to <strong>Normal User</strong>, their active admin sessions will be terminated, and they will immediately lose access to the Admin Dashboard. Their normal account and previous analyses will remain intact.
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
              <button
                type="button"
                disabled={demoteLoading}
                onClick={() => setDemoteConfirmUser(null)}
                style={{
                  padding: "9px 16px",
                  borderRadius: 8,
                  border: "1px solid #cbd5e1",
                  background: "#ffffff",
                  color: "#475569",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: demoteLoading ? "not-allowed" : "pointer"
                }}
              >
                Cancel
              </button>
              <button
                id="confirm-demote-admin-btn"
                type="button"
                disabled={demoteLoading}
                onClick={() => handleDemoteAdmin(demoteConfirmUser.id)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "9px 18px",
                  borderRadius: 8,
                  border: "none",
                  background: "#dc2626",
                  color: "#ffffff",
                  fontSize: 13,
                  fontWeight: 600,
                  cursor: demoteLoading ? "not-allowed" : "pointer"
                }}
              >
                <UserMinus size={15} />
                <span>{demoteLoading ? "Removing..." : "Remove Admin"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
