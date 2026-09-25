"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import type { Brief } from "@/lib/types";
import { getLatestBrief } from "@/lib/api";
import { categoryConfig } from "@/lib/categories";
import { ChangeBadge } from "@/components/ChangeBadge";
import { SignificanceBadge } from "@/components/SignificanceBadge";
import { SourceTag } from "@/components/SourceTag";

export function BriefView() {
  const [brief, setBrief] = useState<Brief | null>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    getLatestBrief()
      .then((b) => mounted && setBrief(b))
      .catch(() => mounted && setError(true))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="container-page py-16">
      <p className="eyebrow">Daily Earth Brief</p>
      <h1 className="mt-3 text-4xl font-semibold tracking-tight text-ink-950 sm:text-5xl">
        {brief?.title || "Daily Earth Brief"}
      </h1>

      {loading ? (
        <div className="mt-8 card h-40 animate-pulse bg-ink-50" />
      ) : error || !brief ? (
        <div className="card mt-8 p-12 text-center text-ink-500">
          No brief available yet — it is generated once per day after the first
          successful ingestion.
        </div>
      ) : (
        <div className="mt-8 grid gap-8 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <p className="max-w-2xl text-lg leading-relaxed text-ink-700">{brief.intro}</p>

            <Section title="Most significant" items={brief.most_significant} />
            <Section title="New developments" items={brief.new_developments} />
            <Section title="Escalating" items={brief.escalating} />
          </div>

          <div className="space-y-6">
            <div className="card p-6">
              <p className="eyebrow">By category</p>
              <ul className="mt-4 space-y-2">
                {Object.entries(brief.by_category).length === 0 && (
                  <li className="text-sm text-ink-400">No events in the window.</li>
                )}
                {Object.entries(brief.by_category)
                  .sort((a, b) => b[1] - a[1])
                  .map(([cat, count]) => {
                    const cfg = categoryConfig(cat);
                    return (
                      <li key={cat} className="flex items-center justify-between text-sm">
                        <span className="inline-flex items-center gap-2 text-ink-600">
                          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: cfg.marker }} />
                          {cfg.label}
                        </span>
                        <span className="font-semibold text-ink-950">{count}</span>
                      </li>
                    );
                  })}
              </ul>
            </div>

            <div className="card p-6">
              <p className="eyebrow">What PLANET is watching</p>
              <ul className="mt-4 space-y-2">
                {brief.watching.length === 0 && <li className="text-sm text-ink-400">Nothing flagged.</li>}
                {brief.watching.map((w) => (
                  <li key={w} className="flex gap-2 text-sm text-ink-600">
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-ocean" />
                    {categoryConfig(w).label}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Section({ title, items }: { title: string; items: Brief["most_significant"] }) {
  if (items.length === 0) return null;
  return (
    <div className="mt-10">
      <h2 className="text-xl font-semibold tracking-tight text-ink-950">{title}</h2>
      <div className="mt-4 space-y-3">
        {items.map((e) => {
          const cfg = categoryConfig(e.category);
          return (
            <Link key={e.id} href={`/events/${e.id}`} className="card flex items-center gap-4 p-4 transition-all hover:shadow-lift">
              <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: cfg.marker }} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-ink-900">{e.title}</p>
                <div className="mt-1 flex items-center gap-2 text-xs text-ink-400">
                  <SourceTag source={e.source} />
                  <ChangeBadge change={e.change_type} />
                </div>
              </div>
              <SignificanceBadge tier={e.significance_tier} score={e.significance_score} />
            </Link>
          );
        })}
      </div>
    </div>
  );
}
