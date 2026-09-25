export function SourceTag({ source }: { source: string }) {
  const label = source === "usgs" ? "USGS" : source === "eonet" ? "NASA EONET" : source === "firms" ? "NASA FIRMS" : source;
  return (
    <span className="inline-flex items-center rounded-md border border-ink-100 bg-ink-50 px-2 py-0.5 text-[11px] font-medium uppercase tracking-wide text-ink-500">
      {label}
    </span>
  );
}
