import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Methodology — PLANET",
  description: "How PLANET works: deterministic filtering, agent investigation, grounding, and validation.",
};

const PIPELINE = [
  {
    n: "01",
    title: "Ingest",
    kind: "Deterministic",
    desc: "Fetch structured data from USGS Earthquake feeds, NASA EONET, and NASA FIRMS. We use official structured APIs, never scraped webpages.",
  },
  {
    n: "02",
    title: "Normalize",
    kind: "Deterministic",
    desc: "Convert heterogeneous records into a common event model with a controlled category vocabulary. Raw source payloads are preserved for audit.",
  },
  {
    n: "03",
    title: "Detect change",
    kind: "Deterministic",
    desc: "Compare each event against its prior state to classify transitions: NEW, UPDATED, ESCALATING, DE-ESCALATING, UNCHANGED, or CLOSED.",
  },
  {
    n: "04",
    title: "Score significance",
    kind: "Deterministic",
    desc: "Compute a transparent 0–100 prioritization score with category-specific formulas. No LLM is asked whether an event matters.",
  },
  {
    n: "05",
    title: "Investigate",
    kind: "AI",
    desc: "Only events above a configurable threshold are investigated. The agent uses read-only tools to gather context and write an explanation.",
  },
  {
    n: "06",
    title: "Validate",
    kind: "Deterministic",
    desc: "Generated prose is checked for numeric grounding and restricted claims. Unsupported claims are rejected.",
  },
  {
    n: "07",
    title: "Publish",
    kind: "Deterministic",
    desc: "Validated explanations (or a deterministic fallback) are published. The site never depends on the LLM succeeding.",
  },
];

const RULES = [
  ["Missing → zero", "Missing values stay missing. They are never silently converted to zero."],
  ["Unknown → false", "Unknown is never treated as false."],
  ["Not reported → none", "Fields that are not reported remain absent."],
  ["Not available → safe", "Absence of data is never framed as safety."],
  ["Record / historic / unprecedented", "Never used unless a trusted source explicitly establishes the claim."],
  ["Fire detection ≠ confirmed wildfire", "FIRMS reports satellite thermal anomalies, not confirmed wildfires."],
  ["Significance ≠ hazard severity", "PLANET significance is prioritization, not an official hazard classification."],
];

function Step({ step }: { step: (typeof PIPELINE)[number] }) {
  return (
    <div className="card relative overflow-hidden p-6">
      <div className="flex items-center justify-between">
        <span className="font-mono text-sm text-ocean">{step.n}</span>
        <span
          className={`chip ${
            step.kind === "AI"
              ? "bg-ocean-100 text-ocean-600"
              : "bg-earth-100 text-earth-600"
          }`}
        >
          {step.kind}
        </span>
      </div>
      <h3 className="mt-3 text-lg font-semibold text-ink-950">{step.title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-ink-500">{step.desc}</p>
    </div>
  );
}

export default function MethodologyPage() {
  return (
    <div className="container-page py-16">
      <div className="max-w-3xl">
        <p className="eyebrow">Methodology</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-ink-950 sm:text-5xl">
          How PLANET works
        </h1>
        <p className="mt-5 text-lg leading-relaxed text-ink-500">
          PLANET is a small autonomous intelligence system, not a chatbot with a
          map. Its core principle:
        </p>
        <p className="mt-4 font-display text-2xl italic text-ink-900">
          Machines filter everything. The agent investigates what matters.
        </p>
      </div>

      <section className="mt-16">
        <h2 className="text-2xl font-semibold tracking-tight text-ink-950">The pipeline</h2>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {PIPELINE.map((s) => (
            <Step key={s.n} step={s} />
          ))}
        </div>
      </section>

      <section className="mt-20 grid gap-10 lg:grid-cols-2">
        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-ink-950">
            Significance scoring
          </h2>
          <p className="mt-4 text-base leading-relaxed text-ink-500">
            Scores range 0–100 and map to tiers: ROUTINE (0–24), NOTABLE (25–49),
            SIGNIFICANT (50–74), MAJOR (75–100). Formulas are category-specific and
            strongly nonlinear for magnitude.
          </p>
          <p className="mt-4 text-base leading-relaxed text-ink-500">
            For earthquakes, the magnitude component scales roughly as{" "}
            <code className="rounded bg-ink-50 px-1.5 py-0.5 text-sm">(M / 9)^3.5</code>,
            so a 7 → 8 increase carries far more weight than 3 → 4. Additional
            components account for depth, felt reports, USGS significance, alert
            level, and tsunami flags.
          </p>
          <p className="mt-4 text-base leading-relaxed text-ink-500">
            For wildfires (FIRMS thermal-anomaly clusters), the score uses detection
            count (log-scaled), fire radiative power (FRP), confidence distribution,
            and growth since the previous run.
          </p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-ink-950">
            Fire clustering
          </h2>
          <p className="mt-4 text-base leading-relaxed text-ink-500">
            FIRMS returns tens of thousands of individual detections. These are
            never sent to an LLM. Instead we cluster detections deterministically
            using a single-pass greedy algorithm with a fixed haversine radius
            (default 5 km). Detections are sorted by position and time so results
            are reproducible.
          </p>
          <p className="mt-4 text-base leading-relaxed text-ink-500">
            Each cluster derives a centroid, detection count, bounding box, mean/max
            FRP, confidence distribution, and first/last detection times. Growth is
            computed by comparing a cluster against the previous run.
          </p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-ink-950">
            Grounded generation
          </h2>
          <p className="mt-4 text-base leading-relaxed text-ink-500">
            Model output is treated as a proposal to validate, not truth to display.
            Numbers in generated prose must be traceable to source records,
            deterministic calculations, or tool outputs. Restricted words (record,
            catastrophic, deadly, historic…) are rejected unless an explicit trusted
            source establishes them.
          </p>
        </div>

        <div>
          <h2 className="text-2xl font-semibold tracking-tight text-ink-950">
            Deterministic fallback
          </h2>
          <p className="mt-4 text-base leading-relaxed text-ink-500">
            If AI generation fails validation — or no LLM is configured — PLANET
            publishes a deterministic description built only from verified fields.
            The public site never depends on the LLM responding successfully.
            Failure yields less sophisticated but still correct output.
          </p>
        </div>
      </section>

      <section className="mt-20">
        <h2 className="text-2xl font-semibold tracking-tight text-ink-950">Data honesty rules</h2>
        <div className="mt-8 overflow-hidden rounded-2xl border border-ink-100">
          {RULES.map(([term, meaning], i) => (
            <div
              key={term}
              className={`grid gap-1 px-6 py-4 sm:grid-cols-[260px_1fr] ${
                i % 2 ? "bg-ink-50/50" : "bg-white"
              }`}
            >
              <span className="font-medium text-ink-800">{term}</span>
              <span className="text-sm leading-relaxed text-ink-500">{meaning}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-20">
        <h2 className="text-2xl font-semibold tracking-tight text-ink-950">Limitations</h2>
        <ul className="mt-6 max-w-3xl space-y-3 text-base leading-relaxed text-ink-500">
          <li className="flex gap-3">
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-coral" />
            PLANET ingests a limited set of public sources and does not replace
            official emergency or hazard information.
          </li>
          <li className="flex gap-3">
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-coral" />
            FIRMS detections are thermal anomalies, not confirmed wildfire extents
            or impacts.
          </li>
          <li className="flex gap-3">
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-coral" />
            PLANET never estimates casualties, damage, or causal attribution from
            magnitude or anomaly data alone.
          </li>
          <li className="flex gap-3">
            <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-coral" />
            Freshness reflects successful ingestion; the UI marks data as stale when
            a provider is degraded or unavailable.
          </li>
        </ul>
      </section>
    </div>
  );
}
