"""
Vercel serverless entry for FastAPI.

Vercel project settings (second project, backend only):
  - Root Directory: backend
  - Framework Preset: Other  (NOT Next.js)
  - Output Directory: leave EMPTY (do not set .next)
  - Install Command: pip install -r requirements.txt  (or default from vercel.json)

Env vars on this Vercel backend project:
  DATABASE_URL, SECRET_KEY, FRONTEND_URL=https://wc-fantasy-fs.vercel.app, ...
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure `app` package is importable (backend/ is project root on Vercel)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

os.environ.setdefault("VERCEL", "1")

from mangum import Mangum

from app.main import app, run_startup_init

# Run DB init on cold start (Mangum lifespan="off" skips FastAPI lifespan)
try:
    run_startup_init()
except Exception as e:  # pragma: no cover — log but still export handler
    print(f"run_startup_init warning: {e}")

# lifespan off: avoid ASGI lifespan issues on Vercel; we init above instead
handler = Mangum(app, lifespan="off")
