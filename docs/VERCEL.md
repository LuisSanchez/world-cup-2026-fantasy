# Deploying WC Fantasy on Vercel

## Important: one project ≠ frontend + FastAPI

This repo is a **monorepo** (`frontend/` Next.js + `backend/` FastAPI).  
**Vercel only runs the Next.js app** in this setup. FastAPI does **not** ship as a second service in the same Vercel project.

| URL | What runs |
|-----|-----------|
| `https://wc-fantasy-fs.vercel.app/login` | Next.js frontend |
| `https://wc-fantasy-fs.vercel.app/api/auth/me` | Not FastAPI alone — needs **proxy** (`BACKEND_URL`) or you get **404** |

Setting backend to `https://wc-fantasy-fs.vercel.app` or `.../api` points at **yourself**, not Python.

## Setup: frontend on Vercel + API elsewhere (Neon DB on API host)

1. Deploy FastAPI (Railway/Render/Fly/VPS) with `DATABASE_URL` (Neon), `FRONTEND_URL=https://wc-fantasy-fs.vercel.app`
2. Vercel env: `BACKEND_URL=https://your-fastapi-host` (no slash), leave `NEXT_PUBLIC_API_URL` empty
3. Redeploy Vercel
4. Check `https://wc-fantasy-fs.vercel.app/api/health` (proxied, not 404)
