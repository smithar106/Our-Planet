"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import type { EventDetail } from "@/lib/types";
import { getEvent } from "@/lib/api";
import { categoryConfig } from "@/lib/categories";
import { formatNumber, formatTime, round, timeAgo } from "@/lib/format";
import { SignificanceBadge } from "@/components/SignificanceBadge";
import { ChangeBadge } from "@/components/ChangeBadge";
import { SourceTag } from "@/components/SourceTag";
import { DetailMap } from "@/components/DetailMap";

export function EventDetailView() {
  const params = useParams<{ id: string }>();
  const [event, setEvent] = useState<EventDetail | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    getEvent(params.id)
      .then((d) => mounted && setEvent(d))
      .catch(() => mounted && setError(true))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, [params.id]);

  if (loading) {
    return <div className="container-page py-16"><Skeleton /></div>;
  }
  if (error || !event) {
    return (
      <div className="container-page py-16">
        <div className="card p-12 text-center text-ink-500">Event not found.</div>
      </div>
    );
  }

  const cfg = categoryConfig(event.category);
  const explanation = event.explanation;

  return (
    <div className="container-page py-10">
      <nav className="mb-6 text-sm text-ink-400">
        <a href="/" className="hover:text-ink-700">Earth</a>
        <span className="mx-2">/</span>
        <span className="text-ink-600">{cfg.label}</span>
      </nav>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="card p-6 sm:p-8">
            <div className="flex flex-wrap items-center gap-2">
              <span className="chip" style={{ backgroundColor: cfg.soft, color: cfg.color }}>
                {cfg.label}
              </span>
              <ChangeBadge change={event.change_type} />
              <SignificanceBadge tier={event.significance_tier} score={event.significance_score} />
            </div>

            <h1 className="mt-5 text-3xl font-semibold leading-tight tracking-tight text-ink-950 sm:text-4xl">
              {event.title}
            </h1>

            <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2 text-sm text-ink-500">
              <span className="inline-flex items-center gap-1.5">
                <SourceTag source={event.source} />
              </span>
              <span>{formatTime(event.last_observed_at)}</span>
              <span>{timeAgo(event.last_observed_at)}</span>
              {event.latitude != null && event.longitude != null && (
                <span>{event.latitude.toFixed(2)}°, {event.longitude.toFixed(2)}°</span>
              )}
              {event.status === "closed" && <span className="font-medium text-ink-400">Closed</span>}
            </div>

            <DetailMap event={event} />

            {/* Metrics */}
            <MetricsGrid event={event} />
          </div>

          {/* Why flagged */}
          <div className="card mt-6 p-6 sm:p-8">
            <p className="eyebrow">Agent investigation</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink-950">
              Why PLANET flagged this
            </h2>
            {explanation?.deterministic && (
              <p className="mt-3 rounded-lg bg-ink-50 px-3 py-2 text-xs text-ink-500">
                Deterministic summary (agent unavailable or validation failed).
              </p>
            )}
            <p className="mt-4 text-base leading-relaxed text-ink-700">
              {explanation?.summary || "No explanation available yet."}
            </p>

            {explanation?.why_notable && explanation.why_notable.length > 0 && (
              <div className="mt-5">
                <p className="text-sm font-semibold text-ink-950">Why it&apos;s notable</p>
                <ul className="mt-2 space-y-2">
                  {explanation.why_notable.map((w, i) => (
                    <li key={i} className="flex gap-2 text-sm leading-relaxed text-ink-600">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-ocean" />
                      {w}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {explanation?.watch_next && explanation.watch_next.length > 0 && (
              <div className="mt-5">
                <p className="text-sm font-semibold text-ink-950">What PLANET is watching next</p>
                <ul className="mt-2 space-y-2">
                  {explanation.watch_next.map((w, i) => (
                    <li key={i} className="flex gap-2 text-sm leading-relaxed text-ink-600">
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-earth" />
                      {w}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Source references */}
          <div className="card mt-6 p-6 sm:p-8">
            <p className="eyebrow">Source references</p>
            <h2 className="mt-2 text-xl font-semibold tracking-tight text-ink-950">Attribution</h2>
            <ul className="mt-4 space-y-3">
              {explanation?.source_claims && explanation.source_claims.length > 0 ? (
                explanation.source_claims.map((c, i) => (
                  <li key={i} className="flex items-start justify-between gap-4 text-sm">
                    <span className="text-ink-600">{c.claim}</span>
                    {c.url ? (
                      <a
                        href={c.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="shrink-0 font-medium text-ocean hover:underline"
                      >
                        {c.source} ↗
                      </a>
                    ) : (
                      <span className="shrink-0 text-ink-400">{c.source}</span>
                    )}
                  </li>
                ))
              ) : event.source_url ? (
                <li className="flex items-start justify-between gap-4 text-sm">
                  <span className="text-ink-600">Official source record</span>
                  <a
                    href={event.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="shrink-0 font-medium text-ocean hover:underline"
                  >
                    {event.source.toUpperCase()} ↗
                  </a>
                </li>
              ) : (
                <li className="text-sm text-ink-400">No external source URL available.</li>
              )}
            </ul>
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          <div className="card p-6">
            <p className="eyebrow">Significance</p>
            <div className="mt-4 flex items-end gap-2">
              <span className="text-5xl font-semibold tracking-tight text-ink-950">
                {formatNumber(Math.round(event.significance_score))}
              </span>
              <span className="mb-1 text-sm text-ink-400">/ 100</span>
            </div>
            <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-ink-100">
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.min(100, event.significance_score)}%`,
                  backgroundColor: cfg.marker,
                }}
              />
            </div>
            <p className="mt-4 text-xs leading-relaxed text-ink-400">
              PLANET significance is an application-level prioritization score and
              is not an official hazard classification.
            </p>
          </div>

          <div className="card p-6">
            <p className="eyebrow">Change history</p>
            <ol className="mt-4 space-y-4">
              {event.change_history.length === 0 && (
                <p className="text-sm text-ink-400">No change history recorded.</p>
              )}
              {event.change_history.slice(0, 10).map((s, i) => (
                <li key={i} className="relative flex gap-3">
                  {i !== event.change_history.length - 1 && (
                    <span className="absolute left-1 top-4 h-full w-px bg-ink-100" />
                  )}
                  <span className="relative mt-1 h-2 w-2 shrink-0 rounded-full bg-ocean" />
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <ChangeBadge change={s.change_type} />
                      <span className="text-xs text-ink-400">{formatTime(s.at)}</span>
                    </div>
                    <p className="mt-0.5 text-xs text-ink-500">
                      Score {formatNumber(Math.round(s.score))} · {s.tier.toLowerCase()}
                    </p>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <div className="card p-6 text-sm text-ink-500">
            <p className="eyebrow mb-2">Last updated</p>
            <p>{formatTime(event.updated_at)}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricsGrid({ event }: { event: EventDetail }) {
  const metrics = event.metrics ?? {};
  const entries = Object.entries(metrics).filter(
    ([, v]) => typeof v === "number" || typeof v === "string",
  ) as [string, string | number][];
  if (entries.length === 0) return null;
  return (
    <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3">
      {entries.slice(0, 9).map(([k, v]) => (
        <div key={k} className="rounded-xl border border-ink-100 bg-ink-50/50 px-4 py-3">
          <p className="text-xs font-medium text-ink-400">{labelFor(k)}</p>
          <p className="mt-1 text-lg font-semibold text-ink-950">
            {typeof v === "number" ? formatNumber(v) : v}
          </p>
        </div>
      ))}
    </div>
  );
}

function labelFor(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function Skeleton() {
  return (
    <div className="grid gap-8 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <div className="card h-96 animate-pulse bg-ink-50" />
      </div>
      <div className="card h-64 animate-pulse bg-ink-50" />
    </div>
  );
}
