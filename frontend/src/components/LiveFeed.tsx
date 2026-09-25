"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { EventBrief } from "@/lib/types";
import { getRecentEvents } from "@/lib/api";
import { categoryConfig } from "@/lib/categories";
import { formatTime, timeAgo } from "@/lib/format";
import { ChangeBadge } from "./ChangeBadge";
import { SourceTag } from "./SourceTag";

export function LiveFeed() {
  const [events, setEvents] = useState<EventBrief[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    getRecentEvents(60)
      .then((d) => mounted && setEvents(d))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <section id="feed" className="container-page py-20">
      <div className="mb-10 max-w-2xl">
        <p className="eyebrow">Live Earth feed</p>
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-ink-950 sm:text-4xl">
          The stream of what changed
        </h2>
        <p className="mt-3 text-base leading-relaxed text-ink-500">
          A chronological record of state transitions — new events, updates, and
          escalations — generated directly from the pipeline.
        </p>
      </div>

      {loading ? (
        <div className="card divide-y divide-ink-50">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex h-16 animate-pulse items-center gap-4 px-6">
              <div className="h-2 w-16 rounded bg-ink-100" />
              <div className="h-2 flex-1 rounded bg-ink-100" />
            </div>
          ))}
        </div>
      ) : events.length === 0 ? (
        <div className="card p-12 text-center text-ink-500">No events yet.</div>
      ) : (
        <div className="card divide-y divide-ink-50">
          {events.slice(0, 30).map((event) => {
            const cfg = categoryConfig(event.category);
            return (
              <Link
                key={event.id}
                href={`/events/${event.id}`}
                className="flex items-center gap-4 px-5 py-3.5 transition-colors hover:bg-ink-50/60 sm:px-6"
              >
                <span className="w-[68px] shrink-0 font-mono text-[11px] text-ink-400">
                  {formatTime(event.last_observed_at)}
                </span>
                <ChangeBadge change={event.change_type} />
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: cfg.marker }}
                />
                <span className="min-w-0 flex-1 truncate text-sm font-medium text-ink-800">
                  {event.title}
                </span>
                <span className="hidden shrink-0 sm:block">
                  <SourceTag source={event.source} />
                </span>
                <span className="hidden shrink-0 text-xs text-ink-400 md:block">
                  {timeAgo(event.last_observed_at)}
                </span>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}
