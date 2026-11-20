import React from "react";
import { TrendingUp, ShieldCheck, FileSpreadsheet, Layers, CheckCircle2, Building2 } from "lucide-react";

export default function AuthFeaturePanel() {
  const features = [
    {
      icon: TrendingUp,
      title: "Official WPI Time Series (1954–2025)",
      desc: "Multi-stage inflation index linking across 6 official economic base periods for accurate current replacement cost."
    },
    {
      icon: Layers,
      title: "Automated Category & Column Detection",
      desc: "Smart header mapping detects descriptions, purchase years, and category hierarchies from any company FAR Excel file."
    },
    {
      icon: ShieldCheck,
      title: "100% Deterministic & Audit-Proof",
      desc: "Pure rule-based mathematical valuation conforming strictly to institutional insurance adequacy standards without black-box AI."
    },
    {
      icon: FileSpreadsheet,
      title: "Enterprise Reports & Persistent History",
      desc: "Instant valuation downloads with saved user analyses, full audit logging, and company-wide asset intelligence."
    }
  ];

  return (
    <div
      className="auth-feature-panel"
      style={{
        flex: "1 1 52%",
        background: "linear-gradient(160deg, #091326 0%, #0f244a 45%, #173b75 100%)",
        padding: "44px 40px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        color: "#ffffff",
        position: "relative",
        overflow: "hidden",
        borderRight: "1px solid rgba(255, 255, 255, 0.08)"
      }}
    >
      {/* Decorative background glow circles */}
      <div
        style={{
          position: "absolute",
          top: -80,
          left: -80,
          width: 260,
          height: 260,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(37, 99, 235, 0.25) 0%, transparent 70%)",
          pointerEvents: "none"
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: -100,
          right: -80,
          width: 320,
          height: 320,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(59, 130, 246, 0.2) 0%, transparent 70%)",
          pointerEvents: "none"
        }}
      />

      <div style={{ position: "relative", zIndex: 1 }}>
        {/* Company Header with Share India Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 32, flexWrap: "wrap" }}>
          <div
            style={{
              background: "#ffffff",
              padding: "7px 14px",
              borderRadius: 10,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 4px 14px rgba(0, 0, 0, 0.25)",
              border: "1px solid rgba(255, 255, 255, 0.8)"
            }}
          >
            <img
              src="/share_india_logo.png"
              alt="Share India"
              style={{
                height: 30,
                width: "auto",
                objectFit: "contain",
                display: "block"
              }}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "#60a5fa"
              }}
            >
              Enterprise Platform
            </span>
            <span style={{ fontSize: 13, color: "#94a3b8", fontWeight: 500 }}>
              Share India Insurance Brokers
            </span>
          </div>
        </div>

        {/* Hero Section */}
        <div style={{ marginBottom: 32 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              background: "rgba(37, 99, 235, 0.18)",
              border: "1px solid rgba(96, 165, 250, 0.3)",
              padding: "4px 10px",
              borderRadius: 20,
              fontSize: 11,
              fontWeight: 600,
              color: "#93c5fd",
              marginBottom: 14,
              letterSpacing: "0.02em"
            }}
          >
            <Building2 size={13} color="#60a5fa" />
            <span>Fixed Asset Register Replacement Valuation</span>
          </div>

          <h2
            style={{
              fontSize: 26,
              fontWeight: 800,
              lineHeight: 1.25,
              color: "#ffffff",
              margin: "0 0 12px 0",
              letterSpacing: "-0.025em"
            }}
          >
            Accurate Asset Valuation. Built for Adequate Coverage.
          </h2>
          <p
            style={{
              fontSize: 13.5,
              color: "#cbd5e1",
              lineHeight: 1.55,
              margin: 0
            }}
          >
            Estimate current replacement values for insurance adequacy using official Wholesale Price Index data from 1954 to 2025 across all major asset categories.
          </p>
        </div>

        {/* Feature Cards Grid */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          {features.map((feat, idx) => {
            const IconComponent = feat.icon;
            return (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 12,
                  background: "rgba(255, 255, 255, 0.04)",
                  border: "1px solid rgba(255, 255, 255, 0.07)",
                  padding: "12px 14px",
                  borderRadius: 10,
                  backdropFilter: "blur(4px)"
                }}
              >
                <div
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 8,
                    background: "rgba(37, 99, 235, 0.25)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    marginTop: 1,
                    border: "1px solid rgba(96, 165, 250, 0.3)"
                  }}
                >
                  <IconComponent size={16} color="#60a5fa" />
                </div>
                <div>
                  <div
                    style={{
                      fontSize: 13,
                      fontWeight: 700,
                      color: "#f8fafc",
                      marginBottom: 2
                    }}
                  >
                    {feat.title}
                  </div>
                  <div
                    style={{
                      fontSize: 11.5,
                      color: "#94a3b8",
                      lineHeight: 1.45
                    }}
                  >
                    {feat.desc}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Trust Footer */}
      <div
        style={{
          marginTop: 32,
          paddingTop: 18,
          borderTop: "1px solid rgba(255, 255, 255, 0.1)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 10,
          fontSize: 11.5,
          color: "#94a3b8",
          position: "relative",
          zIndex: 1
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <CheckCircle2 size={13} color="#34d399" />
          <span>Institutional Grade Reliability</span>
        </div>
        <div style={{ color: "#64748b" }}>
          © 2026 Share India Insurance Brokers
        </div>
      </div>
    </div>
  );
}
