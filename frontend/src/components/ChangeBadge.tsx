import type { ChangeType } from "@/lib/types";
import { CHANGE_CONFIG } from "@/lib/categories";

export function ChangeBadge({ change }: { change: ChangeType }) {
  const cfg = CHANGE_CONFIG[change] ?? CHANGE_CONFIG.UPDATED;
  return (
    <span className="chip" style={{ backgroundColor: cfg.soft, color: cfg.color }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: cfg.color }} />
      {cfg.label}
    </span>
  );
}
