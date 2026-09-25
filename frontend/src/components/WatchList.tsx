"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { EventBrief } from "@/lib/types";
import { getSignificantEvents } from "@/lib/api";
import { categoryConfig } from "@/lib/categories";
import { timeAgo } from "@/lib/format";
import { SignificanceBadge } from "./SignificanceBadge";
import { ChangeBadge } from "./ChangeBadge";
import { SourceTag } from "./SourceTag";

export function WatchList() {
  const [events, setEvents] = useState<EventBrief[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    getSignificantEvents(9)
      .then((d) => mounted && setEvents(d))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <section id="watching" className="container-page py-20">
      <SectionHeading
        eyebrow="What Planet is watching"
        title="Events that deserve attention"
        blurb="The highest-priority events from the last 24 hours, ranked by PLANET's deterministic significance score."
      />

      {loading ? (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="card h-48 animate-pulse bg-ink-50" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <EmptyState message="No significant events in the last 24 hours." />
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {events.map((event) => (
            <WatchCard key={event.id} event={event} />
          ))}
        </div>
      )}
    </section>
  );
}

function WatchCard({ event }: { event: EventBrief }) {
  const cfg = categoryConfig(event.category);
  return (
    <Link
      href={`/events/${event.id}`}
      className="card group flex flex-col p-6 transition-all hover:-translate-y-0.5 hover:shadow-lift"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: cfg.marker }} />
          <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: cfg.color }}>
            {cfg.label}
          </span>
        </div>
        <ChangeBadge change={event.change_type} />
      </div>

      <h3 className="mt-4 text-xl font-semibold leading-snug tracking-tight text-ink-950 group-hover:text-ocean">
        {event.title}
      </h3>

      <p className="mt-2 text-sm text-ink-500">
        {event.latitude != null && event.longitude != null
          ? `${event.latitude.toFixed(1)}°N/S, ${event.longitude.toFixed(1)}°E/W`
          : "Location unavailable"}
      </p>

      <div className="mt-auto pt-5">
        <div className="flex items-center justify-between text-xs text-ink-500">
          <SourceTag source={event.source} />
          <span>{timeAgo(event.last_observed_at)}</span>
        </div>
        <div className="mt-3 flex items-center justify-between border-t border-ink-50 pt-3">
          <SignificanceBadge tier={event.significance_tier} score={event.significance_score} />
          <span className="text-xs font-medium text-ocean group-hover:underline">Why flagged →</span>
        </div>
      </div>
    </Link>
  );
}

export function SectionHeading({
  eyebrow,
  title,
  blurb,
}: {
  eyebrow: string;
  title: string;
  blurb?: string;
}) {
  return (
    <div className="mb-10 max-w-2xl">
      <p className="eyebrow">{eyebrow}</p>
      <h2 className="mt-3 text-3xl font-semibold tracking-tight text-ink-950 sm:text-4xl">{title}</h2>
      {blurb && <p className="mt-3 text-base leading-relaxed text-ink-500">{blurb}</p>}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="card flex flex-col items-center justify-center gap-2 p-12 text-center">
      <p className="text-ink-500">{message}</p>
    </div>
  );
}
