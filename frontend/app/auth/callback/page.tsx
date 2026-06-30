"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";
import { setToken } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

function CallbackInner() {
  const params = useSearchParams();
  const router = useRouter();
  const { refresh } = useAuth();

  useEffect(() => {
    const token = params.get("token");
    if (token) {
      setToken(token);
      refresh().then(() => router.replace("/"));
    } else {
      router.replace("/login");
    }
  }, [params, router, refresh]);

  return <div className="loading-center">Iniciando sesión…</div>;
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<div className="loading-center">…</div>}>
      <CallbackInner />
    </Suspense>
  );
}
