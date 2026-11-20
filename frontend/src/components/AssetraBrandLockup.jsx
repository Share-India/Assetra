import React from "react";

/**
 * Reusable Assetra brand icon:
 * Displays the Assetra logo (Assetra.png) on a clean white background.
 * Contained in a rounded square with crisp border definition.
 */
export function AssetraIcon({ size = 44, style = {} }) {
  const radius = Math.max(8, Math.round(size * 0.22));
  return (
    <div
      style={{
        width: size,
        height: size,
        backgroundColor: "#FFFFFF",
        borderRadius: radius,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        boxShadow: "0 1px 3px rgba(0, 0, 0, 0.08), 0 0 0 1px rgba(0, 0, 0, 0.08)",
        overflow: "hidden",
        boxSizing: "border-box",
        padding: Math.max(3, Math.round(size * 0.08)),
        ...style
      }}
      aria-hidden="true"
    >
      <img
        src="/share_india_ribbon_logo.png?v=3"
        alt="Assetra"
        style={{
          width: "100%",
          height: "100%",
          objectFit: "contain",
          display: "block"
        }}
      />
    </div>
  );
}

/**
 * Reusable Assetra brand lockup:
 * - Rounded-square primary blue icon with white "A"
 * - Word "Assetra" in normal capitalisation, Inter 700, slightly tight letter spacing, dark navy (or white on dark)
 * - Tagline "Fixed asset valuation" in small grey text beneath
 */
export default function AssetraBrandLockup({
  theme = "light", // "light" | "dark"
  iconSize = 44,
  fontSize = 20,
  taglineSize = 12,
  showTagline = true,
  align = "left",
  style = {}
}) {
  const isDark = theme === "dark";
  const textColor = isDark ? "#FFFFFF" : "#0A192F"; // Dark navy or white
  const taglineColor = isDark ? "#94A3B8" : "#64748B"; // Accessible grey

  return (
    <div
      className="assetra-brand-lockup"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 10,
        textAlign: align,
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        userSelect: "none",
        ...style
      }}
    >
      <AssetraIcon size={iconSize} />
      <div style={{ display: "flex", flexDirection: "column", lineHeight: 1.15, minWidth: 0 }}>
        <span
          style={{
            fontSize,
            fontWeight: 700,
            color: textColor,
            letterSpacing: "-0.025em",
            fontFamily: "'Inter', sans-serif"
          }}
        >
          Assetra
        </span>
        {showTagline && (
          <span
            style={{
              fontSize: taglineSize,
              fontWeight: 400,
              color: taglineColor,
              letterSpacing: "0.01em",
              whiteSpace: "nowrap"
            }}
          >
            Fixed asset valuation
          </span>
        )}
      </div>
    </div>
  );
}
