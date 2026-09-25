"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import type { EventDetail } from "@/lib/types";
import { categoryConfig } from "@/lib/categories";

const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
const STYLE_URL = MAPBOX_TOKEN
  ? `https://api.mapbox.com/styles/v1/mapbox/light-v11?access_token=${MAPBOX_TOKEN}`
  : "https://tiles.openfreemap.org/styles/liberty";

export function DetailMap({ event }: { event: EventDetail }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const cfg = categoryConfig(event.category);

  const hasPoint = event.latitude != null && event.longitude != null;

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const center: [number, number] = hasPoint
      ? [event.longitude!, event.latitude!]
      : [0, 0];
    const zoom = hasPoint ? 6 : 1;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE_URL,
      center,
      zoom,
      attributionControl: { compact: true },
    });

    if (hasPoint) {
      map.on("load", () => {
        map.addSource("event-point", {
          type: "geojson",
          data: {
            type: "Feature",
            geometry: { type: "Point", coordinates: center },
            properties: {},
          },
        });
        map.addLayer({
          id: "event-marker",
          type: "circle",
          source: "event-point",
          paint: {
            "circle-radius": 14,
            "circle-color": cfg.marker,
            "circle-opacity": 0.9,
            "circle-stroke-width": 3,
            "circle-stroke-color": "#ffffff",
          },
        });
      });
    }

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event.id]);

  return (
    <div className="mt-6 overflow-hidden rounded-xl border border-ink-100">
      <div ref={containerRef} className="map-wrap h-[320px] w-full" />
      {!hasPoint && (
        <div className="border-t border-ink-100 bg-ink-50 px-4 py-2 text-xs text-ink-400">
          No precise coordinates available for this event.
        </div>
      )}
    </div>
  );
}
