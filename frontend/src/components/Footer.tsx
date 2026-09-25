import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-24 border-t border-ink-100 bg-white">
      <div className="container-page flex flex-col gap-6 py-12 sm:flex-row sm:items-start sm:justify-between">
        <div className="max-w-sm">
          <div className="flex items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded-full bg-ink-900 text-white">
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
                <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.4" />
              </svg>
            </span>
            <span className="font-semibold tracking-tight">PLANET</span>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-ink-500">
            An AI agent watching Earth. Machines filter everything; the agent
            investigates what matters.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-8 text-sm">
          <div>
            <p className="eyebrow mb-3">Explore</p>
            <ul className="space-y-2 text-ink-600">
              <li><Link className="hover:text-ink-950" href="/">Live Earth</Link></li>
              <li><Link className="hover:text-ink-950" href="/methodology">Methodology</Link></li>
              <li><Link className="hover:text-ink-950" href="/status">System status</Link></li>
            </ul>
          </div>
          <div>
            <p className="eyebrow mb-3">Sources</p>
            <ul className="space-y-2 text-ink-600">
              <li>USGS Earthquakes</li>
              <li>NASA EONET</li>
              <li>NASA FIRMS</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="border-t border-ink-100">
        <div className="container-page flex flex-col gap-2 py-5 text-xs text-ink-400 sm:flex-row sm:items-center sm:justify-between">
          <p>
            PLANET significance is an application-level prioritization score — not
            an official hazard classification.
          </p>
          <p>© {new Date().getFullYear()} PLANET</p>
        </div>
      </div>
    </footer>
  );
}
