import { Hero } from "@/components/Hero";
import { LiveMap } from "@/components/LiveMap";
import { GlobalSnapshot } from "@/components/GlobalSnapshot";
import { WatchList } from "@/components/WatchList";
import { LiveFeed } from "@/components/LiveFeed";
import { MethodologyTeaser } from "@/components/MethodologyTeaser";

export default function Home() {
  return (
    <>
      <Hero />

      <section className="container-page pb-20">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-x-8 gap-y-2">
          <div className="min-w-0">
            <p className="eyebrow">Live world map</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
              What is happening right now
            </h2>
          </div>
          <p className="max-w-xs shrink-0 text-xs leading-relaxed text-ink-400 sm:text-right">
            Marker size reflects PLANET significance. Click any event for details.
          </p>
        </div>
        <LiveMap />
      </section>

      <GlobalSnapshot />
      <WatchList />
      <LiveFeed />
      <MethodologyTeaser />
    </>
  );
}
