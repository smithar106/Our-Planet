"use client";

import { useEffect, useState } from "react";
import type { SystemStatus } from "@/lib/types";
import { getStatus } from "@/lib/api";
import { formatTime } from "@/lib/format";

export default function StatusPage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let mounted = true;
    getStatus()
      .then((s) => mounted && setStatus(s))
      .catch(() => mounted && setError(true));
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="container-page py-16">
      <div className="max-w-3xl">
        <p className="eyebrow">System status</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-ink-950 sm:text-5xl">
          Pipeline health
        </h1>
        <p className="mt-4 text-lg text-ink-500">
          Real, measured state of the ingestion pipeline, providers, and agent.
        </p>
      </div>

      {error ? (
        <div className="card mt-8 p-12 text-center text-ink-500">Unable to load status.</div>
      ) : !status ? (
        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="card h-28 animate-pulse bg-ink-50" />
          ))}
        </div>
      ) : (
        <>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <HealthCard label="Pipeline" value={status.pipeline} />
            <HealthCard label="Agent" value={status.agent} />
            <HealthCard
              label="LLM"
              value={status.llm_configured ? "configured" : "disabled"}
            />
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Stat label="Events processed" value={String(status.events_processed)} />
            <Stat label="Selected for investigation" value={String(status.events_selected_for_investigation)} />
            <Stat label="Investigations completed" value={String(status.investigations_completed)} />
            <Stat label="Fallbacks" value={String(status.fallbacks)} />
          </div>

          <div className="card mt-8 overflow-hidden">
            <div className="border-b border-ink-100 px-6 py-4">
              <h2 className="text-lg font-semibold text-ink-950">Providers</h2>
            </div>
            <div className="divide-y divide-ink-50">
              {status.providers.length === 0 && (
                <p className="px-6 py-8 text-sm text-ink-400">No provider runs recorded yet.</p>
              )}
              {status.providers.map((p) => (
                <div key={p.provider} className="flex flex-wrap items-center gap-x-6 gap-y-2 px-6 py-4">
                  <span className="w-24 font-medium uppercase tracking-wide text-ink-700">
                    {p.provider}
                  </span>
                  <span
                    className={`chip ${
                      p.status === "succeeded"
                        ? "bg-earth-100 text-earth-600"
                        : "bg-coral/10 text-coral"
                    }`}
                  >
                    {p.status}
                  </span>
                  <span className="text-sm text-ink-500">
                    {p.last_successful_fetch
                      ? `Last fetch ${formatTime(p.last_successful_fetch)}`
                      : "No successful fetch yet"}
                  </span>
                  <span className="text-sm text-ink-400">
                    {p.records_last_fetch} records
                  </span>
                  {p.last_error && (
                    <span className="truncate text-sm text-coral">{p.last_error}</span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {status.last_pipeline_duration_ms != null && (
            <p className="mt-6 text-sm text-ink-400">
              Last pipeline duration: {(status.last_pipeline_duration_ms / 1000).toFixed(2)}s
            </p>
          )}
        </>
      )}
    </div>
  );
}

function HealthCard({ label, value }: { label: string; value: string }) {
  const tone =
    value === "healthy" || value === "configured"
      ? "bg-earth-100 text-earth-600"
      : value === "degraded" || value === "disabled"
        ? "bg-amber/15 text-amber"
        : "bg-coral/10 text-coral";
  return (
    <div className="card p-6">
      <p className="eyebrow">{label}</p>
      <div className="mt-3 flex items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${value === "healthy" || value === "configured" ? "bg-earth" : "bg-coral"}`} />
        <span className="text-xl font-semibold text-ink-950">{value}</span>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="card p-6">
      <p className="text-3xl font-semibold tracking-tight text-ink-950">{value}</p>
      <p className="mt-1 text-xs font-medium text-ink-500">{label}</p>
    </div>
  );
}
