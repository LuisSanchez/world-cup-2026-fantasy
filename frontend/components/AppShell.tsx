"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth-context";
import { BottomNav } from "./BottomNav";
import { ThemeToggle } from "./ThemeToggle";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [user, loading, router]);

  if (loading) {
    return <div className="loading-center">Cargando…</div>;
  }
  if (!user) return null;

  return (
    <div className="app-shell">
      <div className="container">
        <div className="header-bar">
          <div className="user-chip">
            {user.picture ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={user.picture} alt="" />
            ) : (
              <span>👤</span>
            )}
            <span>{user.name || user.email}</span>
            {user.is_admin && <span className="badge badge-live">Admin</span>}
          </div>
          <div className="header-actions">
            <ThemeToggle compact />
            <button className="btn btn-secondary btn-sm" onClick={logout}>
              Salir
            </button>
          </div>
        </div>
        {children}
      </div>
      <BottomNav />
    </div>
  );
}
