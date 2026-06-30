# Deploy: Railway (backend) + Vercel (frontend)

Recommended production setup. **Do not** run FastAPI on Vercel.

```
Browser  →  https://wc-fantasy-fs.vercel.app        (Next.js on Vercel)
         →  /api/* proxy (optional)  →  https://YOUR-APP.up.railway.app  (FastAPI)
Database →  Neon / Railway Postgres  (DATABASE_URL on Railway only)
```

---

## 1. Railway — backend

### Create service

1. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub** → `LuisSanchez/wc-fantasy`.
2. **Root Directory**: leave empty / `.` (repo root). **Do not** set it to `backend` if the Dockerfile path is `backend/Dockerfile` — that mismatch is what caused `COPY start.sh: not found` / missing `backend/app` paths.
3. Build: **Dockerfile** at `backend/Dockerfile` (see repo-root `railway.toml`). Context = whole repo; image runs `uvicorn` directly (no `start.sh` in image).
4. **Generate domain**: Settings → Networking → **Generate Domain**  
   Example: `https://wc-fantasy-production.up.railway.app`

### Environment variables (Railway service)

| Variable | Example / notes |
|----------|------------------|
| `DATABASE_URL` | Neon: `postgresql://user:pass@host/db?sslmode=require` |
| `SECRET_KEY` | Long random string |
| `FRONTEND_URL` | `https://wc-fantasy-fs.vercel.app` |
| `BACKEND_URL` | Your Railway public URL (same as generate domain) |
| `SUPER_ADMIN_EMAIL` | Optional spectator admin |
| `ADMIN_EMAILS` | Comma-separated real admins |
| `FOOTBALL_API_KEY` | Optional, for results API |
| `PREDICTION_LOCK_MINUTES` | `10` (default) |

Railway sets `PORT` automatically; the Dockerfile/Procfile use it.

### Verify backend

Open in browser:

`https://YOUR-RAILWAY-URL/api/health`

Expect JSON like:

```json
{ "status": "ok", "database": "postgresql", "schedule_revision": 4 }
```

Startup runs seed (if empty), kickoff schedule refresh, and background results worker.

### Optional: delete the failed Vercel backend project

You no longer need a second Vercel project for Python.

---

## 2. Vercel — frontend only

### Project settings

1. **One** Vercel project (e.g. `wc-fantasy-fs`).
2. **Root Directory**: `frontend` (recommended) **or** repo root with workspaces.
3. Framework: **Next.js**.
4. Connect same GitHub repo; ignore/remove any backend-only Vercel project.

### Environment variables (Vercel — Production + Preview)

| Variable | Value |
|----------|--------|
| `BACKEND_URL` | `https://YOUR-RAILWAY-URL` (**no** trailing slash, **no** `/api`) |
| `NEXT_PUBLIC_API_URL` | Leave **empty** (browser calls `/api/*` on Vercel → Next proxy → Railway) |

Alternative (direct to Railway, skips proxy):

| `NEXT_PUBLIC_API_URL` | `https://YOUR-RAILWAY-URL` |
| `BACKEND_URL` | same (proxy fallback still works) |

CORS: backend already allows `FRONTEND_URL` and `*.vercel.app`.

### Redeploy

After setting `BACKEND_URL`, **Redeploy** the frontend (required for any `NEXT_PUBLIC_*`; server `BACKEND_URL` applies on next deploy too).

### Verify frontend

1. `https://wc-fantasy-fs.vercel.app/login` loads.
2. `https://wc-fantasy-fs.vercel.app/api/health` returns the **same** health JSON as Railway (via proxy), **not** 404.
3. Login / `/api/auth/me` works (401 without token is OK; 404 is not).

---

## 3. Local development (unchanged)

```bash
# backend
cd backend && source .venv/bin/activate
export DATABASE_URL="postgresql://..."   # or sqlite
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
echo 'NEXT_PUBLIC_API_URL=http://localhost:8000' > .env.local
npm run dev
```

---

## 4. Troubleshooting

| Symptom | Fix |
|---------|-----|
| Vercel `/api/auth/me` **404** | `BACKEND_URL` missing/wrong; redeploy frontend; ensure Railway is up |
| Vercel `/api/health` **502** | Railway URL wrong or backend crashed; check Railway logs |
| CORS errors (direct mode) | Set `FRONTEND_URL` on Railway to exact Vercel origin |
| Empty DB on Railway | First boot seeds if empty; point `DATABASE_URL` at Neon; wait for cold start |
| Wrong match times | Redeploy Railway so `schedule_revision` updates; or `POST /api/admin/refresh-kickoffs` as admin |

---

## 5. Re-sync quiniela from CSV upload (admin)

Containers start **without** any `quiniela.csv` mount or image copy. Schedule/matches seed from code; users/predictions come from admin uploads (or Google login + in-app picks).

When people update scores in the Google Sheet outside the app:

1. Export the sheet as CSV (columns: email + `Partido N: …` cells like `2-1`).
2. As **admin**: **Admin → Resultados** → drag onto **Quiniela CSV** → **Importar CSV subido**.
   - Optionally check **también sincronizar resultados oficiales** before import.
3. API (multipart, admin JWT, **file required**):  
   `POST /api/admin/import-quiniela?update_existing=true&also_sync_results=false` with form field `file`.

Each upload is stored as a **new** file (`{original_stem}_{uuid}.csv`) under the first writable dir: `QUINIELA_DATA_DIR` → `/app/data` → `backend/data` → `/tmp`. Uploads are **not** reused; upload again for the next sync. Predictions live in the DB after import.

`import-quiniela` upserts **predictions** only; official match scores come from results sync or admin entry.

**Local docker:** `make up` / compose uses only the `wc_sqlite_data` volume at `/app/data` — no host `data/quiniela.csv` bind (avoids “not a directory” if that path is missing or is a folder).
