"use client";

import { useEffect, useState } from "react";
import type { Summary } from "@/lib/types";
import { getSummary } from "@/lib/api";

const STATS: { key: keyof Summary["last_24h"]; label: string }[] = [
  { key: "total_events", label: "Total events" },
  { key: "earthquakes", label: "Earthquakes" },
  { key: "fire_clusters", label: "Fire clusters" },
  { key: "other_active", label: "Other active" },
  { key: "significant", label: "Significant events" },
  { key: "new", label: "New events" },
  { key: "escalating", label: "Escalating" },
];

export function GlobalSnapshot() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let mounted = true;
    getSummary()
      .then((s) => mounted && setSummary(s))
      .catch(() => mounted && setError(true));
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <section className="container-page py-20">
      <div className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-ink-100 px-6 py-4 sm:px-8">
          <div>
            <p className="eyebrow">Global snapshot</p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight text-ink-950">Last 24 hours</h2>
          </div>
          <span className="hidden text-xs text-ink-400 sm:block">Computed deterministically, not by AI</span>
        </div>

        {error ? (
          <div className="px-8 py-10 text-ink-500">Unable to load snapshot.</div>
        ) : !summary ? (
          <div className="grid grid-cols-2 gap-px bg-ink-100 sm:grid-cols-4 lg:grid-cols-7">
            {Array.from({ length: 7 }).map((_, i) => (
              <div key={i} className="h-28 animate-pulse bg-white" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-px bg-ink-100 sm:grid-cols-4 lg:grid-cols-7">
            {STATS.map(({ key, label }) => (
              <div key={key} className="bg-white px-5 py-6">
                <p className="text-3xl font-semibold tracking-tight text-ink-950">
                  {summary.last_24h[key] ?? 0}
                </p>
                <p className="mt-1 text-xs font-medium text-ink-500">{label}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
