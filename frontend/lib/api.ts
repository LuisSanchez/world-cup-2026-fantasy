/**
 * API base URL resolution (order of preference):
 *
 * 1. NEXT_PUBLIC_API_URL = full backend origin, e.g. https://api.example.com (no trailing slash)
 * 2. NEXT_PUBLIC_API_URL = "" | "same" | "proxy" → same-origin /api/* via Next proxy (BACKEND_URL on Vercel)
 * 3. Unset on Vercel/production → same-origin proxy
 * 4. Unset locally → http://localhost:8000
 */
function resolveApiBase(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL;

  if (raw === "" || raw === "same" || raw === "proxy" || raw === "/") {
    return "";
  }

  if (raw && raw.trim()) {
    const base = raw.trim().replace(/\/$/, "");
    // Common mistake: pointing at the Vercel frontend itself
    const host = base.replace(/^https?:\/\//, "");
    if (/wc-fantasy.*\.vercel\.app$/i.test(host) || /\.vercel\.app$/i.test(host)) {
      return "";
    }
    return base;
  }

  if (process.env.VERCEL || process.env.NODE_ENV === "production") {
    return "";
  }
  return "http://localhost:8000";
}

const API_URL = resolveApiBase();


export type User = {
  id: number;
  email: string;
  name: string;
  picture: string;
  is_admin: boolean;
  total_points: number;
};

export type Match = {
  id: number;
  match_number: number;
  home_team: string;
  away_team: string;
  home_flag: string;
  away_flag: string;
  kickoff: string | null;
  /** ISO datetime when predictions lock (kickoff − lock minutes); null if no kickoff */
  lock_at: string | null;
  stage: string;
  group_name: string;
  home_score: number | null;
  away_score: number | null;
  is_finished: boolean;
  is_placeholder: boolean;
  status: "upcoming" | "locked" | "live" | "finished";
  can_edit: boolean;
};

/** Parse API datetimes (naive UTC from FastAPI) as UTC */
export function parseApiUtc(iso: string | null | undefined): Date | null {
  if (!iso) return null;
  const s = iso.endsWith("Z") || /[+-]\d{2}:\d{2}$/.test(iso) ? iso : `${iso}Z`;
  const d = new Date(s);
  return Number.isNaN(d.getTime()) ? null : d;
}

export function formatCountdown(totalSeconds: number): string {
  if (totalSeconds <= 0) return "0:00";
  const d = Math.floor(totalSeconds / 86400);
  const h = Math.floor((totalSeconds % 86400) / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  if (d > 0) return `${d}d ${h}h ${pad(m)}m`;
  if (h > 0) return `${h}:${pad(m)}:${pad(s)}`;
  return `${m}:${pad(s)}`;
}

export type Prediction = {
  id: number;
  match_id: number;
  home_score: number;
  away_score: number;
  points_goals: number;
  points_result: number;
  points_total: number;
};

export type PredictionWithMatch = {
  prediction: Prediction | null;
  match: Match;
};

export type LeaderboardEntry = {
  rank: number;
  user_id: number;
  email: string;
  name: string;
  picture: string;
  total_points: number;
  predictions_count: number;
};

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("wc_token");
}

export function setToken(token: string) {
  localStorage.setItem("wc_token", token);
}

export function clearToken() {
  localStorage.removeItem("wc_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  health: () => request<{ status: string }>("/api/health"),
  googleAuthUrl: () =>
    request<{ url: string | null; dev_login: boolean }>("/api/auth/google/url"),
  devLogin: (email: string) =>
    request<{ access_token: string; user: User }>("/api/auth/dev-login", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  me: () => request<User>("/api/auth/me"),
  matches: (stage?: string) =>
    request<Match[]>(`/api/matches${stage ? `?stage=${stage}` : ""}`),
  myPredictions: () => request<PredictionWithMatch[]>("/api/predictions/me"),
  savePrediction: (matchId: number, home_score: number, away_score: number) =>
    request<Prediction>(`/api/predictions/${matchId}`, {
      method: "PUT",
      body: JSON.stringify({ home_score, away_score }),
    }),
  leaderboard: () => request<LeaderboardEntry[]>("/api/leaderboard"),
  adminUsers: () => request<User[]>("/api/admin/users"),
  adminUserPredictions: (userId: number) =>
    request<PredictionWithMatch[]>(`/api/admin/users/${userId}/predictions`),
  adminSetScore: (matchId: number, home_score: number, away_score: number) =>
    request<Match>(`/api/admin/matches/${matchId}/score`, {
      method: "POST",
      body: JSON.stringify({ home_score, away_score, is_finished: true }),
    }),
  adminUpdateMatch: (matchId: number, data: Record<string, unknown>) =>
    request<Match>(`/api/admin/matches/${matchId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  adminSyncResults: () =>
    request<{
      checked: number;
      updated: number;
      skipped_no_api_key: boolean;
      updates: { match_id: number; match_number: number; score: string }[];
    }>("/api/admin/sync-results", { method: "POST" }),
  adminSyncStatus: () =>
    request<{
      football_api_configured: boolean;
      league_id: number;
      season: number;
      match_duration_minutes: number;
      results_fetch_window_minutes: number;
      results_poll_seconds: number;
    }>("/api/admin/sync-status"),
  /**
   * Upload quiniela CSV (admin). Always sends a new file; server stores quiniela_<uuid>.csv.
   */
  adminImportQuiniela: async (
    file: File,
    opts?: { updateExisting?: boolean; alsoSyncResults?: boolean }
  ) => {
    const updateExisting = opts?.updateExisting !== false;
    const alsoSyncResults = opts?.alsoSyncResults === true;
    const q = new URLSearchParams({
      update_existing: String(updateExisting),
      also_sync_results: String(alsoSyncResults),
    });
    const token = typeof window !== "undefined" ? localStorage.getItem("wc_token") : null;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const body = new FormData();
    body.append("file", file);
    const res = await fetch(`${API_URL}/api/admin/import-quiniela?${q}`, {
      method: "POST",
      headers,
      body,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(typeof err.detail === "string" ? err.detail : err.detail?.[0]?.msg || `HTTP ${res.status}`);
    }
    return res.json() as Promise<{
      ok: boolean;
      error?: string;
      csv?: string;
      saved_to?: string;
      users_created?: number;
      predictions_created?: number;
      predictions_updated?: number;
      predictions_unchanged_or_skipped?: number;
      results_sync?: { checked?: number; updated?: number; skipped_no_api_key?: boolean };
      recalculated?: boolean;
    }>;
  },
  adminRecalculate: () => request<{ ok: boolean }>("/api/admin/recalculate", { method: "POST" }),
  /** Admin-only: download Excel (leaderboard + per-player match scores). */
  adminExportScoresExcel: async (): Promise<Blob> => {
    const token = typeof window !== "undefined" ? localStorage.getItem("wc_token") : null;
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API_URL}/api/admin/export/scores.xlsx`, { headers });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.blob();
  },
  dashboard: () => request<DashboardData>("/api/dashboard"),
};

export type DashboardLeader = {
  user_id: number;
  name: string;
  email: string;
  picture: string;
  value: number;
  evaluated: number;
  total_points: number;
} | null;

export type DashboardRankRow = {
  rank: number;
  user_id: number;
  name: string;
  email: string;
  picture: string;
  value: number;
  evaluated: number;
  total_points: number;
};

export type DashboardPlayer = {
  user_id: number;
  name: string;
  email: string;
  picture: string;
  total_points: number;
  evaluated: number;
  exact_scores: number;
  team_goals_hits: number;
  result_hits: number;
  goal_diff_hits: number;
  avg_points_when_result_correct: number;
  avg_points_when_result_wrong: number;
  avg_points_overall: number;
  hit_rate_result: number;
  hit_rate_exact: number;
};

export type DashboardData = {
  finished_matches: number;
  players_count: number;
  highlights: {
    most_exact: DashboardLeader;
    most_team_goals: DashboardLeader;
    most_results: DashboardLeader;
    most_goal_diff: DashboardLeader;
    best_avg_when_winning: DashboardLeader;
    best_avg_when_losing: DashboardLeader;
    best_avg_overall: DashboardLeader;
    most_points: DashboardLeader;
  };
  rankings: Record<string, DashboardRankRow[]>;
  players: DashboardPlayer[];
};

export function flagUrl(code: string, w = 40): string {
  if (!code) return "";
  return `https://flagcdn.com/w${w}/${code.toLowerCase()}.png`;
}

export function formatKickoff(iso: string | null): string {
  if (!iso) return "TBD";
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
  return d.toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function stageLabel(stage: string): string {
  const map: Record<string, string> = {
    group: "Fase de grupos",
    r16: "Dieciseisavos",
    qf: "Octavos",
    sf: "Semifinales",
    third: "3er puesto",
    final: "Final",
    knockout: "Eliminatorias",
  };
  return map[stage] || stage;
}
