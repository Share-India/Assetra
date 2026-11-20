import React from "react";
import { TrendingUp, ShieldCheck, FileSpreadsheet, Layers, CheckCircle2, Building2 } from "lucide-react";

export default function AuthFeaturePanel() {
  const features = [
    {
      icon: TrendingUp,
      title: "Official WPI Time Series (1954–2025)",
      desc: "Multi-stage inflation index linking across 6 official economic base periods for accurate replacement cost."
    },
    {
      icon: Layers,
      title: "Automated Category & Column Detection",
      desc: "Smart header mapping detects descriptions, purchase years, and category hierarchies from any company FAR file."
    },
    {
      icon: ShieldCheck,
      title: "100% Deterministic & Audit-Proof",
      desc: "Pure rule-based mathematical valuation conforming strictly to institutional insurance adequacy standards."
    },
    {
      icon: FileSpreadsheet,
      title: "Enterprise Reports & Persistent History",
      desc: "Instant valuation downloads with saved analyses, full audit logging, and company-wide asset intelligence."
    }
  ];

  return (
    <div
      className="auth-feature-panel"
      style={{
        flex: "1 1 50%",
        background: "linear-gradient(160deg, #091326 0%, #0f244a 45%, #173b75 100%)",
        padding: "26px 28px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        color: "#ffffff",
        position: "relative",
        overflow: "hidden",
        borderRight: "1px solid rgba(255, 255, 255, 0.08)",
        boxSizing: "border-box"
      }}
    >
      {/* Decorative background glow circles */}
      <div
        style={{
          position: "absolute",
          top: -60,
          left: -60,
          width: 220,
          height: 220,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(37, 99, 235, 0.22) 0%, transparent 70%)",
          pointerEvents: "none"
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: -80,
          right: -60,
          width: 260,
          height: 260,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(59, 130, 246, 0.18) 0%, transparent 70%)",
          pointerEvents: "none"
        }}
      />

      <div style={{ position: "relative", zIndex: 1 }}>
        {/* Company Header with Brand Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 18, flexWrap: "wrap" }}>
          <div
            style={{
              background: "#ffffff",
              width: 44,
              height: 44,
              borderRadius: 10,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 3px 12px rgba(0, 0, 0, 0.22)",
              border: "1px solid rgba(255, 255, 255, 0.9)",
              flexShrink: 0,
              padding: 4,
              boxSizing: "border-box"
            }}
          >
            <img
              src="/share_india_ribbon.png?v=3"
              alt="Share India Insurance Brokers"
              style={{
                width: "100%",
                height: "100%",
                objectFit: "contain",
                display: "block"
              }}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.15 }}>
            <span
              style={{
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "#60a5fa"
              }}
            >
              Enterprise Platform
            </span>
            <span style={{ fontSize: 13, color: "#e2e8f0", fontWeight: 600 }}>
              Share India Insurance Brokers
            </span>
          </div>
        </div>

        {/* Hero Section */}
        <div style={{ marginBottom: 16 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 5,
              background: "rgba(37, 99, 235, 0.18)",
              border: "1px solid rgba(96, 165, 250, 0.3)",
              padding: "2px 8px",
              borderRadius: 16,
              fontSize: 10.5,
              fontWeight: 600,
              color: "#93c5fd",
              marginBottom: 8,
              letterSpacing: "0.02em"
            }}
          >
            <Building2 size={12} color="#60a5fa" />
            <span>Fixed Asset Register Replacement Valuation</span>
          </div>

          <h2
            style={{
              fontSize: 20,
              fontWeight: 800,
              lineHeight: 1.25,
              color: "#ffffff",
              margin: "0 0 6px 0",
              letterSpacing: "-0.02em"
            }}
          >
            Accurate Asset Valuation. Built for Adequate Coverage.
          </h2>
          <p
            style={{
              fontSize: 12,
              color: "#94a3b8",
              lineHeight: 1.45,
              margin: 0
            }}
          >
            Estimate current replacement values for insurance adequacy using official Wholesale Price Index data (1954–2025).
          </p>
        </div>

        {/* Compact Feature Cards Grid */}
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {features.map((feat, idx) => {
            const IconComponent = feat.icon;
            return (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 10,
                  background: "rgba(255, 255, 255, 0.04)",
                  border: "1px solid rgba(255, 255, 255, 0.07)",
                  padding: "7px 10px",
                  borderRadius: 8,
                  backdropFilter: "blur(4px)"
                }}
              >
                <div
                  style={{
                    width: 26,
                    height: 26,
                    borderRadius: 6,
                    background: "rgba(37, 99, 235, 0.25)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    marginTop: 1,
                    border: "1px solid rgba(96, 165, 250, 0.3)"
                  }}
                >
                  <IconComponent size={14} color="#60a5fa" />
                </div>
                <div>
                  <div
                    style={{
                      fontSize: 12,
                      fontWeight: 700,
                      color: "#f8fafc",
                      lineHeight: 1.2,
                      marginBottom: 1
                    }}
                  >
                    {feat.title}
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: "#94a3b8",
                      lineHeight: 1.35
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
          marginTop: 14,
          paddingTop: 10,
          borderTop: "1px solid rgba(255, 255, 255, 0.1)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 6,
          fontSize: 10.5,
          color: "#94a3b8",
          position: "relative",
          zIndex: 1
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <CheckCircle2 size={12} color="#34d399" />
          <span>Institutional Grade Reliability</span>
        </div>
        <div style={{ color: "#64748b" }}>
          © 2026 Share India Insurance Brokers
        </div>
      </div>
    </div>
  );
}
