import type { Category } from "@/lib/types";
import { categoryConfig } from "@/lib/categories";

export function CategoryTag({ category }: { category: string }) {
  const cfg = categoryConfig(category);
  return (
    <span className="chip" style={{ backgroundColor: cfg.soft, color: cfg.color }}>
      {cfg.label}
    </span>
  );
}

export { categoryConfig };
