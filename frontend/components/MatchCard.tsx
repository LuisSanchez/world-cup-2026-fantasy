"use client";

import { useCallback, useState } from "react";
import {
  api,
  formatKickoff,
  type Match,
  type Prediction,
  stageLabel,
} from "@/lib/api";
import { Flag } from "./Flag";
import { LockCountdown } from "./LockCountdown";

const statusLabel: Record<string, string> = {
  upcoming: "Abierto",
  locked: "Cerrado",
  live: "En vivo",
  finished: "Finalizado",
};

type Props = {
  match: Match;
  prediction?: Prediction | null;
  readOnly?: boolean;
  showRealScore?: boolean;
  onSaved?: () => void;
  adminMode?: boolean;
};

export function MatchCard({
  match,
  prediction,
  readOnly = false,
  showRealScore = true,
  onSaved,
  adminMode = false,
}: Props) {
  const [home, setHome] = useState(prediction?.home_score ?? 0);
  const [away, setAway] = useState(prediction?.away_score ?? 0);
  const [adminHome, setAdminHome] = useState(match.home_score ?? 0);
  const [adminAway, setAdminAway] = useState(match.away_score ?? 0);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  // Local override when countdown hits lock (until parent refreshes)
  const [locallyLocked, setLocallyLocked] = useState(false);

  const handleLockReached = useCallback(() => {
    setLocallyLocked(true);
    onSaved?.(); // parent refresh so server status/can_edit updates
  }, [onSaved]);

  const editable = !readOnly && match.can_edit && !locallyLocked;
  const displayStatus = locallyLocked && match.status === "upcoming" ? "locked" : match.status;
  const hasPred = prediction != null;

  const save = async () => {
    setSaving(true);
    setErr("");
    setMsg("");
    try {
      await api.savePrediction(match.id, home, away);
      setMsg("Guardado");
      onSaved?.();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Error");
    } finally {
      setSaving(false);
    }
  };

  const saveAdminScore = async () => {
    setSaving(true);
    setErr("");
    try {
      await api.adminSetScore(match.id, adminHome, adminAway);
      setMsg("Resultado oficial guardado");
      onSaved?.();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card">
      <div className="card-header">
        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
          #{match.match_number} · {stageLabel(match.stage)}
        </span>
        <span className={`badge badge-${displayStatus}`}>{statusLabel[displayStatus]}</span>
      </div>

      <div className="match-teams">
        <div className="team">
          <Flag code={match.home_flag} team={match.home_team} />
          <span className="team-name">{match.home_team}</span>
        </div>

        <div className="score-inputs">
          {showRealScore && match.is_finished && match.home_score != null ? (
            <span className="real-score">
              {match.home_score} – {match.away_score}
            </span>
          ) : editable ? (
            <>
              <input
                className="score-input"
                type="number"
                min={0}
                max={20}
                value={home}
                onChange={(e) => setHome(Math.max(0, parseInt(e.target.value) || 0))}
              />
              <span className="score-sep">:</span>
              <input
                className="score-input"
                type="number"
                min={0}
                max={20}
                value={away}
                onChange={(e) => setAway(Math.max(0, parseInt(e.target.value) || 0))}
              />
            </>
          ) : hasPred ? (
            <span className="real-score" style={{ color: "var(--text)" }}>
              {prediction!.home_score} – {prediction!.away_score}
            </span>
          ) : (
            <span className="score-sep">vs</span>
          )}
        </div>

        <div className="team away">
          <Flag code={match.away_flag} team={match.away_team} />
          <span className="team-name">{match.away_team}</span>
        </div>
      </div>

      {hasPred && match.is_finished && (
        <div className="meta-row">
          <span>
            Tu pronóstico: {prediction!.home_score}–{prediction!.away_score}
          </span>
          {prediction!.points_total > 0 && (
            <span className="points-pill">+{prediction!.points_total} pts</span>
          )}
        </div>
      )}

      <div className="meta-row">
        <span>{formatKickoff(match.kickoff)}</span>
        {hasPred && !match.is_finished && (
          <span style={{ color: "var(--text-muted)" }}>
            Pred: {prediction!.home_score}–{prediction!.away_score}
          </span>
        )}
      </div>

      {!readOnly && !match.is_finished && displayStatus !== "finished" && (
        <div className="countdown-row">
          <LockCountdown
            lockAt={match.lock_at}
            kickoff={match.kickoff}
            status={displayStatus}
            canEdit={editable || (match.can_edit && !locallyLocked)}
            onLockReached={handleLockReached}
          />
        </div>
      )}

      {editable && (
        <button className="btn btn-primary btn-sm" style={{ marginTop: 10, width: "100%" }} onClick={save} disabled={saving}>
          {saving ? "Guardando…" : "Guardar pronóstico"}
        </button>
      )}

      {!editable && !readOnly && (locallyLocked || match.status === "locked") && !match.is_finished && (
        <div className="lock-notice">Pronósticos cerrados (10 min antes del partido)</div>
      )}

      {adminMode && (
        <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid var(--border)" }}>
          <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginBottom: 6 }}>
            Resultado oficial (admin)
          </div>
          <div className="score-inputs" style={{ justifyContent: "center" }}>
            <input
              className="score-input"
              type="number"
              min={0}
              value={adminHome}
              onChange={(e) => setAdminHome(Math.max(0, parseInt(e.target.value) || 0))}
            />
            <span className="score-sep">:</span>
            <input
              className="score-input"
              type="number"
              min={0}
              value={adminAway}
              onChange={(e) => setAdminAway(Math.max(0, parseInt(e.target.value) || 0))}
            />
          </div>
          <button
            className="btn btn-secondary btn-sm"
            style={{ marginTop: 8, width: "100%" }}
            onClick={saveAdminScore}
            disabled={saving}
          >
            Publicar resultado y actualizar ranking
          </button>
        </div>
      )}

      {msg && <div className="success-msg" style={{ marginTop: 8 }}>{msg}</div>}
      {err && <div className="error-msg" style={{ marginTop: 8 }}>{err}</div>}
    </div>
  );
}
