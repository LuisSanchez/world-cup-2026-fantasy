"use client";

import { useEffect, useState } from "react";
import { formatCountdown, parseApiUtc } from "@/lib/api";

type Props = {
  lockAt: string | null;
  kickoff: string | null;
  status: string;
  canEdit: boolean;
  /** Called once when countdown crosses lock time (client clock) */
  onLockReached?: () => void;
};

/**
 * Live countdown until predictions lock (lock_at from API).
 * Cosmetic only — backend still enforces the real rule.
 */
export function LockCountdown({ lockAt, kickoff, status, canEdit, onLockReached }: Props) {
  const lockDate = parseApiUtc(lockAt);
  const kickDate = parseApiUtc(kickoff);
  const [now, setNow] = useState(() => Date.now());
  const [firedLock, setFiredLock] = useState(false);

  useEffect(() => {
    if (!lockDate) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [lockDate]);

  useEffect(() => {
    if (!lockDate || firedLock) return;
    if (now >= lockDate.getTime()) {
      setFiredLock(true);
      onLockReached?.();
    }
  }, [now, lockDate, firedLock, onLockReached]);

  if (!lockDate) {
    if (status === "upcoming" || canEdit) {
      return <span className="countdown countdown-open">Sin hora de cierre (TBD)</span>;
    }
    return null;
  }

  const secsToLock = Math.floor((lockDate.getTime() - now) / 1000);

  // Still open — show time until lock
  if (secsToLock > 0 && (canEdit || status === "upcoming")) {
    const urgent = secsToLock <= 600; // last 10 min before lock (20 min before kickoff) — emphasize last stretch
    const veryUrgent = secsToLock <= 120;
    return (
      <span
        className={`countdown ${veryUrgent ? "countdown-critical" : urgent ? "countdown-urgent" : "countdown-open"}`}
        title={kickDate ? `Cierra 10 min antes del inicio (${kickDate.toLocaleString()})` : undefined}
      >
        <span className="countdown-icon" aria-hidden>
          ⏱
        </span>
        Cierra en <strong>{formatCountdown(secsToLock)}</strong>
      </span>
    );
  }

  // Locked but not yet kicked off
  if (status === "locked" || (secsToLock <= 0 && kickDate && now < kickDate.getTime())) {
    const secsToKick = kickDate ? Math.max(0, Math.floor((kickDate.getTime() - now) / 1000)) : 0;
    return (
      <span className="countdown countdown-locked">
        <span className="countdown-icon" aria-hidden>
          🔒
        </span>
        Cerrado
        {secsToKick > 0 && (
          <>
            {" "}
            · inicio en <strong>{formatCountdown(secsToKick)}</strong>
          </>
        )}
      </span>
    );
  }

  if (status === "live") {
    return (
      <span className="countdown countdown-live">
        <span className="countdown-icon" aria-hidden>
          ●
        </span>
        En vivo · pronósticos cerrados
      </span>
    );
  }

  return null;
}
