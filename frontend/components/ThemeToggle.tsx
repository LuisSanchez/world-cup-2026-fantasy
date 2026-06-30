"use client";

import { useTheme } from "@/lib/theme-context";

type Props = {
  className?: string;
  /** Compact icon-only for headers */
  compact?: boolean;
};

export function ThemeToggle({ className = "", compact = false }: Props) {
  const { theme, toggle } = useTheme();
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      className={`theme-toggle ${compact ? "theme-toggle-compact" : ""} ${className}`}
      onClick={toggle}
      aria-label={isDark ? "Cambiar a modo claro" : "Cambiar a modo oscuro"}
      title={isDark ? "Modo claro" : "Modo oscuro"}
    >
      <span className="theme-toggle-icon" aria-hidden>
        {isDark ? "☀️" : "🌙"}
      </span>
      {!compact && <span>{isDark ? "Claro" : "Oscuro"}</span>}
    </button>
  );
}
