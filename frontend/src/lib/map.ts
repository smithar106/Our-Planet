import type maplibregl from "maplibre-gl";

export const MAPBOX_TOKEN = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;

export const FALLBACK_STYLE_URL = "https://tiles.openfreemap.org/styles/liberty";

export const MAPBOX_STYLE_URL = MAPBOX_TOKEN
  ? `https://api.mapbox.com/styles/v1/mapbox/light-v11?access_token=${MAPBOX_TOKEN}`
  : FALLBACK_STYLE_URL;

export const PRIMARY_STYLE_URL = MAPBOX_TOKEN ? MAPBOX_STYLE_URL : FALLBACK_STYLE_URL;

/** If the Mapbox style fails (invalid/expired token, network), fall back to a
 * free, MapLibre-native style so the map always renders something useful. */
export function attachStyleFallback(map: maplibregl.Map): void {
  if (!MAPBOX_TOKEN) return;
  let fellBack = false;
  map.on("error", (e) => {
    if (fellBack) return;
    const err = e?.error as { status?: number; message?: string } | undefined;
    const isAuth = err?.status === 401 || err?.status === 403;
    const isFetch = /failed to fetch|network/i.test(err?.message ?? "");
    if (isAuth || isFetch) {
      fellBack = true;
      map.setStyle(FALLBACK_STYLE_URL);
    }
  });
}
