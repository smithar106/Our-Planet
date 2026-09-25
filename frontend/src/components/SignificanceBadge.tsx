import type { SignificanceTier } from "@/lib/types";
import { TIER_CONFIG } from "@/lib/categories";

export function SignificanceBadge({ tier, score }: { tier: SignificanceTier; score: number }) {
  const cfg = TIER_CONFIG[tier];
  return (
    <span
      className="chip"
      style={{ backgroundColor: cfg.soft, color: cfg.color }}
      title="PLANET application-level prioritization score (not an official hazard classification)"
    >
      <span className="font-semibold">{cfg.label}</span>
      <span className="opacity-70">· {Math.round(score)}</span>
    </span>
  );
}
