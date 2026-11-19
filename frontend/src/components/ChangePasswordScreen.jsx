import React, { useState } from "react";
import { KeyRound, Lock, Eye, EyeOff, Loader2, AlertCircle, CheckCircle2, ShieldAlert, X } from "lucide-react";

export default function ChangePasswordScreen({ isForced, onPasswordChanged, onCancel, token, apiBaseUrl }) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!currentPassword || !newPassword || !confirmPassword) {
      setError("Please fill in all password fields.");
      return;
    }

    if (newPassword.length < 6) {
      setError("New password must be at least 6 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("New password and confirm password do not match.");
      return;
    }

    if (currentPassword === newPassword) {
      setError("New password cannot be the same as your current password.");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${apiBaseUrl}/auth/change-password`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword
        })
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Failed to change password.");
      }

      setSuccess(true);
      setTimeout(() => {
        onPasswordChanged();
      }, 1200);
    } catch (err) {
      setError(err.message || "An error occurred while updating your password.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div 
      onClick={(e) => {
        if (!isForced && onCancel && e.target === e.currentTarget) {
          onCancel();
        }
      }}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 10000,
        background: isForced ? "rgba(11, 25, 44, 0.95)" : "rgba(11, 25, 44, 0.65)",
        backdropFilter: "blur(6px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
        fontFamily: "'Inter', sans-serif",
        boxSizing: "border-box"
      }}
    >
      <div 
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: 440,
          maxHeight: "calc(100dvh - 32px)",
          overflowY: "auto",
          WebkitOverflowScrolling: "touch",
          background: "#ffffff",
          borderRadius: 16,
          padding: "32px 28px",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.35)",
          boxSizing: "border-box",
          position: "relative"
        }}
      >
        {/* Optional Close X Button when modal is voluntary */}
        {!isForced && onCancel && (
          <button
            type="button"
            onClick={onCancel}
            aria-label="Close modal"
            style={{
              position: "absolute",
              top: 16,
              right: 16,
              background: "transparent",
              border: "none",
              color: "#94a3b8",
              cursor: "pointer",
              padding: 4,
              borderRadius: 6,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "color 0.2s"
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = "#0f172a"}
            onMouseLeave={(e) => e.currentTarget.style.color = "#94a3b8"}
          >
            <X size={20} />
          </button>
        )}

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <div style={{
            width: 48,
            height: 48,
            borderRadius: "50%",
            background: isForced ? "#fef3c7" : "#e0f2fe",
            color: isForced ? "#d97706" : "#0284c7",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: 12
          }}>
            {isForced ? <ShieldAlert size={24} /> : <KeyRound size={24} />}
          </div>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: "#0f172a", margin: "0 0 6px 0" }}>
            {isForced ? "Password Change Required" : "Change Password"}
          </h2>
          <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
            {isForced
              ? "For your account security, you must update your temporary password before proceeding."
              : "Enter your current password and choose a new secure password."}
          </p>
        </div>

        {/* Success Alert */}
        {success && (
          <div style={{
            background: "#ecfdf5",
            border: "1px solid #a7f3d0",
            borderRadius: 8,
            padding: "12px 14px",
            marginBottom: 20,
            display: "flex",
            alignItems: "center",
            gap: 10,
            color: "#065f46",
            fontSize: 13
          }}>
            <CheckCircle2 size={18} />
            <span>Password updated successfully! Redirecting...</span>
          </div>
        )}

        {/* Error Alert */}
        {error && (
          <div style={{
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: 8,
            padding: "12px 14px",
            marginBottom: 20,
            display: "flex",
            alignItems: "flex-start",
            gap: 10,
            color: "#991b1b",
            fontSize: 13
          }}>
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Current Password */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6 }}>
              Current Password
            </label>
            <div style={{ position: "relative" }}>
              <Lock size={18} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
              <input
                type={showCurrent ? "text" : "password"}
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="••••••••"
                disabled={loading || success}
                style={{
                  width: "100%",
                  height: 44,
                  padding: "0 40px 0 38px",
                  border: "1px solid #cbd5e1",
                  borderRadius: 8,
                  fontSize: 14,
                  outline: "none",
                  boxSizing: "border-box",
                  background: "#f8fafc"
                }}
              />
              <button
                type="button"
                onClick={() => setShowCurrent(!showCurrent)}
                tabIndex={-1}
                style={{
                  position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)",
                  background: "transparent", border: "none", cursor: "pointer", color: "#94a3b8", display: "flex"
                }}
              >
                {showCurrent ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {/* New Password */}
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6 }}>
              New Password (minimum 6 characters)
            </label>
            <div style={{ position: "relative" }}>
              <Lock size={18} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
              <input
                type={showNew ? "text" : "password"}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••"
                disabled={loading || success}
                style={{
                  width: "100%",
                  height: 44,
                  padding: "0 40px 0 38px",
                  border: "1px solid #cbd5e1",
                  borderRadius: 8,
                  fontSize: 14,
                  outline: "none",
                  boxSizing: "border-box",
                  background: "#f8fafc"
                }}
              />
              <button
                type="button"
                onClick={() => setShowNew(!showNew)}
                tabIndex={-1}
                style={{
                  position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)",
                  background: "transparent", border: "none", cursor: "pointer", color: "#94a3b8", display: "flex"
                }}
              >
                {showNew ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {/* Confirm New Password */}
          <div style={{ marginBottom: 24 }}>
            <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6 }}>
              Confirm New Password
            </label>
            <div style={{ position: "relative" }}>
              <Lock size={18} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="••••••••"
                disabled={loading || success}
                style={{
                  width: "100%",
                  height: 44,
                  padding: "0 12px 0 38px",
                  border: "1px solid #cbd5e1",
                  borderRadius: 8,
                  fontSize: 14,
                  outline: "none",
                  boxSizing: "border-box",
                  background: "#f8fafc"
                }}
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", gap: 12 }}>
            {!isForced && onCancel && (
              <button
                type="button"
                onClick={onCancel}
                disabled={loading || success}
                style={{
                  flex: 1,
                  height: 44,
                  minHeight: 44,
                  background: "#f1f5f9",
                  color: "#475569",
                  border: "1px solid #cbd5e1",
                  borderRadius: 8,
                  fontSize: 14,
                  fontWeight: 600,
                  cursor: "pointer"
                }}
              >
                Cancel
              </button>
            )}
            <button
              type="submit"
              disabled={loading || success}
              style={{
                flex: 1,
                height: 44,
                minHeight: 44,
                background: loading ? "#94a3b8" : "linear-gradient(135deg, #1e3e62 0%, #0b192c 100%)",
                color: "#ffffff",
                border: "none",
                borderRadius: 8,
                fontSize: 14,
                fontWeight: 600,
                cursor: loading ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8
              }}
            >
              {loading ? (
                <>
                  <Loader2 size={18} style={{ animation: "spin 1s linear infinite" }} />
                  <span>Updating...</span>
                </>
              ) : (
                <span>Update Password</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
