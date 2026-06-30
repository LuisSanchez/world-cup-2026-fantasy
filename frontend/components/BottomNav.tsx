"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

const items = [
  { href: "/", icon: "⚽", label: "Partidos" },
  { href: "/leaderboard", icon: "🏆", label: "Ranking" },
  { href: "/dashboard", icon: "📊", label: "Stats" },
  { href: "/rules", icon: "📋", label: "Reglas" },
];

export function BottomNav() {
  const path = usePathname();
  const { user } = useAuth();

  return (
    <nav className="bottom-nav">
      {items.map((it) => (
        <Link
          key={it.href}
          href={it.href}
          className={`nav-item ${path === it.href ? "active" : ""}`}
        >
          <span className="icon">{it.icon}</span>
          <span>{it.label}</span>
        </Link>
      ))}
      {user?.is_admin && (
        <Link href="/admin" className={`nav-item ${path?.startsWith("/admin") ? "active" : ""}`}>
          <span className="icon">⚙️</span>
          <span>Admin</span>
        </Link>
      )}
    </nav>
  );
}
