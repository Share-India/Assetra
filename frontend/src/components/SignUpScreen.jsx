import React, { useState, useEffect } from "react";
import { User, Mail, Lock, Eye, EyeOff, Loader2, AlertCircle, CheckCircle2, ArrowLeft, KeyRound, RefreshCw, ExternalLink } from "lucide-react";
import TermsModal from "./TermsModal";
import PrivacyModal from "./PrivacyModal";
import AssetraBrandLockup from "./AssetraBrandLockup";
import AuthFeaturePanel from "./AuthFeaturePanel";

export default function SignUpScreen({ onNavigateLogin, onNavigateForgotPassword, onLoginSuccess, apiBaseUrl }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [consented, setConsented] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Email verification step state
  const [awaitingVerification, setAwaitingVerification] = useState(false);
  const [verificationCode, setVerificationCode] = useState("");
  const [verificationLoading, setVerificationLoading] = useState(false);
  const [resendStatus, setResendStatus] = useState("");
  const [resendCooldown, setResendCooldown] = useState(0);

  // Modals for Terms & Privacy
  const [showTermsModal, setShowTermsModal] = useState(false);
  const [showPrivacyModal, setShowPrivacyModal] = useState(false);
  const [devCode, setDevCode] = useState("");

  useEffect(() => {
    document.title = awaitingVerification ? "Verify Email | Assetra" : "Create Account | Assetra";
  }, [awaitingVerification]);

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!name.trim()) {
      setError("Please enter your full name.");
      return;
    }
    if (!email.trim()) {
      setError("Please enter your email address.");
      return;
    }
    if (password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (!consented) {
      setError("You must agree to the Terms of Use and Privacy Policy to create an account.");
      return;
    }

    setLoading(true);
    try {
      let res;
      try {
        res = await fetch(`${apiBaseUrl}/auth/signup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: name.trim(),
            email: email.trim(),
            password: password,
            confirm_password: confirmPassword,
            consented: true
          })
        });
      } catch (netErr) {
        throw new Error(
          `Cannot connect to backend server at ${apiBaseUrl}. Please verify uvicorn is running on port 8001.`
        );
      }

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.detail || "Sign-up failed. Please check your information.");
      }

      if (data.status === "unverified_resend") {
        setResendStatus(data.message || "An unverified account with this email already exists. A new verification code has been sent.");
      }

      if (data.dev_code) {
        setDevCode(data.dev_code);
        setVerificationCode(data.dev_code);
      }

      // Smoothly switch to entering the 6-digit verification code
      setAwaitingVerification(true);
      setResendCooldown(60);
      setError("");
    } catch (err) {
      setError(err.message || "An error occurred while creating your account.");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e) => {
    e.preventDefault();
    setError("");
    setResendStatus("");

    if (!verificationCode.trim()) {
      setError("Please enter the 6-digit verification code.");
      return;
    }

    setVerificationLoading(true);
    try {
      const res = await fetch(`${apiBaseUrl}/auth/verify-code`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim(),
          code: verificationCode.trim()
        })
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Verification failed. Please check your code.");
      }

      if (data.token && onLoginSuccess) {
        onLoginSuccess(data.token, data.user);
      } else {
        onNavigateLogin();
      }
    } catch (err) {
      setError(err.message || "Invalid verification code.");
    } finally {
      setVerificationLoading(false);
    }
  };

  const handleResendCode = async () => {
    if (resendCooldown > 0) return;
    setError("");
    setResendStatus("Sending new code...");
    try {
      const res = await fetch(`${apiBaseUrl}/auth/resend-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Failed to resend code. Please try again.");
      }
      setResendCooldown(60);
      if (data.dev_code) {
        setDevCode(data.dev_code);
        setVerificationCode(data.dev_code);
        setResendStatus(`Development Mode: Verification code generated: ${data.dev_code}`);
      } else {
        setResendStatus(data.message || "A new 6-digit code has been dispatched to your inbox.");
      }
    } catch (err) {
      setError(err.message || "Failed to resend code. Please try again.");
      setResendStatus("");
    }
  };

  return (
    <div className="far-auth-page-container" style={{
      height: "100vh",
      maxHeight: "100vh",
      width: "100vw",
      background: "radial-gradient(ellipse at 50% 20%, #173b75 0%, #0b192c 60%, #030712 100%)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "16px",
      fontFamily: "'Inter', sans-serif",
      boxSizing: "border-box",
      overflow: "hidden"
    }}>
      <style>{`
        .far-auth-split-wrapper {
          width: 100%;
          max-width: 960px;
          max-height: calc(100vh - 32px);
          background: #ffffff;
          border-radius: 16px;
          box-shadow: 0 20px 50px -10px rgba(0, 0, 0, 0.55), 0 0 0 1px rgba(255, 255, 255, 0.1);
          display: flex;
          flex-direction: row;
          overflow: hidden;
          margin: auto;
          box-sizing: border-box;
        }
        .far-auth-form-column {
          flex: 1 1 50%;
          padding: 22px 30px;
          display: flex;
          flex-direction: column;
          justifyContent: center;
          box-sizing: border-box;
          background: #ffffff;
          min-width: 0;
          overflow-y: auto;
        }
        @media (max-width: 900px) {
          .far-auth-page-container {
            height: auto !important;
            min-height: 100vh !important;
            overflow-y: auto !important;
          }
          .far-auth-split-wrapper {
            flex-direction: column;
            max-width: 480px;
            max-height: none !important;
          }
          .auth-feature-panel {
            border-right: none !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12) !important;
            padding: 20px 18px !important;
          }
          .far-auth-form-column {
            padding: 22px 18px !important;
          }
        }
        @media (max-width: 767px) {
          input {
            font-size: 15px !important;
          }
        }
        @media (max-width: 480px) {
          .far-auth-split-wrapper {
            border-radius: 12px;
          }
          .auth-feature-panel {
            padding: 18px 14px !important;
          }
          .far-auth-form-column {
            padding: 18px 14px !important;
          }
        }
        input:focus-visible, button:focus-visible {
          outline: 2px solid #2563EB !important;
          outline-offset: 1px !important;
        }
      `}</style>

      {/* Terms & Privacy Modals */}
      <TermsModal isOpen={showTermsModal} onClose={() => setShowTermsModal(false)} />
      <PrivacyModal isOpen={showPrivacyModal} onClose={() => setShowPrivacyModal(false)} />

      <div className="far-auth-split-wrapper">
        {/* Left Side: Share India & Project Features */}
        <AuthFeaturePanel />

        {/* Right Side: Assetra Branding & Sign Up Form */}
        <div className="far-auth-form-column">
          {/* Assetra Brand Lockup on Right Side Form */}
          <div style={{ marginBottom: 10, textAlign: "center", width: "100%", display: "flex", justifyContent: "center" }}>
            <AssetraBrandLockup theme="light" iconSize={50} fontSize={23} taglineSize={12} align="center" />
          </div>

          {/* Card Header */}
          <div style={{ textAlign: "center", marginBottom: 14 }}>
            <h1 style={{
              fontSize: 19,
              fontWeight: 700,
              color: "#0b192c",
              margin: "0 0 3px 0",
              letterSpacing: "-0.02em"
            }}>
              {awaitingVerification ? "Verify Your Email" : "Create Your Account"}
            </h1>
            <p style={{ fontSize: 12, color: "#64748b", margin: 0 }}>
              {awaitingVerification
                ? `We sent a 6-digit code to ${email}`
                : "Create an account for Assetra"}
            </p>
          </div>

        {/* Error Alert */}
        {error && (
          <div style={{
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
          }}>
            <AlertCircle size={18} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>
              {error.includes("An account with this email already exists") ? (
                <>
                  An account with this email already exists.{" "}
                  <button
                    type="button"
                    onClick={() => {
                      if (onNavigateLogin) onNavigateLogin();
                    }}
                    style={{
                      background: "none",
                      border: "none",
                      color: "#1e40af",
                      fontWeight: 600,
                      textDecoration: "underline",
                      cursor: "pointer",
                      padding: 0,
                      fontSize: "inherit"
                    }}
                  >
                    Sign in
                  </button>
                  {", or "}
                  <button
                    type="button"
                    onClick={() => {
                      window.location.hash = "#forgot-password";
                      if (onNavigateForgotPassword) {
                        onNavigateForgotPassword(email.trim());
                      } else if (onNavigateLogin) {
                        onNavigateLogin();
                      }
                    }}
                    style={{
                      background: "none",
                      border: "none",
                      color: "#1e40af",
                      fontWeight: 600,
                      textDecoration: "underline",
                      cursor: "pointer",
                      padding: 0,
                      fontSize: "inherit"
                    }}
                  >
                    reset your password
                  </button>
                  .
                </>
              ) : (
                error
              )}
            </span>
          </div>
        )}

        {/* Info/Resend Toast */}
        {resendStatus && (
          <div style={{
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: 8,
            padding: "10px 14px",
            marginBottom: 16,
            color: "#1e40af",
            fontSize: 13,
            display: "flex",
            alignItems: "center",
            gap: 8
          }}>
            <CheckCircle2 size={16} />
            <span>{resendStatus}</span>
          </div>
        )}

        {/* STEP 2: Email Verification Code Entry */}
        {awaitingVerification ? (
          <form onSubmit={handleVerifyCode}>
            {devCode && (
              <div style={{
                background: "#eff6ff",
                border: "1px solid #bfdbfe",
                borderRadius: 8,
                padding: "10px 14px",
                marginBottom: 16,
                fontSize: 13,
                color: "#1e3a8a",
                lineHeight: 1.4
              }}>
                <div style={{ fontWeight: 600, marginBottom: 2 }}>Testing Mode (SMTP not configured in .env):</div>
                <div>Your 6-digit verification code is: <strong style={{ letterSpacing: 2, fontSize: 15, color: "#1d4ed8" }}>{devCode}</strong> (Auto-filled below)</div>
              </div>
            )}
            <div style={{ marginBottom: 20 }}>
              <label style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "#334155",
                marginBottom: 6
              }}>
                6-Digit Verification Code
              </label>
              <div style={{ position: "relative" }}>
                <KeyRound size={18} style={{
                  position: "absolute",
                  left: 12,
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "#94a3b8"
                }} />
                <input
                  id="verification-code-input"
                  type="text"
                  maxLength={6}
                  value={verificationCode}
                  onChange={(e) => setVerificationCode(e.target.value.replace(/\D/g, ""))}
                  placeholder="Enter 6-digit code"
                  disabled={verificationLoading}
                  required
                  autoFocus
                  style={{
                    width: "100%",
                    height: 48,
                    padding: "0 12px 0 38px",
                    border: "1px solid #cbd5e1",
                    borderRadius: 8,
                    fontSize: 18,
                    letterSpacing: "4px",
                    fontWeight: 700,
                    outline: "none",
                    boxSizing: "border-box",
                    background: "#f8fafc",
                    color: "#0f172a"
                  }}
                />
              </div>
              <div style={{ fontSize: 12, color: "#64748b", marginTop: 6 }}>
                Code expires in 15 minutes (max 5 attempts).
              </div>
            </div>

            <button
              id="verify-code-submit-btn"
              type="submit"
              disabled={verificationLoading || verificationCode.length < 6}
              style={{
                width: "100%",
                height: 44,
                minHeight: 44,
                background: (verificationLoading || verificationCode.length < 6)
                  ? "#94a3b8"
                  : "linear-gradient(135deg, #1e3e62 0%, #0b192c 100%)",
                color: "#ffffff",
                border: "none",
                borderRadius: 8,
                fontSize: 14,
                fontWeight: 600,
                cursor: (verificationLoading || verificationCode.length < 6) ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                boxShadow: "0 4px 12px rgba(11, 25, 44, 0.25)"
              }}
            >
              {verificationLoading ? (
                <>
                  <Loader2 size={18} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
                  <span>Verifying code...</span>
                </>
              ) : (
                <span>Verify & Sign In</span>
              )}
            </button>

            <div style={{
              marginTop: 18,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: 13
            }}>
              <button
                type="button"
                onClick={handleResendCode}
                disabled={resendCooldown > 0}
                style={{
                  background: "none",
                  border: "none",
                  color: resendCooldown > 0 ? "#94a3b8" : "#1d4ed8",
                  cursor: resendCooldown > 0 ? "not-allowed" : "pointer",
                  fontWeight: 600,
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 4,
                  padding: 0
                }}
              >
                <RefreshCw size={14} />
                <span>{resendCooldown > 0 ? `Resend Code (${resendCooldown}s)` : "Resend Code"}</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setAwaitingVerification(false);
                  setError("");
                }}
                style={{
                  background: "none",
                  border: "none",
                  color: "#64748b",
                  cursor: "pointer",
                  padding: 0
                }}
              >
                Change email
              </button>
            </div>
          </form>
        ) : (
          /* STEP 1: Registration Form */
          <form onSubmit={handleSubmit}>
            {/* Full Name Field */}
            <div style={{ marginBottom: 8 }}>
              <label style={{
                display: "block",
                fontSize: 12,
                fontWeight: 600,
                color: "#334155",
                marginBottom: 3
              }}>
                Full Name
              </label>
              <div style={{ position: "relative" }}>
                <User size={16} style={{
                  position: "absolute",
                  left: 11,
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "#94a3b8"
                }} />
                <input
                  id="signup-name-input"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. John Doe"
                  disabled={loading}
                  required
                  style={{
                    width: "100%",
                    height: 36,
                    padding: "0 10px 0 34px",
                    border: "1px solid #cbd5e1",
                    borderRadius: 7,
                    fontSize: 13,
                    outline: "none",
                    boxSizing: "border-box",
                    background: "#f8fafc"
                  }}
                />
              </div>
            </div>

            {/* Email Field */}
            <div style={{ marginBottom: 8 }}>
              <label style={{
                display: "block",
                fontSize: 12,
                fontWeight: 600,
                color: "#334155",
                marginBottom: 3
              }}>
                Email address
              </label>
              <div style={{ position: "relative" }}>
                <Mail size={16} style={{
                  position: "absolute",
                  left: 11,
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "#94a3b8"
                }} />
                <input
                  id="signup-email-input"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  disabled={loading}
                  autoComplete="email"
                  required
                  style={{
                    width: "100%",
                    height: 36,
                    padding: "0 10px 0 34px",
                    border: "1px solid #cbd5e1",
                    borderRadius: 7,
                    fontSize: 13,
                    outline: "none",
                    boxSizing: "border-box",
                    background: "#f8fafc"
                  }}
                />
              </div>
            </div>

            {/* Password Field */}
            <div style={{ marginBottom: 8 }}>
              <label style={{
                display: "block",
                fontSize: 12,
                fontWeight: 600,
                color: "#334155",
                marginBottom: 3
              }}>
                Password
              </label>
              <div style={{ position: "relative" }}>
                <Lock size={16} style={{
                  position: "absolute",
                  left: 11,
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "#94a3b8"
                }} />
                <input
                  id="signup-password-input"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="At least 6 characters"
                  disabled={loading}
                  required
                  style={{
                    width: "100%",
                    height: 36,
                    padding: "0 36px 0 34px",
                    border: "1px solid #cbd5e1",
                    borderRadius: 7,
                    fontSize: 13,
                    outline: "none",
                    boxSizing: "border-box",
                    background: "#f8fafc"
                  }}
                />
                <button
                  type="button"
                  id="toggle-signup-password-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  tabIndex={-1}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  style={{
                    position: "absolute",
                    right: 10,
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    color: "#94a3b8",
                    padding: 2,
                    display: "flex",
                    alignItems: "center"
                  }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Confirm Password Field */}
            <div style={{ marginBottom: 10 }}>
              <label style={{
                display: "block",
                fontSize: 12,
                fontWeight: 600,
                color: "#334155",
                marginBottom: 3
              }}>
                Confirm Password
              </label>
              <div style={{ position: "relative" }}>
                <Lock size={16} style={{
                  position: "absolute",
                  left: 11,
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "#94a3b8"
                }} />
                <input
                  id="signup-confirm-password-input"
                  type={showConfirmPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Re-enter password"
                  disabled={loading}
                  required
                  style={{
                    width: "100%",
                    height: 36,
                    padding: "0 36px 0 34px",
                    border: "1px solid #cbd5e1",
                    borderRadius: 7,
                    fontSize: 13,
                    outline: "none",
                    boxSizing: "border-box",
                    background: "#f8fafc"
                  }}
                />
                <button
                  type="button"
                  id="toggle-signup-confirm-password-btn"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  tabIndex={-1}
                  aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                  style={{
                    position: "absolute",
                    right: 10,
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                    color: "#94a3b8",
                    padding: 2,
                    display: "flex",
                    alignItems: "center"
                  }}
                >
                  {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {/* Terms & Privacy Consent Checkbox */}
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 12,
              padding: "6px 10px",
              background: "#f8fafc",
              borderRadius: 6,
              border: "1px solid #e2e8f0"
            }}>
              <input
                id="signup-consent-checkbox"
                type="checkbox"
                checked={consented}
                onChange={(e) => setConsented(e.target.checked)}
                required
                style={{
                  width: 15,
                  height: 15,
                  cursor: "pointer",
                  accentColor: "#1e3e62",
                  margin: 0
                }}
              />
              <label htmlFor="signup-consent-checkbox" style={{
                fontSize: 11.5,
                color: "#334155",
                lineHeight: 1.35,
                cursor: "pointer",
                userSelect: "none"
              }}>
                I agree to the{" "}
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    setShowTermsModal(true);
                  }}
                  style={{
                    background: "none",
                    border: "none",
                    padding: 0,
                    color: "#1d4ed8",
                    fontWeight: 600,
                    cursor: "pointer",
                    textDecoration: "underline",
                    fontSize: 11.5
                  }}
                >
                  Terms
                </button>
                {" "}and{" "}
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    setShowPrivacyModal(true);
                  }}
                  style={{
                    background: "none",
                    border: "none",
                    padding: 0,
                    color: "#1d4ed8",
                    fontWeight: 600,
                    cursor: "pointer",
                    textDecoration: "underline",
                    fontSize: 11.5
                  }}
                >
                  Privacy Policy
                </button>
              </label>
            </div>

            {/* Submit Button */}
            <button
              id="signup-submit-btn"
              type="submit"
              disabled={loading}
              style={{
                width: "100%",
                height: 38,
                minHeight: 38,
                background: loading ? "#94a3b8" : "linear-gradient(135deg, #1e3e62 0%, #0b192c 100%)",
                color: "#ffffff",
                border: "none",
                borderRadius: 7,
                fontSize: 13.5,
                fontWeight: 600,
                cursor: loading ? "not-allowed" : "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                transition: "0.2s ease",
                boxShadow: "0 3px 10px rgba(11, 25, 44, 0.2)"
              }}
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
                  <span>Creating account...</span>
                </>
              ) : (
                <span>Create account</span>
              )}
            </button>
          </form>
        )}

        {/* Back to Sign In Link */}
        <div style={{
          marginTop: 12,
          paddingTop: 10,
          borderTop: "1px solid #e2e8f0",
          textAlign: "center",
          fontSize: 12.5,
          color: "#475569"
        }}>
          Already have an account?{" "}
          <button
            id="back-to-signin-btn"
            type="button"
            onClick={onNavigateLogin}
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
            Back to sign in
          </button>
        </div>
      </div>
      </div>
    </div>
  );
}
