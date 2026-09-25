export type ChangeType =
  | "NEW"
  | "UPDATED"
  | "ESCALATING"
  | "DE-ESCALATING"
  | "UNCHANGED"
  | "CLOSED";

export type SignificanceTier = "ROUTINE" | "NOTABLE" | "SIGNIFICANT" | "MAJOR";

export type Category =
  | "earthquake"
  | "wildfire"
  | "volcano"
  | "storm"
  | "flood"
  | "landslide"
  | "drought"
  | "ice"
  | "other";

export interface EventBrief {
  id: string;
  source: string;
  source_id: string;
  category: Category;
  subtype: string | null;
  title: string;
  latitude: number | null;
  longitude: number | null;
  status: string;
  significance_score: number;
  significance_tier: SignificanceTier;
  change_type: ChangeType;
  first_observed_at: string;
  last_observed_at: string;
  source_url: string | null;
}

export interface SourceClaim {
  source: string;
  url: string | null;
  claim: string;
}

export interface Explanation {
  status: string;
  headline: string | null;
  summary: string | null;
  why_notable: string[];
  watch_next: string[];
  source_claims: SourceClaim[];
  grounded: boolean;
  deterministic?: boolean;
}

export interface ChangeSnapshot {
  at: string;
  score: number;
  tier: SignificanceTier;
  change_type: ChangeType;
  status: string;
}

export interface EventDetail extends EventBrief {
  geometry: unknown;
  raw_severity: Record<string, unknown> | null;
  confidence: number;
  metrics: Record<string, unknown>;
  explanation: Explanation;
  change_history: ChangeSnapshot[];
  updated_at: string;
}

export interface Summary {
  generated_at: string;
  last_24h: {
    total_events: number;
    earthquakes: number;
    fire_clusters: number;
    other_active: number;
    significant: number;
    new: number;
    escalating: number;
  };
  most_significant: EventBrief[];
  escalating: EventBrief[];
}

export interface ProviderStatus {
  provider: string;
  last_successful_fetch: string | null;
  status: string;
  last_error: string | null;
  records_last_fetch: number;
}

export interface SystemStatus {
  pipeline: string;
  agent: string;
  last_pipeline_duration_ms: number | null;
  events_processed: number;
  events_selected_for_investigation: number;
  investigations_completed: number;
  fallbacks: number;
  providers: ProviderStatus[];
  llm_configured: boolean;
}

export interface Brief {
  brief_date: string;
  title: string;
  intro: string;
  most_significant: EventBrief[];
  new_developments: EventBrief[];
  escalating: EventBrief[];
  by_category: Record<string, number>;
  watching: string[];
  generated_at: string;
}
