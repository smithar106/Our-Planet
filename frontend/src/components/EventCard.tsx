import Link from "next/link";
import type { EventBrief } from "@/lib/types";
import { categoryConfig } from "@/lib/categories";
import { timeAgo } from "@/lib/format";
import { SignificanceBadge } from "./SignificanceBadge";
import { ChangeBadge } from "./ChangeBadge";
import { SourceTag } from "./SourceTag";

export function EventCard({ event }: { event: EventBrief }) {
  const cfg = categoryConfig(event.category);
  return (
    <Link
      href={`/events/${event.id}`}
      className="group card block p-5 transition-all hover:-translate-y-0.5 hover:shadow-lift"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <span
            className="h-2.5 w-2.5 shrink-0 rounded-full"
            style={{ backgroundColor: cfg.marker }}
          />
          <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: cfg.color }}>
            {cfg.label}
          </span>
        </div>
        <ChangeBadge change={event.change_type} />
      </div>

      <h3 className="mt-3 text-[17px] font-semibold leading-snug tracking-tight text-ink-950 group-hover:text-ocean">
        {event.title}
      </h3>

      <div className="mt-3 flex items-center gap-2 text-xs text-ink-500">
        <SourceTag source={event.source} />
        <span>·</span>
        <span>{timeAgo(event.last_observed_at)}</span>
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-ink-50 pt-3">
        <SignificanceBadge tier={event.significance_tier} score={event.significance_score} />
        <span className="text-xs text-ink-400">
          {event.latitude != null && event.longitude != null
            ? `${event.latitude.toFixed(1)}°, ${event.longitude.toFixed(1)}°`
            : "—"}
        </span>
      </div>
    </Link>
  );
}
