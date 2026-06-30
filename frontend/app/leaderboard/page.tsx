"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { api, type LeaderboardEntry } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function LeaderboardPage() {
  const [rows, setRows] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    const load = async () => {
      try {
        setRows(await api.leaderboard());
      } finally {
        setLoading(false);
      }
    };
    load();
    const t = setInterval(load, 30_000);
    return () => clearInterval(t);
  }, []);

  const rankClass = (r: number) => {
    if (r === 1) return "gold";
    if (r === 2) return "silver";
    if (r === 3) return "bronze";
    return "";
  };

  return (
    <AppShell>
      <h1 className="page-title">Ranking</h1>
      <p className="page-sub">Puntos actualizados al finalizar cada partido</p>

      {loading && <div className="loading-center">Cargando…</div>}

      {rows.map((row) => {
        const isMe = user?.id === row.user_id;
        return (
          <div
            key={row.user_id}
            className="lb-row"
            style={isMe ? { borderColor: "var(--accent)", boxShadow: "0 0 0 1px var(--accent)" } : undefined}
          >
            <div className={`lb-rank ${rankClass(row.rank)}`}>{row.rank}</div>
            {row.picture ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img className="lb-avatar" src={row.picture} alt="" />
            ) : (
              <div className="lb-avatar" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
                👤
              </div>
            )}
            <div className="lb-info">
              <div className="lb-name">
                {row.name} {isMe && <span style={{ color: "var(--accent)" }}>(tú)</span>}
              </div>
              <div className="lb-email">
                {row.email} · {row.predictions_count} pronósticos
              </div>
            </div>
            <div className="lb-points">{row.total_points}</div>
          </div>
        );
      })}
    </AppShell>
  );
}
