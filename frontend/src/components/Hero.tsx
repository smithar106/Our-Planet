"use client";

import { useEffect, useState } from "react";
import { getStatus } from "@/lib/api";
import { timeAgo } from "@/lib/format";

export function Hero() {
  const [updated, setUpdated] = useState<string | null>(null);
  const [sourcesOnline, setSourcesOnline] = useState<number>(0);

  useEffect(() => {
    let mounted = true;
    getStatus()
      .then((s) => {
        if (!mounted) return;
        const online = s.providers.filter((p) => p.status === "succeeded").length;
        setSourcesOnline(online);
        const last = s.providers.map((p) => p.last_successful_fetch).filter(Boolean).sort().pop();
        setUpdated(last ?? null);
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <section className="relative overflow-hidden border-b border-ink-100 bg-gradient-to-b from-white to-paper">
      <div
        className="pointer-events-none absolute inset-0 opacity-60"
        style={{
          background:
            "radial-gradient(60% 60% at 20% 0%, rgba(46,143,201,0.10), transparent 60%), radial-gradient(50% 50% at 85% 10%, rgba(47,125,91,0.08), transparent 60%)",
        }}
      />
      <div className="container-page relative py-16 sm:pt-24 sm:pb-12">
        <div className="mx-auto max-w-3xl text-center">
          <div className="inline-flex items-center gap-2 rounded-full border border-ink-100 bg-white px-3 py-1 text-xs font-medium text-ink-600 shadow-soft">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full rounded-full bg-earth opacity-60 animate-ping" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-earth" />
            </span>
            Live Earth Intelligence
          </div>

          <h1 className="mt-6 font-display text-5xl font-normal leading-[1.05] tracking-tight text-ink-950 sm:text-7xl">
            PLANET
          </h1>

          <p className="mx-auto mt-5 max-w-xl text-xl font-medium leading-relaxed text-ink-700 sm:text-2xl">
            An AI agent watching Earth.
          </p>

          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-ink-500">
            PLANET continuously monitors trusted global data to detect, investigate,
            and explain significant events as they happen.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-ink-500">
            <span className="inline-flex items-center gap-2">
              <Dot live />
              {updated ? `Last updated ${timeAgo(updated)}` : "Awaiting first ingestion"}
            </span>
            <span className="inline-flex items-center gap-2">
              <Dot live={false} />
              {sourcesOnline}/3 sources online
            </span>
            <span className="inline-flex items-center gap-1.5">
              <SourceMini>USGS</SourceMini>
              <SourceMini>NASA EONET</SourceMini>
              <SourceMini>NASA FIRMS</SourceMini>
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

function Dot({ live }: { live: boolean }) {
  return <span className={`h-2 w-2 rounded-full ${live ? "bg-earth" : "bg-ink-300"}`} />;
}

function SourceMini({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-md border border-ink-100 bg-white px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-ink-500">
      {children}
    </span>
  );
}
