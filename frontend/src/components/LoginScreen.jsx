import React, { useState, useEffect } from "react";
import { Mail, Lock, Eye, EyeOff, Loader2, AlertCircle, CheckCircle2, Shield, ArrowLeft, KeyRound } from "lucide-react";
import AssetraBrandLockup from "./AssetraBrandLockup";

export default function LoginScreen({
  onLoginSuccess,
  onNavigateSignUp,
  apiBaseUrl,
  sessionExpiredMessage,
  onClearSessionExpiredMessage
}) {
  const [mode, setMode] = useState("login"); // "login" | "forgot_request" | "forgot_reset"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Forgot / Reset Password state (6-digit OTP flow)
  const [resetEmail, setResetEmail] = useState("");
  const [resetOtp, setResetOtp] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [otpCooldown, setOtpCooldown] = useState(0);

  useEffect(() => {
    document.title = mode === "login" ? "Sign In | Assetra" : (mode === "forgot_request" ? "Forgot Password | Assetra" : "Reset Password | Assetra");
  }, [mode]);

  useEffect(() => {
    if (otpCooldown <= 0) return;
    const timer = setInterval(() => {
      setOtpCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [otpCooldown]);

  useEffect(() => {
    // Check if URL has #forgot-password
    const handleUrlState = () => {
      if (typeof window !== "undefined") {
        if (window.location.hash === "#forgot-password") {
          setMode("forgot_request");
        }
      }
    };
    handleUrlState();
    window.addEventListener("hashchange", handleUrlState);
    return () => window.removeEventListener("hashchange", handleUrlState);
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    if (onClearSessionExpiredMessage) {
      onClearSessionExpiredMessage();
    }

    if (!email.trim() || !password) {
      setError("Please enter both email and password.");
      return;
    }

    setLoading(true);
    try {
      let res;
      try {
        res = await fetch(`${apiBaseUrl}/auth/login`, {
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email: email.trim(), password, remember_me: rememberMe })
        });
      } catch (netErr) {
        throw new Error(
          `Cannot connect to backend server at ${apiBaseUrl}. Please verify uvicorn is running on port 8001.`
        );
      }

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.detail || "Invalid email or password");
      }

      onLoginSuccess(data.token, data.user, rememberMe, data.idle_timeout_minutes);
    } catch (err) {
      setError(err.message || "Failed to log in. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleForgotRequest = async (e) => {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    if (!resetEmail.trim()) {
      setError("Please enter your registered email address.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBaseUrl}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: resetEmail.trim() })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Failed to send verification code.");
      }
      setSuccessMsg(data.message || "A 6-digit verification code has been sent to your email.");
      setOtpCooldown(60);
      setMode("forgot_reset");
    } catch (err) {
      setError(err.message || "Could not process password reset request.");
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    if (otpCooldown > 0 || !resetEmail.trim()) return;
    setError("");
    setSuccessMsg("Sending new 6-digit OTP...");
    try {
      const res = await fetch(`${apiBaseUrl}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: resetEmail.trim() })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Failed to resend code.");
      }
      setSuccessMsg("A fresh 6-digit OTP has been sent to your email.");
      setOtpCooldown(60);
    } catch (err) {
      setError(err.message || "Failed to resend code.");
    }
  };

  const handleResetPasswordSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    if (!resetOtp.trim() || resetOtp.trim().length !== 6) {
      setError("Please enter the 6-digit OTP sent to your email.");
      return;
    }
    if (newPassword.length < 6) {
      setError("New password must be at least 6 characters long.");
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setError("Passwords do not match.");
      return;
    }
    setLoading(true);
    try {
      const res = await fetch(`${apiBaseUrl}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: resetEmail.trim(),
          otp: resetOtp.trim(),
          new_password: newPassword,
          confirm_password: confirmNewPassword
        })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Failed to reset password.");
      }
      setSuccessMsg(data.message || "Password reset successfully! Please sign in with your new password.");
      setEmail(resetEmail.trim());
      setPassword("");
      setResetOtp("");
      setNewPassword("");
      setConfirmNewPassword("");
      setMode("login");
    } catch (err) {
      setError(err.message || "Invalid or expired OTP.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100dvh",
      width: "100%",
      background: "linear-gradient(135deg, #0b192c 0%, #1e3e62 50%, #000000 100%)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      padding: "24px 16px",
      paddingTop: "max(24px, env(safe-area-inset-top, 0px))",
      paddingBottom: "max(24px, env(safe-area-inset-bottom, 0px))",
      fontFamily: "'Inter', sans-serif",
      boxSizing: "border-box",
      overflowY: "auto"
    }}>
      <style>{`
        .far-auth-card {
          width: 100%;
          max-width: 410px;
          min-width: 0;
          background: rgba(255, 255, 255, 0.98);
          border-radius: 16px;
          padding: 36px 28px;
          box-shadow: 0 20px 50px rgba(0, 0, 0, 0.35);
          box-sizing: border-box;
          margin: 0 auto;
        }
        @media (max-width: 767px) {
          input {
            font-size: 16px !important;
          }
        }
        @media (max-width: 480px) {
          .far-auth-card {
            max-width: 100% !important;
            padding: 24px 18px !important;
            border-radius: 14px !important;
          }
        }
        input:focus-visible, button:focus-visible {
          outline: 2px solid #2563EB !important;
          outline-offset: 2px !important;
        }
      `}</style>

      <div style={{
        width: "100%",
        maxWidth: 410,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        margin: "auto 0"
      }}>
        {/* Brand Lockup: White version on dark panel */}
        <div style={{ marginBottom: 20, textAlign: "center", width: "100%", display: "flex", justifyContent: "center" }}>
          <AssetraBrandLockup theme="dark" iconSize={46} fontSize={22} taglineSize={12} align="center" />
        </div>

        <div className="far-auth-card">
        {/* Card Header */}
        <div style={{ textAlign: "center", marginBottom: 24 }}>
          <h1 style={{
            fontSize: 22,
            fontWeight: 700,
            color: "#0b192c",
            margin: "0 0 6px 0",
            letterSpacing: "-0.02em"
          }}>
            {mode === "login"
              ? "Sign In"
              : mode === "forgot_request"
              ? "Forgot Password"
              : "Reset Your Password"}
          </h1>
          <p style={{ fontSize: 13, color: "#64748b", margin: 0 }}>
            {mode === "login"
              ? "Sign in to access Assetra & saved valuation analyses"
              : mode === "forgot_request"
              ? "Enter your registered email to receive a password reset token"
              : "Enter your reset token and choose a new password"}
          </p>
        </div>

        {/* Success Alert */}
        {successMsg && (
          <div
            id="login-success-banner"
            style={{
              background: "#ecfdf5",
              border: "1px solid #a7f3d0",
              borderRadius: 8,
              padding: "12px 14px",
              marginBottom: 18,
              display: "flex",
              alignItems: "flex-start",
              gap: 10,
              color: "#065f46",
              fontSize: 13,
              lineHeight: "1.4"
            }}
          >
            <CheckCircle2 size={18} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>{successMsg}</span>
          </div>
        )}

        {/* Session Expired / Error Alert */}
        {(error || sessionExpiredMessage) && (
          <div
            id="login-alert-banner"
            style={{
              background: "#fef2f2",
              border: "1px solid #fecaca",
              borderRadius: 8,
              padding: "12px 14px",
              marginBottom: 18,
              display: "flex",
              alignItems: "flex-start",
              gap: 10,
              color: "#991b1b",
              fontSize: 13,
              lineHeight: "1.4"
            }}
          >
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>{error || sessionExpiredMessage}</span>
          </div>
        )}

        {mode === "login" && (
          <>
            {/* Login Form */}
            <form onSubmit={handleSubmit}>
              {/* Email Field */}
              <div style={{ marginBottom: 16 }}>
                <label style={{
                  display: "block",
                  fontSize: 13,
                  fontWeight: 600,
                  color: "#334155",
                  marginBottom: 6
                }}>
                  Email address
                </label>
                <div style={{ position: "relative" }}>
                  <Mail size={18} style={{
                    position: "absolute",
                    left: 12,
                    top: "50%",
                    transform: "translateY(-50%)",
                    color: "#94a3b8"
                  }} />
                  <input
                    id="login-email-input"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@company.com"
                    disabled={loading}
                    autoComplete="email"
                    required
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

              {/* Password Field */}
              <div style={{ marginBottom: 14 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <label style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: "#334155"
                  }}>
                    Password
                  </label>
                  <button
                    id="forgot-password-link"
                    type="button"
                    onClick={() => {
                      setError("");
                      setSuccessMsg("");
                      setResetEmail(email);
                      setMode("forgot_request");
                    }}
                    style={{
                      background: "none",
                      border: "none",
                      color: "#2563eb",
                      fontSize: 12,
                      fontWeight: 600,
                      cursor: "pointer",
                      padding: 0
                    }}
                  >
                    Forgot password?
                  </button>
                </div>
                <div style={{ position: "relative" }}>
                  <Lock size={18} style={{
                    position: "absolute",
                    left: 12,
                    top: "50%",
                    transform: "translateY(-50%)",
                    color: "#94a3b8"
                  }} />
                  <input
                    id="login-password-input"
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••••••"
                    disabled={loading}
                    autoComplete="current-password"
                    required
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
                    id="toggle-login-password-btn"
                    onClick={() => setShowPassword(!showPassword)}
                    tabIndex={-1}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    style={{
                      position: "absolute",
                      right: 12,
                      top: "50%",
                      transform: "translateY(-50%)",
                      background: "transparent",
                      border: "none",
                      cursor: "pointer",
                      color: "#94a3b8",
                      padding: 4,
                      display: "flex",
                      alignItems: "center"
                    }}
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>

              {/* Keep me signed in Checkbox (unchecked by default) */}
              <div style={{ marginBottom: 18, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <label
                  htmlFor="remember-me-checkbox"
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 8,
                    fontSize: 13,
                    fontWeight: 500,
                    color: "#334155",
                    cursor: loading ? "not-allowed" : "pointer",
                    userSelect: "none"
                  }}
                >
                  <input
                    id="remember-me-checkbox"
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    disabled={loading}
                    style={{
                      width: 16,
                      height: 16,
                      accentColor: "#1e3e62",
                      cursor: loading ? "not-allowed" : "pointer",
                      margin: 0
                    }}
                  />
                  <span>Keep me signed in</span>
                </label>
              </div>

              {/* Submit Button */}
              <button
                id="login-submit-btn"
                type="submit"
                disabled={loading}
                style={{
                  width: "100%",
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
                  gap: 8,
                  transition: "0.2s ease",
                  boxShadow: "0 4px 12px rgba(11, 25, 44, 0.25)"
                }}
              >
                {loading ? (
                  <>
                    <Loader2 size={18} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
                    <span>Signing in...</span>
                  </>
                ) : (
                  <span>Sign In</span>
                )}
              </button>
            </form>

            {/* Account Creation Link */}
            <div style={{
              marginTop: 22,
              paddingTop: 18,
              borderTop: "1px solid #e2e8f0",
              textAlign: "center",
              fontSize: 13,
              color: "#475569"
            }}>
              Don't have an account?{" "}
              <button
                id="go-to-signup-btn"
                type="button"
                onClick={onNavigateSignUp}
                style={{
                  background: "none",
                  border: "none",
                  color: "#1d4ed8",
                  fontWeight: 600,
                  cursor: "pointer",
                  textDecoration: "underline",
                  padding: 0,
                  fontSize: 13
                }}
              >
                Create account
              </button>
            </div>
          </>
        )}

        {mode === "forgot_request" && (
          <form onSubmit={handleForgotRequest}>
            <div style={{ marginBottom: 18 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6 }}>
                Registered Email Address
              </label>
              <div style={{ position: "relative" }}>
                <Mail size={18} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
                <input
                  id="forgot-email-input"
                  type="email"
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                  placeholder="name@company.com"
                  required
                  disabled={loading}
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
              <p style={{ fontSize: 12, color: "#64748b", margin: "6px 0 0" }}>
                A 6-digit verification code (valid for 10 minutes) will be sent to this email.
              </p>
            </div>

            <button
              id="forgot-submit-btn"
              type="submit"
              disabled={loading}
              style={{
                width: "100%",
                height: 44,
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
              {loading ? <Loader2 size={18} className="animate-spin" /> : null}
              <span>{loading ? "Sending OTP..." : "Send 6-Digit OTP"}</span>
            </button>

            <div style={{ marginTop: 16, display: "flex", justifyContent: "space-between", fontSize: 13 }}>
              <button
                type="button"
                onClick={() => {
                  setError("");
                  setSuccessMsg("");
                  setMode("login");
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "#475569",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  padding: 0
                }}
              >
                <ArrowLeft size={14} />
                <span>Back to Sign In</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setError("");
                  setMode("forgot_reset");
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "#2563eb",
                  fontWeight: 600,
                  cursor: "pointer",
                  padding: 0
                }}
              >
                Already have an OTP?
              </button>
            </div>
          </form>
        )}

        {mode === "forgot_reset" && (
          <form onSubmit={handleResetPasswordSubmit}>
            <div style={{
              background: "#f0fdf4",
              border: "1px solid #bbf7d0",
              borderRadius: 8,
              padding: "10px 12px",
              marginBottom: 16,
              fontSize: 12,
              color: "#166534"
            }}>
              <div>Enter the 6-digit OTP sent to:</div>
              <strong style={{ wordBreak: "break-all" }}>{resetEmail || "your registered email"}</strong>
              <div style={{ color: "#dc2626", fontWeight: 600, marginTop: 4 }}>
                Code expires in 10 minutes
              </div>
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6 }}>
                6-Digit One-Time Password (OTP)
              </label>
              <div style={{ position: "relative" }}>
                <KeyRound size={18} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
                <input
                  id="reset-otp-input"
                  type="text"
                  maxLength={6}
                  value={resetOtp}
                  onChange={(e) => setResetOtp(e.target.value.replace(/[^0-9]/g, "").slice(0, 6))}
                  placeholder="123456"
                  required
                  disabled={loading}
                  style={{
                    width: "100%",
                    height: 46,
                    padding: "0 12px 0 38px",
                    border: "2px solid #cbd5e1",
                    borderRadius: 8,
                    fontSize: 18,
                    fontWeight: 700,
                    letterSpacing: "6px",
                    outline: "none",
                    boxSizing: "border-box",
                    background: "#f8fafc",
                    color: "#0f172a"
                  }}
                />
              </div>
            </div>

            <div style={{ marginBottom: 14 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6 }}>
                New Password
              </label>
              <div style={{ position: "relative" }}>
                <Lock size={18} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
                <input
                  id="reset-new-password-input"
                  type={showNewPassword ? "text" : "password"}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Minimum 6 characters"
                  required
                  disabled={loading}
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
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  tabIndex={-1}
                  style={{
                    position: "absolute",
                    right: 12,
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    color: "#94a3b8"
                  }}
                >
                  {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <div style={{ marginBottom: 18 }}>
              <label style={{ display: "block", fontSize: 13, fontWeight: 600, color: "#334155", marginBottom: 6 }}>
                Confirm New Password
              </label>
              <div style={{ position: "relative" }}>
                <Lock size={18} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "#94a3b8" }} />
                <input
                  id="reset-confirm-password-input"
                  type="password"
                  value={confirmNewPassword}
                  onChange={(e) => setConfirmNewPassword(e.target.value)}
                  placeholder="Confirm new password"
                  required
                  disabled={loading}
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

            <button
              id="reset-password-submit-btn"
              type="submit"
              disabled={loading}
              style={{
                width: "100%",
                height: 44,
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
              {loading ? <Loader2 size={18} className="animate-spin" /> : null}
              <span>{loading ? "Updating Password..." : "Reset Password"}</span>
            </button>

            <div style={{ marginTop: 14, display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 13 }}>
              <button
                type="button"
                onClick={() => {
                  setError("");
                  setSuccessMsg("");
                  setMode("login");
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "#475569",
                  fontWeight: 600,
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  padding: 0
                }}
              >
                <ArrowLeft size={14} />
                <span>Back to Sign In</span>
              </button>

              <button
                type="button"
                onClick={handleResendOtp}
                disabled={otpCooldown > 0 || loading}
                style={{
                  background: "none",
                  border: "none",
                  color: otpCooldown > 0 ? "#94a3b8" : "#2563eb",
                  fontWeight: 600,
                  cursor: otpCooldown > 0 ? "not-allowed" : "pointer",
                  padding: 0
                }}
              >
                {otpCooldown > 0 ? `Resend OTP in ${otpCooldown}s` : "Resend OTP"}
              </button>
            </div>
          </form>
        )}
      </div>
      </div>
    </div>
  );
}
