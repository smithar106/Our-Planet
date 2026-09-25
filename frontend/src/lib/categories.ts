import type { Category, ChangeType, SignificanceTier } from "./types";

interface CategoryConfig {
  label: string;
  color: string;
  soft: string;
  marker: string;
}

export const CATEGORY_CONFIG: Record<Category, CategoryConfig> = {
  earthquake: {
    label: "Earthquake",
    color: "#C7782A",
    soft: "#F6E6D3",
    marker: "#C7782A",
  },
  wildfire: {
    label: "Wildfire",
    color: "#D95D45",
    soft: "#FBE4DE",
    marker: "#D95D45",
  },
  volcano: {
    label: "Volcano",
    color: "#A63A3A",
    soft: "#F3DCDC",
    marker: "#A63A3A",
  },
  storm: {
    label: "Storm",
    color: "#2E6FB7",
    soft: "#DCE8F5",
    marker: "#2E6FB7",
  },
  flood: {
    label: "Flood",
    color: "#2E8FC9",
    soft: "#DCEFFA",
    marker: "#2E8FC9",
  },
  landslide: {
    label: "Landslide",
    color: "#9A6A3B",
    soft: "#EFE3D3",
    marker: "#9A6A3B",
  },
  drought: {
    label: "Drought",
    color: "#C7A23A",
    soft: "#F5EDD6",
    marker: "#C7A23A",
  },
  ice: {
    label: "Ice",
    color: "#5A93B5",
    soft: "#DDEAF2",
    marker: "#5A93B5",
  },
  other: {
    label: "Other",
    color: "#6B7280",
    soft: "#E7E9EC",
    marker: "#6B7280",
  },
};

export function categoryConfig(category: string): CategoryConfig {
  return CATEGORY_CONFIG[category as Category] ?? CATEGORY_CONFIG.other;
}

export const TIER_CONFIG: Record<SignificanceTier, { label: string; color: string; soft: string }> = {
  MAJOR: { label: "Major", color: "#B33A2E", soft: "#FBE3DF" },
  SIGNIFICANT: { label: "Significant", color: "#C7782A", soft: "#F6E6D3" },
  NOTABLE: { label: "Notable", color: "#2E6FB7", soft: "#DCE8F5" },
  ROUTINE: { label: "Routine", color: "#6B7280", soft: "#E7E9EC" },
};

export const CHANGE_CONFIG: Record<ChangeType, { label: string; color: string; soft: string }> = {
  NEW: { label: "New", color: "#2F7D5B", soft: "#D9EFE4" },
  UPDATED: { label: "Updated", color: "#2E6FB7", soft: "#DCE8F5" },
  ESCALATING: { label: "Escalating", color: "#B33A2E", soft: "#FBE3DF" },
  "DE-ESCALATING": { label: "De-escalating", color: "#2E8FC9", soft: "#DCEFFA" },
  UNCHANGED: { label: "Unchanged", color: "#6B7280", soft: "#E7E9EC" },
  CLOSED: { label: "Closed", color: "#5A636B", soft: "#E4E7EA" },
};
