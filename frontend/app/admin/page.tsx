"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { MatchCard } from "@/components/MatchCard";
import {
  api,
  type LeaderboardEntry,
  type PredictionWithMatch,
  type User,
} from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useRouter } from "next/navigation";

type Tab = "scores" | "users";

export default function AdminPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("scores");
  const [matches, setMatches] = useState<PredictionWithMatch[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUser, setSelectedUser] = useState<number | "">("");
  const [userPreds, setUserPreds] = useState<PredictionWithMatch[]>([]);
  const [lb, setLb] = useState<LeaderboardEntry[]>([]);
  const [syncMsg, setSyncMsg] = useState("");
  const [syncBusy, setSyncBusy] = useState(false);
  const [syncCfg, setSyncCfg] = useState<{
    football_api_configured?: boolean;
    cron_jobs_enabled?: boolean;
    background_worker_running?: boolean;
    cron_jobs_env_default?: boolean;
    results_poll_seconds?: number;
  } | null>(null);
  const [cronBusy, setCronBusy] = useState(false);
  const [exportBusy, setExportBusy] = useState(false);
  const [exportMsg, setExportMsg] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [pendingCsv, setPendingCsv] = useState<File | null>(null);
  const [alsoSyncAfterUpload, setAlsoSyncAfterUpload] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadMatches = useCallback(async () => {
    const data = await api.myPredictions();
    setMatches(data);
  }, []);

  useEffect(() => {
    if (!authLoading && user && !user.is_admin) router.replace("/");
  }, [user, authLoading, router]);

  useEffect(() => {
    if (!user?.is_admin) return;
    loadMatches();
    api.adminUsers().then(setUsers);
    api.leaderboard().then(setLb);
    api.adminSyncStatus().then(setSyncCfg).catch(() => null);
  }, [user, loadMatches]);

  const runSync = async () => {
    setSyncBusy(true);
    setSyncMsg("");
    try {
      const r = await api.adminSyncResults();
      setSyncMsg(
        r.skipped_no_api_key
          ? "Sin FOOTBALL_API_KEY — configura la API o publica resultados a mano."
          : `Revisados: ${r.checked}, actualizados: ${r.updated}${
              r.updates?.length ? ` (${r.updates.map((u) => `#${u.match_number} ${u.score}`).join(", ")})` : ""
            }`
      );
      await loadMatches();
      setLb(await api.leaderboard());
    } catch (e) {
      setSyncMsg(e instanceof Error ? e.message : "Error en sync");
    } finally {
      setSyncBusy(false);
    }
  };

  const toggleCronJobs = async (enabled: boolean) => {
    setCronBusy(true);
    setSyncMsg("");
    try {
      const r = await api.adminSetCronJobs(enabled);
      setSyncCfg((prev) => ({
        ...prev,
        cron_jobs_enabled: r.cron_jobs_enabled,
        background_worker_running: r.background_worker_running,
        cron_jobs_env_default: r.cron_jobs_env_default,
        results_poll_seconds: r.results_poll_seconds,
      }));
      setSyncMsg(
        r.cron_jobs_enabled
          ? `Cron jobs ACTIVADOS (worker ${r.background_worker_running ? "en marcha" : "iniciando"}; poll ${r.results_poll_seconds}s).`
          : "Cron jobs DESACTIVADOS — no hay sync automático ni worker en background (ahorra créditos DB/API)."
      );
    } catch (e) {
      setSyncMsg(e instanceof Error ? e.message : "Error al cambiar cron jobs");
    } finally {
      setCronBusy(false);
    }
  };

  const loadUserPreds = async (uid: number) => {
    setSelectedUser(uid);
    setUserPreds(await api.adminUserPredictions(uid));
  };

  const downloadExcel = async () => {
    setExportBusy(true);
    setExportMsg("");
    try {
      const blob = await api.adminExportScoresExcel();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `wc_fantasy_puntuaciones_${new Date().toISOString().slice(0, 10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      setExportMsg("Excel descargado (Leaderboard + Puntuaciones).");
    } catch (e) {
      setExportMsg(e instanceof Error ? e.message : "Error al exportar");
    } finally {
      setExportBusy(false);
    }
  };

  const acceptCsvFile = (f: File | null | undefined) => {
    if (!f) return;
    const name = f.name.toLowerCase();
    if (!name.endsWith(".csv") && !name.endsWith(".tsv") && !name.endsWith(".txt")) {
      setSyncMsg("Sube un archivo .csv (export de la hoja de quiniela).");
      return;
    }
    setPendingCsv(f);
    setSyncMsg(`Archivo listo: ${f.name} (${Math.round(f.size / 1024)} KB). Pulsa Importar.`);
  };

  /** Upload CSV (new quiniela_<uuid>.csv each time), import predictions, optionally sync results. */
  const runQuinielaUpload = async (file: File, withResults: boolean) => {
    setSyncBusy(true);
    setSyncMsg("");
    try {
      const imp = await api.adminImportQuiniela(file, {
        updateExisting: true,
        alsoSyncResults: withResults,
      });
      if (!imp.ok) {
        setSyncMsg(imp.error || "Error importando quiniela");
        return;
      }
      const rs = imp.results_sync;
      setSyncMsg(
        `Guardado: ${imp.saved_to || imp.csv || "servidor"}. ` +
          `Quiniela: +${imp.predictions_created ?? 0} nuevas, ~${imp.predictions_updated ?? 0} actualizadas, ${imp.predictions_unchanged_or_skipped ?? 0} sin cambio.` +
          (withResults
            ? rs?.skipped_no_api_key
              ? " Resultados: sin API key — publica a mano."
              : ` Resultados: revisados ${rs?.checked ?? "?"}, actualizados ${rs?.updated ?? "?"}.`
            : " (sin sync de resultados oficiales)")
      );
      setPendingCsv(null);
      await loadMatches();
      setLb(await api.leaderboard());
    } catch (e) {
      setSyncMsg(e instanceof Error ? e.message : "Error al subir/importar quiniela");
    } finally {
      setSyncBusy(false);
    }
  };

  if (!user?.is_admin) {
    return (
      <AppShell>
        <div className="loading-center">Solo administradores</div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <h1 className="page-title">Admin</h1>
      <p className="page-sub">Resultados oficiales y consulta de usuarios</p>

      <div className="filters">
        <button className={`chip ${tab === "scores" ? "active" : ""}`} onClick={() => setTab("scores")}>
          Resultados
        </button>
        <button className={`chip ${tab === "users" ? "active" : ""}`} onClick={() => setTab("users")}>
          Ver usuario
        </button>
      </div>

      {tab === "scores" && (
        <>
          <div className="rules-box">
            <p>
              Tras cada partido, el sistema puede buscar resultados en <strong>FBref</strong>,{" "}
              <strong>Wikipedia</strong> y opcionalmente API-Football. Por defecto los{" "}
              <strong>cron jobs están apagados</strong> para no gastar créditos de base de datos ni
              rate-limits. Actívalos solo cuando necesites sync automático; si no, usa{" "}
              <strong>Solo forzar sync</strong> o publica a mano.
            </p>
            <div
              style={{
                marginTop: 12,
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid var(--border)",
                background: "var(--surface-2, var(--bg))",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 12,
                  flexWrap: "wrap",
                }}
              >
                <div>
                  <strong>Cron jobs (sync automático)</strong>
                  <p style={{ margin: "4px 0 0", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    Worker en background + scrape al cargar leaderboard/partidos.{" "}
                    Estado:{" "}
                    <strong
                      style={{
                        color: syncCfg?.cron_jobs_enabled ? "var(--accent)" : "var(--danger)",
                      }}
                    >
                      {syncCfg?.cron_jobs_enabled ? "ON" : "OFF"}
                    </strong>
                    {syncCfg?.background_worker_running ? " · worker activo" : ""}
                    {syncCfg?.cron_jobs_env_default
                      ? " · env default ON"
                      : " · env default OFF"}
                  </p>
                </div>
                <button
                  type="button"
                  className={`btn btn-sm ${syncCfg?.cron_jobs_enabled ? "btn-secondary" : "btn-primary"}`}
                  disabled={cronBusy}
                  onClick={() => toggleCronJobs(!syncCfg?.cron_jobs_enabled)}
                >
                  {cronBusy
                    ? "…"
                    : syncCfg?.cron_jobs_enabled
                      ? "Apagar cron jobs"
                      : "Encender cron jobs"}
                </button>
              </div>
            </div>
            <p style={{ marginTop: 8, fontSize: "0.75rem" }}>
              API configurada:{" "}
              <strong style={{ color: syncCfg?.football_api_configured ? "var(--accent)" : "var(--danger)" }}>
                {syncCfg?.football_api_configured ? "sí" : "no"}
              </strong>
            </p>
            <div
              className={`csv-dropzone ${dragOver ? "csv-dropzone-active" : ""}`}
              onDragEnter={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={(e) => {
                e.preventDefault();
                setDragOver(false);
              }}
              onDrop={(e) => {
                e.preventDefault();
                setDragOver(false);
                acceptCsvFile(e.dataTransfer.files?.[0]);
              }}
              onClick={() => fileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.tsv,.txt,text/csv"
                style={{ display: "none" }}
                onChange={(e) => acceptCsvFile(e.target.files?.[0])}
              />
              <strong>Quiniela CSV</strong>
              <p style={{ margin: "8px 0 0", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                Arrastra aquí el export de la hoja (o haz clic). Cada import crea un archivo nuevo
                (<code>nombre_uuid.csv</code>); no hace falta ningún CSV al arrancar el servidor.
              </p>
              {pendingCsv && (
                <p style={{ marginTop: 8, fontSize: "0.85rem" }}>
                  Seleccionado: <strong>{pendingCsv.name}</strong>
                </p>
              )}
            </div>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginTop: 10,
                fontSize: "0.8rem",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={alsoSyncAfterUpload}
                onChange={(e) => setAlsoSyncAfterUpload(e.target.checked)}
              />
              Tras importar, también sincronizar resultados oficiales y recalcular puntos
            </label>
            <button
              className="btn btn-primary btn-sm"
              style={{ marginTop: 10, width: "100%" }}
              onClick={() => pendingCsv && runQuinielaUpload(pendingCsv, alsoSyncAfterUpload)}
              disabled={syncBusy || !pendingCsv}
            >
              {syncBusy ? "Importando…" : "Importar CSV subido"}
            </button>
            <p style={{ marginTop: 6, fontSize: "0.72rem", color: "var(--text-muted)" }}>
              Solo administradores. Sube el archivo cada vez que quieras sincronizar la hoja; no se
              reutiliza un quiniela.csv del contenedor.
            </p>
            <button
              className="btn btn-secondary btn-sm"
              style={{ marginTop: 8, width: "100%" }}
              onClick={runSync}
              disabled={syncBusy}
            >
              {syncBusy ? "Sincronizando…" : "Solo forzar sync de resultados"}
            </button>
            <button
              className="btn btn-secondary btn-sm"
              style={{ marginTop: 8, width: "100%" }}
              onClick={downloadExcel}
              disabled={exportBusy}
            >
              {exportBusy ? "Generando Excel…" : "Descargar Excel (ranking + puntuaciones)"}
            </button>
            <p style={{ marginTop: 6, fontSize: "0.72rem", color: "var(--text-muted)" }}>
              Hoja 1: leaderboard. Hoja 2: pronóstico y puntos de cada jugador por partido.
            </p>
            {syncMsg && <div className="success-msg" style={{ marginTop: 8 }}>{syncMsg}</div>}
            {exportMsg && <div className="success-msg" style={{ marginTop: 8 }}>{exportMsg}</div>}
          </div>
          {matches.map(({ match }) => (
            <MatchCard
              key={match.id}
              match={match}
              readOnly
              adminMode
              onSaved={loadMatches}
            />
          ))}
        </>
      )}

      {tab === "users" && (
        <>
          <div className="rules-box">
            Leaderboard: {lb.length} jugadores · selecciona un usuario para ver sus pronósticos
            (solo lectura).
          </div>
          <select
            className="select-full"
            value={selectedUser}
            onChange={(e) => {
              const v = e.target.value;
              if (v) loadUserPreds(Number(v));
            }}
          >
            <option value="">— Seleccionar usuario —</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name || u.email} ({u.email}) — {u.total_points} pts
              </option>
            ))}
          </select>

          {userPreds.map(({ match, prediction }) => (
            <MatchCard
              key={match.id}
              match={match}
              prediction={prediction}
              readOnly
            />
          ))}
        </>
      )}
    </AppShell>
  );
}
