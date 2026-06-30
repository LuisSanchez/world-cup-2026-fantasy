"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { MatchCard } from "@/components/MatchCard";
import { api, type PredictionWithMatch } from "@/lib/api";

const FILTERS = [
  { key: "all", label: "Todos" },
  { key: "open", label: "Abiertos" },
  { key: "live", label: "En vivo" },
  { key: "finished", label: "Finalizados" },
  { key: "group", label: "Grupos" },
  { key: "r16", label: "R16" },
  { key: "qf", label: "8vos" },
  { key: "sf", label: "Semi" },
  { key: "final", label: "Final" },
];

export default function HomePage() {
  const [items, setItems] = useState<PredictionWithMatch[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const data = await api.myPredictions();
      setItems(data);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Error");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, [load]);

  const filtered = useMemo(() => {
    return items.filter(({ match }) => {
      if (filter === "all") return true;
      if (filter === "open") return match.can_edit;
      if (filter === "live") return match.status === "live";
      if (filter === "finished") return match.status === "finished" || match.is_finished;
      return match.stage === filter;
    });
  }, [items, filter]);

  return (
    <AppShell>
      <h1 className="page-title">Mis pronósticos</h1>
      <p className="page-sub">Mundial 2026 · Cierra 10 min antes del partido</p>

      <div className="filters">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            className={`chip ${filter === f.key ? "active" : ""}`}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading && <div className="loading-center">Cargando partidos…</div>}
      {error && <div className="error-msg">{error}</div>}

      {!loading &&
        filtered.map(({ match, prediction }) => (
          <MatchCard key={match.id} match={match} prediction={prediction} onSaved={load} />
        ))}

      {!loading && filtered.length === 0 && (
        <div className="card" style={{ textAlign: "center", color: "var(--text-muted)" }}>
          No hay partidos en este filtro.
        </div>
      )}
    </AppShell>
  );
}
