"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import {
  api,
  type DashboardData,
  type DashboardLeader,
  type DashboardRankRow,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

type SectionKey =
  | "exact_scores"
  | "team_goals_hits"
  | "result_hits"
  | "avg_points_when_result_correct"
  | "avg_points_when_result_wrong"
  | "total_points";

const SECTIONS: {
  key: SectionKey;
  title: string;
  subtitle: string;
  icon: string;
  highlightKey: keyof DashboardData["highlights"];
  format?: (v: number) => string;
}[] = [
  {
    key: "exact_scores",
    title: "Marcadores exactos",
    subtitle: "Acertó el resultado completo (ej. 2-1)",
    icon: "🎯",
    highlightKey: "most_exact",
  },
  {
    key: "team_goals_hits",
    title: "Goles de un equipo",
    subtitle: "Acertó los goles de al menos un equipo",
    icon: "⚽",
    highlightKey: "most_team_goals",
  },
  {
    key: "result_hits",
    title: "Resultado (1X2)",
    subtitle: "Acertó ganador o empate",
    icon: "✅",
    highlightKey: "most_results",
  },
  {
    key: "avg_points_when_result_correct",
    title: "Prom. pts cuando acierta",
    subtitle: "Promedio de puntos en partidos donde acertó el 1X2",
    icon: "📈",
    highlightKey: "best_avg_when_winning",
    format: (v) => v.toFixed(2),
  },
  {
    key: "avg_points_when_result_wrong",
    title: "Prom. pts cuando falla",
    subtitle: "Promedio de puntos aunque falló el ganador/empate (salvajes)",
    icon: "📉",
    highlightKey: "best_avg_when_losing",
    format: (v) => v.toFixed(2),
  },
  {
    key: "total_points",
    title: "Puntos totales",
    subtitle: "Ranking general de la quiniela",
    icon: "🏆",
    highlightKey: "most_points",
  },
];

function Avatar({ picture, name }: { picture: string; name: string }) {
  if (picture) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img className="lb-avatar" src={picture} alt="" />;
  }
  return (
    <div className="lb-avatar" style={{ display: "flex", alignItems: "center", justifyContent: "center" }}>
      {(name || "?")[0].toUpperCase()}
    </div>
  );
}

function HighlightCard({
  icon,
  title,
  leader,
  format,
}: {
  icon: string;
  title: string;
  leader: DashboardLeader;
  format?: (v: number) => string;
}) {
  if (!leader) {
    return (
      <div className="dash-highlight">
        <div className="dash-highlight-icon">{icon}</div>
        <div className="dash-highlight-title">{title}</div>
        <div className="dash-highlight-empty">Sin datos aún</div>
      </div>
    );
  }
  const val = format ? format(leader.value) : String(leader.value);
  return (
    <div className="dash-highlight">
      <div className="dash-highlight-icon">{icon}</div>
      <div className="dash-highlight-title">{title}</div>
      <div className="dash-highlight-user">
        <Avatar picture={leader.picture} name={leader.name} />
        <div>
          <div className="dash-highlight-name">{leader.name}</div>
          <div className="dash-highlight-meta">{leader.evaluated} partidos eval.</div>
        </div>
      </div>
      <div className="dash-highlight-value">{val}</div>
    </div>
  );
}

function RankList({
  rows,
  format,
  meId,
}: {
  rows: DashboardRankRow[];
  format?: (v: number) => string;
  meId?: number;
}) {
  if (!rows?.length) {
    return <div className="card" style={{ color: "var(--text-muted)", textAlign: "center" }}>Sin datos</div>;
  }
  return (
    <>
      {rows.map((row) => {
        const isMe = meId === row.user_id;
        return (
          <div
            key={row.user_id}
            className="lb-row"
            style={isMe ? { borderColor: "var(--accent)", boxShadow: "0 0 0 1px var(--accent)" } : undefined}
          >
            <div className={`lb-rank ${row.rank <= 3 ? ["", "gold", "silver", "bronze"][row.rank] : ""}`}>
              {row.rank}
            </div>
            <Avatar picture={row.picture} name={row.name} />
            <div className="lb-info">
              <div className="lb-name">
                {row.name} {isMe && <span style={{ color: "var(--accent)" }}>(tú)</span>}
              </div>
              <div className="lb-email">
                {row.evaluated} eval. · {row.total_points} pts total
              </div>
            </div>
            <div className="lb-points" style={{ fontSize: "1.1rem" }}>
              {format ? format(row.value) : row.value}
            </div>
          </div>
        );
      })}
    </>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [section, setSection] = useState<SectionKey>("exact_scores");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        setData(await api.dashboard());
        setError("");
      } catch (e) {
        setError(e instanceof Error ? e.message : "Error");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const active = SECTIONS.find((s) => s.key === section)!;

  return (
    <AppShell>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-sub">
        Estadísticas de aciertos · {data?.finished_matches ?? "…"} partidos finalizados ·{" "}
        {data?.players_count ?? "…"} jugadores
      </p>

      {loading && <div className="loading-center">Cargando stats…</div>}
      {error && <div className="error-msg">{error}</div>}

      {data && (
        <>
          <div className="dash-grid">
            {SECTIONS.slice(0, 5).map((s) => (
              <HighlightCard
                key={s.key}
                icon={s.icon}
                title={s.title}
                leader={data.highlights[s.highlightKey]}
                format={s.format}
              />
            ))}
          </div>

          <div className="rules-box" style={{ marginTop: 8 }}>
            <strong>Prom. cuando acierta</strong> = puntos promedio solo en partidos donde acertó
            ganador/empate. <strong>Prom. cuando falla</strong> = puntos promedio cuando falló el 1X2
            (aún puede sumar por goles o diferencia).
          </div>

          <div className="filters" style={{ marginTop: 12 }}>
            {SECTIONS.map((s) => (
              <button
                key={s.key}
                className={`chip ${section === s.key ? "active" : ""}`}
                onClick={() => setSection(s.key)}
              >
                {s.icon} {s.title.split(" ")[0]}
              </button>
            ))}
          </div>

          <h2 className="dash-section-title">
            {active.icon} {active.title}
          </h2>
          <p className="page-sub" style={{ marginBottom: 12 }}>
            {active.subtitle}
          </p>

          <RankList
            rows={data.rankings[active.key] || []}
            format={active.format}
            meId={user?.id}
          />

          <h2 className="dash-section-title" style={{ marginTop: 28 }}>
            Tabla completa
          </h2>
          <p className="page-sub" style={{ marginBottom: 12 }}>
            Desliza horizontal en móvil
          </p>
          <div className="dash-table-wrap">
            <table className="dash-table">
              <thead>
                <tr>
                  <th>Jugador</th>
                  <th>Pts</th>
                  <th>Exactos</th>
                  <th>Goles eq.</th>
                  <th>1X2</th>
                  <th>Dif.</th>
                  <th>Prom✓</th>
                  <th>Prom✗</th>
                  <th>%1X2</th>
                </tr>
              </thead>
              <tbody>
                {data.players.map((p) => (
                  <tr
                    key={p.user_id}
                    className={user?.id === p.user_id ? "dash-row-me" : undefined}
                  >
                    <td className="dash-td-name">{p.name}</td>
                    <td>{p.total_points}</td>
                    <td>{p.exact_scores}</td>
                    <td>{p.team_goals_hits}</td>
                    <td>{p.result_hits}</td>
                    <td>{p.goal_diff_hits}</td>
                    <td>{p.avg_points_when_result_correct.toFixed(1)}</td>
                    <td>{p.avg_points_when_result_wrong.toFixed(1)}</td>
                    <td>{p.hit_rate_result}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </AppShell>
  );
}
