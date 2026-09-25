import type maplibregl from "maplibre-gl";

// Free, MapLibre-native basemap — no API key, no custom protocol handler.
// Reliable and light, matching the bright Earth-intelligence aesthetic.
// (Mapbox styles require a token + MapLibre's mapbox:// protocol and are
// notoriously flaky, so we avoid them.)
export const PRIMARY_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

export const FALLBACK_STYLE_URL = PRIMARY_STYLE_URL;

export function attachStyleFallback(_map: maplibregl.Map): void {
  // No-op: OpenFreeMap is the only style and requires no fallback.
}
