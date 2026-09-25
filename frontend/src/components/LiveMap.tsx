"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import type { EventBrief, Category } from "@/lib/types";
import { getEvents } from "@/lib/api";
import { CATEGORY_CONFIG } from "@/lib/categories";
import { timeAgo } from "@/lib/format";
import { attachStyleFallback, PRIMARY_STYLE_URL } from "@/lib/map";

const CATEGORIES: Category[] = [
  "earthquake",
  "wildfire",
  "volcano",
  "storm",
  "flood",
  "landslide",
  "drought",
  "ice",
  "other",
];

function radiusFor(score: number): number {
  if (score >= 75) return 16;
  if (score >= 50) return 12;
  if (score >= 25) return 8;
  return 5;
}

const SOURCE_ID = "planet-events";

export function LiveMap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const [events, setEvents] = useState<EventBrief[]>([]);
  const [activeCategories, setActiveCategories] = useState<Set<string>>(new Set(CATEGORIES));
  const [minSignificance, setMinSignificance] = useState(0);
  const [hours, setHours] = useState(24);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch events.
  useEffect(() => {
    let mounted = true;
    setLoading(true);
    getEvents({ limit: 500, hours })
      .then((data) => {
        if (!mounted) return;
        setEvents(data);
        setError(null);
      })
      .catch(() => mounted && setError("Unable to load events."))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, [hours]);

  // Init map + layers once.
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: PRIMARY_STYLE_URL,
      center: [10, 20],
      zoom: 1.5,
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), "top-right");
    attachStyleFallback(map);
    mapRef.current = map;

    map.on("load", () => {
      map.addSource(SOURCE_ID, {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });

      CATEGORIES.forEach((cat) => {
        const layerId = `events-${cat}`;
        map.addLayer({
          id: layerId,
          type: "circle",
          source: SOURCE_ID,
          filter: ["==", ["get", "category"], cat],
          paint: {
            "circle-radius": ["get", "radius"],
            "circle-color": CATEGORY_CONFIG[cat].marker,
            "circle-opacity": 0.85,
            "circle-stroke-width": 1.5,
            "circle-stroke-color": "#ffffff",
          },
        });

        map.on("mouseenter", layerId, () => {
          map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", layerId, () => {
          map.getCanvas().style.cursor = "";
        });
        map.on("click", layerId, (e) => {
          const feat = e.features?.[0];
          if (!feat) return;
          const p = feat.properties as Record<string, unknown>;
          const color = CATEGORY_CONFIG[cat].marker;
          const html = `
            <div style="min-width:224px">
              <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px">
                <span style="display:inline-block;width:8px;height:8px;border-radius:99px;background:${color}"></span>
                <span style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;color:#5a636b">${CATEGORY_CONFIG[cat].label}</span>
              </div>
              <p style="font-size:14px;font-weight:600;margin:0 0 2px;color:#14181b">${escapeHtml(String(p.title))}</p>
              <p style="font-size:12px;color:#5a636b;margin:0 0 6px">${escapeHtml(String(p.tier))} · ${Math.round(Number(p.score))} · ${timeAgo(String(p.last))}</p>
              <a href="/events/${p.id}" style="font-size:12px;font-weight:600;color:#0e6ba8;text-decoration:none">View event →</a>
            </div>`;
          new maplibregl.Popup({ offset: 14, closeButton: false })
            .setLngLat(e.lngLat)
            .setHTML(html)
            .addTo(map);
        });
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  const features = useMemo(() => {
    return events
      .filter(
        (e) =>
          e.latitude != null &&
          e.longitude != null &&
          activeCategories.has(e.category) &&
          e.significance_score >= minSignificance,
      )
      .map((e) => ({
        type: "Feature" as const,
        geometry: { type: "Point" as const, coordinates: [e.longitude!, e.latitude!] },
        properties: {
          id: e.id,
          category: e.category,
          title: e.title,
          score: e.significance_score,
          tier: e.significance_tier,
          change: e.change_type,
          last: e.last_observed_at,
          radius: radiusFor(e.significance_score),
        },
      }));
  }, [events, activeCategories, minSignificance]);

  // Update source data when features change.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const source = map.getSource(SOURCE_ID) as maplibregl.GeoJSONSource | undefined;
    if (source) {
      source.setData({ type: "FeatureCollection", features });
    }
  }, [features]);

  function toggleCategory(cat: string) {
    setActiveCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }

  return (
    <div className="card relative overflow-hidden">
      <div className="absolute left-4 top-4 z-10">
        <FilterPanel
          activeCategories={activeCategories}
          onToggle={toggleCategory}
          minSignificance={minSignificance}
          onSignificance={setMinSignificance}
        />
      </div>

      <div className="absolute right-4 top-4 z-10">
        <select
          value={hours}
          onChange={(e) => setHours(Number(e.target.value))}
          className="rounded-lg border border-ink-100 bg-white px-2.5 py-1.5 text-xs font-medium text-ink-700 shadow-soft outline-none"
        >
          <option value={6}>Last 6 hours</option>
          <option value={24}>Last 24 hours</option>
          <option value={72}>Last 3 days</option>
          <option value={168}>Last 7 days</option>
        </select>
      </div>

      {loading && (
        <div className="absolute inset-x-0 top-4 z-10 flex justify-center">
          <span className="rounded-full bg-white px-3 py-1 text-xs text-ink-500 shadow-soft">Loading events…</span>
        </div>
      )}
      {error && (
        <div className="absolute inset-x-0 top-4 z-10 flex justify-center">
          <span className="rounded-full bg-coral/10 px-3 py-1 text-xs text-coral">{error}</span>
        </div>
      )}

      <div ref={containerRef} className="map-wrap h-[520px] w-full sm:h-[560px]" />

      <Legend activeCategories={activeCategories} />
    </div>
  );
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
}

function Legend({ activeCategories }: { activeCategories: Set<string> }) {
  const active = CATEGORIES.filter((c) => activeCategories.has(c));
  return (
    <div className="absolute bottom-4 left-4 z-10 flex max-w-[90%] flex-wrap gap-x-4 gap-y-1.5 rounded-xl border border-ink-100 bg-white/90 px-3 py-2 text-[11px] font-medium text-ink-600 backdrop-blur">
      {active.map((c) => (
        <span key={c} className="inline-flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: CATEGORY_CONFIG[c].marker }} />
          {CATEGORY_CONFIG[c].label}
        </span>
      ))}
    </div>
  );
}

function FilterPanel({
  activeCategories,
  onToggle,
  minSignificance,
  onSignificance,
}: {
  activeCategories: Set<string>;
  onToggle: (c: string) => void;
  minSignificance: number;
  onSignificance: (n: number) => void;
}) {
  return (
    <div className="w-48 rounded-xl border border-ink-100 bg-white/95 p-3 shadow-soft backdrop-blur">
      <p className="eyebrow mb-2">Categories</p>
      <div className="flex flex-col gap-1">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            onClick={() => onToggle(c)}
            className={`flex items-center gap-2 rounded-lg px-2 py-1 text-left text-xs font-medium transition-colors ${
              activeCategories.has(c) ? "text-ink-800" : "text-ink-300"
            }`}
          >
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: activeCategories.has(c) ? CATEGORY_CONFIG[c].marker : "#D6DAD9" }}
            />
            {CATEGORY_CONFIG[c].label}
          </button>
        ))}
      </div>

      <p className="eyebrow mb-1.5 mt-3">Min significance</p>
      <select
        value={minSignificance}
        onChange={(e) => onSignificance(Number(e.target.value))}
        className="w-full rounded-lg border border-ink-100 bg-white px-2 py-1.5 text-xs font-medium text-ink-700 outline-none"
      >
        <option value={0}>All</option>
        <option value={25}>Notable +</option>
        <option value={50}>Significant +</option>
        <option value={75}>Major only</option>
      </select>
    </div>
  );
}
