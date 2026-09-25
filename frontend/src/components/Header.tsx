import Link from "next/link";
import { LiveIndicator } from "./LiveIndicator";

const NAV = [
  { href: "/", label: "Earth" },
  { href: "/brief", label: "Daily Brief" },
  { href: "/methodology", label: "Methodology" },
  { href: "/status", label: "Status" },
];

export function Header() {
  return (
    <header className="sticky top-0 z-40 border-b border-ink-100 bg-paper/80 backdrop-blur">
      <div className="container-page flex h-16 items-center justify-between">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-full bg-ink-900 text-white">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
              <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.4" />
              <path
                d="M2.4 8h11.2M8 2a11 11 0 0 1 3 6 11 11 0 0 1-3 6 11 11 0 0 1-3-6 11 11 0 0 1 3-6Z"
                stroke="currentColor"
                strokeWidth="1.1"
                fill="none"
              />
            </svg>
          </span>
          <span className="text-[15px] font-semibold tracking-tight">
            PLANET
            <span className="ml-2 hidden text-xs font-normal uppercase tracking-[0.2em] text-ink-400 sm:inline">
              Live Earth Intelligence
            </span>
          </span>
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-full px-3 py-1.5 text-sm font-medium text-ink-700 transition-colors hover:bg-ink-50 hover:text-ink-950"
            >
              {item.label}
            </Link>
          ))}
          <LiveIndicator className="ml-2 hidden sm:inline-flex" />
        </nav>
      </div>
    </header>
  );
}
