import type {
  Brief,
  EventBrief,
  EventDetail,
  Summary,
  SystemStatus,
} from "./types";

const BASE = "/api";

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    signal,
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`API ${res.status} for ${path}`);
  }
  return res.json() as Promise<T>;
}

export function getEvents(params?: {
  category?: string;
  significance?: string;
  hours?: number;
  limit?: number;
}): Promise<EventBrief[]> {
  const q = new URLSearchParams();
  if (params?.category) q.set("category", params.category);
  if (params?.significance) q.set("significance", params.significance);
  if (params?.hours) q.set("hours", String(params.hours));
  if (params?.limit) q.set("limit", String(params.limit));
  const qs = q.toString();
  return get<EventBrief[]>(`/events${qs ? `?${qs}` : ""}`);
}

export function getSignificantEvents(limit = 12): Promise<EventBrief[]> {
  return get<EventBrief[]>(`/events/significant?limit=${limit}`);
}

export function getRecentEvents(limit = 40): Promise<EventBrief[]> {
  return get<EventBrief[]>(`/events/recent?limit=${limit}`);
}

export function getEvent(id: string): Promise<EventDetail> {
  return get<EventDetail>(`/events/${id}`);
}

export function getSummary(): Promise<Summary> {
  return get<Summary>("/summary");
}

export function getStatus(): Promise<SystemStatus> {
  return get<SystemStatus>("/status");
}

export function getLatestBrief(): Promise<Brief> {
  return get<Brief>("/brief/latest");
}

export function getBrief(date: string): Promise<Brief> {
  return get<Brief>(`/brief/${date}`);
}
