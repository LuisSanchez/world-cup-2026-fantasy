"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function LoginPage() {
  const { user, loading, loginDev, loginGoogle } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showDev, setShowDev] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace("/");
  }, [user, loading, router]);

  const onGoogle = async () => {
    setError("");
    setBusy(true);
    try {
      await loginGoogle();
    } catch (e) {
      if (e instanceof Error && e.message === "DEV_LOGIN") {
        setShowDev(true);
        setError("Google OAuth no configurado. Usa login de desarrollo abajo.");
      } else {
        setError(e instanceof Error ? e.message : "Error");
      }
    } finally {
      setBusy(false);
    }
  };

  const onDev = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await loginDev(email.trim());
      router.replace("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <div className="loading-center">Cargando…</div>;

  return (
    <div className="login-page">
      <div className="login-theme-bar">
        <ThemeToggle />
      </div>
      <div className="login-card">
        <div className="login-logo">
          <div style={{ fontSize: "3rem", marginBottom: 8 }}>🏆</div>
          <h1>WC Fantasy 2026</h1>
          <p>Quiniela del Mundial · predice y compite</p>
        </div>

        {error && <div className="error-msg">{error}</div>}

        <button className="btn btn-primary" onClick={onGoogle} disabled={busy}>
          Continuar con Google
        </button>

        <div className="divider">o desarrollo local</div>

        <button className="btn btn-secondary" onClick={() => setShowDev(!showDev)} type="button">
          Login por email (dev / admin)
        </button>

        {showDev && (
          <form onSubmit={onDev} style={{ marginTop: 16 }}>
            <input
              className="input"
              type="email"
              placeholder="admin@localhost.dev"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
            <button className="btn btn-primary" type="submit" disabled={busy}>
              Entrar
            </button>
            <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 10 }}>
              Super admin local: <code>admin@localhost.dev</code>
              <br />
              O cualquier email del CSV (ej. jugador@example.com)
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
