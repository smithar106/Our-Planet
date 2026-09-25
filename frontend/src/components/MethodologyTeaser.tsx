import Link from "next/link";

const STEPS = [
  { n: "01", title: "Ingest", desc: "Trusted global data from USGS, NASA EONET, and NASA FIRMS." },
  { n: "02", title: "Normalize", desc: "Heterogeneous records become a common event model." },
  { n: "03", title: "Detect change", desc: "Compare with prior state to find what changed." },
  { n: "04", title: "Score", desc: "A transparent, deterministic significance score." },
  { n: "05", title: "Investigate", desc: "The agent investigates only what matters." },
  { n: "06", title: "Validate", desc: "Generated claims are grounded or rejected." },
  { n: "07", title: "Publish", desc: "Grounded explanations reach the public." },
];

export function MethodologyTeaser() {
  return (
    <section className="border-t border-ink-100 bg-white">
      <div className="container-page py-20">
        <div className="grid gap-10 lg:grid-cols-2">
          <div>
            <p className="eyebrow">How it works</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-ink-950 sm:text-4xl">
              Machines filter everything.
              <br />
              <span className="font-display italic text-ocean">The agent investigates what matters.</span>
            </h2>
            <p className="mt-5 max-w-md text-base leading-relaxed text-ink-500">
              LLMs don&apos;t process every raw event. Deterministic software handles
              ingestion, normalization, deduplication, scoring, and validation —
              while the agent only investigates events that cross a threshold.
            </p>
            <Link href="/methodology" className="btn-primary mt-8">
              Read the methodology
              <span aria-hidden>→</span>
            </Link>
          </div>

          <ol className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {STEPS.map((s) => (
              <li key={s.n} className="card p-5">
                <span className="font-mono text-xs text-ocean">{s.n}</span>
                <p className="mt-2 font-semibold text-ink-950">{s.title}</p>
                <p className="mt-1 text-sm leading-relaxed text-ink-500">{s.desc}</p>
              </li>
            ))}
            <li className="flex items-center justify-center rounded-2xl border border-dashed border-ink-200 p-5 text-sm text-ink-400">
              7 deterministic steps
            </li>
          </ol>
        </div>
      </div>
    </section>
  );
}
