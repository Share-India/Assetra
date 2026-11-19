import React from "react";
import { X, Shield, Lock } from "lucide-react";

export default function PrivacyModal({ isOpen, onClose }) {
  if (!isOpen) return null;

  return (
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: "rgba(11, 25, 44, 0.75)",
      backdropFilter: "blur(4px)",
      zIndex: 99999,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "20px 16px",
      boxSizing: "border-box",
      fontFamily: "'Inter', sans-serif"
    }}>
      <div style={{
        background: "#ffffff",
        width: "100%",
        maxWidth: 680,
        maxHeight: "calc(100dvh - 32px)",
        borderRadius: 16,
        display: "flex",
        flexDirection: "column",
        boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.35)",
        overflow: "hidden"
      }}>
        {/* Modal Header */}
        <div style={{
          padding: "20px 24px",
          borderBottom: "1px solid #e2e8f0",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "#f8fafc"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: "#ecfdf5",
              color: "#059669",
              display: "flex",
              alignItems: "center",
              justifyContent: "center"
            }}>
              <Shield size={20} />
            </div>
            <div>
              <h2 style={{ fontSize: 18, fontWeight: 700, color: "#0f172a", margin: 0 }}>Privacy Policy</h2>
              <span style={{ fontSize: 12, color: "#64748b" }}>Data Protection Notice • Effective Date: October 2026</span>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            style={{
              background: "#F8FAFC",
              border: "1px solid #E2E8F0",
              cursor: "pointer",
              color: "#64748b",
              width: 44,
              height: 44,
              borderRadius: 8,
              display: "flex",
              alignItems: "center",
              justifyContent: "center"
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Modal Body with Scroll */}
        <div style={{
          padding: "24px",
          overflowY: "auto",
          fontSize: 14,
          lineHeight: 1.7,
          color: "#334155"
        }}>
          <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", marginTop: 0, marginBottom: 8 }}>
            1. What We Collect
          </h3>
          <p style={{ marginTop: 0, marginBottom: 16 }}>
            When you register, we collect your name, email address, password hash, and terms consent timestamp. When you calculate replacement values in ASSETRA, we process the asset descriptions, acquisition values, and purchase years contained in your uploaded asset register. We also record security logs (IP address, login timestamps, and user agent) for fraud prevention and abuse protection.
          </p>

          <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", marginBottom: 8 }}>
            2. Why We Collect It
          </h3>
          <p style={{ marginTop: 0, marginBottom: 16 }}>
            We use your data solely to:
            <br />• Index and calculate replacement values against multi-series WPI datasets.
            <br />• Provide historical saved analyses accessible exclusively to your account.
            <br />• Protect against bot abuse, brute force login attempts, and unauthorized access.
          </p>

          <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", marginBottom: 8 }}>
            3. Who Can See Your Data
          </h3>
          <p style={{ marginTop: 0, marginBottom: 16 }}>
            Your calculated analyses are private and accessible only by you. System administrators can monitor aggregate system metrics (file names, row counts, company names, and Gemini API call volumes). By default, system administrators cannot view your individual asset rows unless specifically authorized for audit or troubleshooting.
          </p>

          <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", marginBottom: 8 }}>
            4. Right to Erasure & Account Deletion
          </h3>
          <p style={{ marginTop: 0, marginBottom: 16 }}>
            In compliance with applicable data protection laws, you have the right to permanent erasure of your personal data. When you select <strong>Delete My Account</strong>, all your personal information, saved analyses, and calculation rows are permanently purged from the database in a cascading transaction.
          </p>

          <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", marginBottom: 8 }}>
            5. Backup Retention
          </h3>
          <p style={{ marginTop: 0, marginBottom: 16 }}>
            Encrypted database backups are maintained for disaster recovery and are kept for the retention period defined by system configuration (typically 180 days), after which they expire and are automatically overwritten.
          </p>

          <h3 style={{ fontSize: 15, fontWeight: 700, color: "#0f172a", marginBottom: 8 }}>
            6. Privacy Inquiries & Contact
          </h3>
          <p style={{ marginTop: 0, marginBottom: 0 }}>
            If you have questions about our data practices or wish to submit a privacy request, please contact our data compliance team at privacy@shareindia.com.
          </p>
        </div>

        {/* Modal Footer */}
        <div style={{
          padding: "16px 24px",
          borderTop: "1px solid #e2e8f0",
          display: "flex",
          justifyContent: "flex-end",
          background: "#f8fafc"
        }}>
          <button
            onClick={onClose}
            style={{
              padding: "9px 20px",
              background: "#059669",
              color: "#ffffff",
              border: "none",
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 600,
              cursor: "pointer"
            }}
          >
            I Understand & Close
          </button>
        </div>
      </div>
    </div>
  );
}
