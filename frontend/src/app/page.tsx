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

      <section className="container-page -mt-8 pb-20">
        <div className="mb-6 flex items-end justify-between">
          <div>
            <p className="eyebrow">Live world map</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-ink-950 sm:text-3xl">
              What is happening right now
            </h2>
          </div>
          <p className="hidden max-w-xs text-right text-xs leading-relaxed text-ink-400 sm:block">
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
