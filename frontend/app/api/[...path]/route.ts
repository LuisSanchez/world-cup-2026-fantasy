import { NextRequest, NextResponse } from "next/server";

/**
 * Proxies /api/* on the Vercel frontend to the real FastAPI backend.
 *
 * Set in Vercel (server env, NOT required to be NEXT_PUBLIC):
 *   BACKEND_URL=https://your-api.example.com
 *   (no trailing slash; do not include /api in BACKEND_URL)
 *
 * Client can use NEXT_PUBLIC_API_URL="" (same-origin) so requests hit this proxy,
 * or set NEXT_PUBLIC_API_URL to the backend directly (bypasses proxy; needs CORS).
 */
function backendBase(): string {
  const b =
    process.env.BACKEND_URL ||
    process.env.API_BACKEND_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "";
  return b.replace(/\/$/, "");
}

async function proxy(req: NextRequest, segments: string[]) {
  const base = backendBase();
  if (!base) {
    return NextResponse.json(
      {
        detail:
          "Backend not configured. In Vercel set BACKEND_URL=https://your-fastapi-host (no trailing slash), then redeploy. Or set NEXT_PUBLIC_API_URL to that same host and redeploy.",
      },
      { status: 502 }
    );
  }

  // Reject looping to our own Vercel host
  try {
    const host = req.headers.get("host") || "";
    const targetHost = new URL(base).host;
    if (host && targetHost === host) {
      return NextResponse.json(
        {
          detail:
            "BACKEND_URL / NEXT_PUBLIC_API_URL points at this Vercel app itself. Set it to your FastAPI server (Railway/Fly/VPS/etc.), not wc-fantasy-fs.vercel.app.",
        },
        { status: 502 }
      );
    }
  } catch {
    /* invalid URL handled below */
  }

  const path = segments.join("/");
  const search = req.nextUrl.search || "";
  const target = `${base}/api/${path}${search}`;

  const headers = new Headers();
  const auth = req.headers.get("authorization");
  if (auth) headers.set("authorization", auth);
  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  const init: RequestInit = {
    method: req.method,
    headers,
    redirect: "manual",
  };

  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.arrayBuffer();
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, init);
  } catch (e) {
    const msg = e instanceof Error ? e.message : "fetch failed";
    return NextResponse.json(
      { detail: `Cannot reach backend at ${base}: ${msg}` },
      { status: 502 }
    );
  }

  // Stream body through (JSON or binary Excel export, etc.)
  const outHeaders = new Headers();
  const pass = ["content-type", "content-disposition", "cache-control"];
  for (const h of pass) {
    const v = upstream.headers.get(h);
    if (v) outHeaders.set(h, v);
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: outHeaders,
  });
}

type Ctx = { params: { path: string[] } };

export async function GET(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path || []);
}
export async function POST(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path || []);
}
export async function PUT(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path || []);
}
export async function PATCH(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path || []);
}
export async function DELETE(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx.params.path || []);
}
