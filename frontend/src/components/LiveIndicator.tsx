"use client";

import { useEffect, useState } from "react";
import { getStatus } from "@/lib/api";

export function LiveIndicator({ className }: { className?: string }) {
  const [live, setLive] = useState<boolean | null>(null);
  const [updated, setUpdated] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      try {
        const status = await getStatus();
        if (!mounted) return;
        const healthy = status.pipeline !== "failed";
        setLive(healthy);
        const last = status.providers
          .map((p) => p.last_successful_fetch)
          .filter(Boolean)
          .sort()
          .pop();
        setUpdated(last ?? null);
      } catch {
        if (mounted) setLive(false);
      }
    }
    load();
    const id = setInterval(load, 60_000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <span className={`inline-flex items-center gap-2 text-xs text-ink-500 ${className ?? ""}`}>
      <span className="relative flex h-2 w-2">
        <span
          className={`absolute inline-flex h-full w-full rounded-full ${
            live === false ? "bg-coral" : "bg-earth"
          } opacity-60 animate-ping`}
        />
        <span
          className={`relative inline-flex h-2 w-2 rounded-full ${
            live === false ? "bg-coral" : "bg-earth"
          }`}
        />
      </span>
      <span>
        {live === null ? "Connecting…" : live ? "Live" : "Degraded"}
        {updated ? ` · updated ${updated}` : ""}
      </span>
    </span>
  );
}
