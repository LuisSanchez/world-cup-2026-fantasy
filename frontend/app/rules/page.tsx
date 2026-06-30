"use client";

import { AppShell } from "@/components/AppShell";

export default function RulesPage() {
  return (
    <AppShell>
      <h1 className="page-title">Reglas</h1>
      <p className="page-sub">Cómo se puntúa en la quiniela</p>

      <div className="rules-box">
        <p style={{ marginBottom: 10 }}>
          Los puntos son <strong>acumulativos</strong> según lo que aciertes:
        </p>
        <ul style={{ paddingLeft: 18, lineHeight: 1.7 }}>
          <li>
            <strong style={{ color: "var(--gold)" }}>+1</strong> — Acertar ganador o empate
          </li>
          <li>
            <strong style={{ color: "var(--gold)" }}>+1</strong> — Acertar los goles de al menos un equipo
          </li>
          <li>
            <strong style={{ color: "var(--gold)" }}>+1</strong> — Acertar la diferencia de goles
          </li>
          <li>
            <strong style={{ color: "var(--gold)" }}>+2</strong> — Marcador exacto
          </li>
        </ul>
        <br />
        <p>
          Si aciertas el marcador exacto, sumas también las demás categorías aplicables.
          Máximo sin exacto: <strong>3 pts</strong>. Máximo total: <strong>5 pts</strong> por partido.
        </p>
      </div>

      <div className="rules-box">
        <p>
          <strong>Ejemplo</strong> — resultado real <strong>2-1</strong>
        </p>
        <br />
        <ul style={{ paddingLeft: 18, lineHeight: 1.7, fontSize: "0.78rem" }}>
          <li><code>2-1</code> → <strong>5 pts</strong> (todo)</li>
          <li><code>1-0</code> → <strong>2 pts</strong> (ganador + diferencia)</li>
          <li><code>2-0</code> → <strong>2 pts</strong> (ganador + goles de un equipo)</li>
          <li><code>0-1</code> / <code>2-2</code> → <strong>1 pt</strong> (goles de un equipo)</li>
          <li><code>0-2</code> → <strong>0 pts</strong></li>
        </ul>
      </div>

      <div className="rules-box">
        <p>
          <strong>Plazos</strong>
        </p>
        <br />
        <ul style={{ paddingLeft: 18 }}>
          <li>Solo puedes editar partidos futuros.</li>
          <li>Los pronósticos se bloquean <strong>10 minutos antes</strong> del inicio.</li>
          <li>Partidos en curso o finalizados no se pueden modificar.</li>
        </ul>
      </div>

      <div className="rules-box">
        <p>
          <strong>Ranking</strong>
        </p>
        <br />
        <p>
          Cuando un partido termina y el admin publica el resultado oficial, los puntos se
          recalculan automáticamente y el leaderboard se actualiza.
        </p>
      </div>
    </AppShell>
  );
}
