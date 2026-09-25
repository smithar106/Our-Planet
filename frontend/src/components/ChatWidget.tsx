"use client";

import { useEffect, useRef, useState } from "react";
import { askChat } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  text: string;
  sources?: string[];
  deterministic?: boolean;
}

const SUGGESTIONS = [
  "What significant events happened in the last 24 hours?",
  "Show me the strongest earthquakes today",
  "Are there any active wildfire clusters?",
];

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  async function send(text?: string) {
    const question = (text ?? input).trim();
    if (!question || loading) return;
    setInput("");
    setError(null);
    setMessages((m) => [...m, { role: "user", text: question }]);
    setLoading(true);
    try {
      const resp = await askChat(question);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: resp.answer, sources: resp.sources, deterministic: resp.deterministic },
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Ask PLANET"
        className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-ink-900 text-white shadow-lift transition-transform hover:scale-105"
      >
        {open ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5c-1.5 0-2.9-.4-4.1-1L3 20l1-5.4A8.5 8.5 0 1 1 21 11.5Z" />
          </svg>
        )}
      </button>

      {open && (
        <div className="fixed bottom-24 right-5 z-50 flex h-[480px] w-[360px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-ink-100 bg-white shadow-lift">
          <div className="flex items-center justify-between border-b border-ink-100 bg-paper px-4 py-3">
            <div className="flex items-center gap-2">
              <span className="grid h-7 w-7 place-items-center rounded-full bg-ink-900 text-white">
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.4">
                  <circle cx="8" cy="8" r="6" />
                  <path d="M2.4 8h11.2" stroke="currentColor" strokeWidth="1.1" />
                </svg>
              </span>
              <div>
                <p className="text-sm font-semibold text-ink-950">Ask PLANET</p>
                <p className="text-[11px] text-ink-400">Questions about live Earth events</p>
              </div>
            </div>
          </div>

          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
            {messages.length === 0 && (
              <div className="space-y-2 pt-2">
                <p className="text-xs text-ink-400">Try asking:</p>
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="block w-full rounded-xl border border-ink-100 px-3 py-2 text-left text-xs text-ink-600 transition-colors hover:bg-ink-50"
                  >
                    {s}
                  </button>
                ))}
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <div
                  className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed ${
                    m.role === "user"
                      ? "bg-ink-900 text-white"
                      : "bg-ink-50 text-ink-800"
                  }`}
                >
                  <p className="whitespace-pre-wrap">{m.text}</p>
                  {m.sources && m.sources.length > 0 && (
                    <p className="mt-2 text-[11px] opacity-70">
                      Sources: {m.sources.join(", ")}
                    </p>
                  )}
                  {m.deterministic && (
                    <p className="mt-1.5 text-[11px] italic opacity-60">Deterministic response</p>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="flex items-center gap-1.5 rounded-2xl bg-ink-50 px-4 py-3">
                  <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-ink-400" />
                  <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-ink-400" style={{ animationDelay: "0.2s" }} />
                  <span className="h-1.5 w-1.5 animate-pulse-soft rounded-full bg-ink-400" style={{ animationDelay: "0.4s" }} />
                </div>
              </div>
            )}

            {error && <p className="text-center text-xs text-coral">{error}</p>}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
            className="flex items-center gap-2 border-t border-ink-100 p-3"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about earthquakes, fires, storms…"
              className="min-w-0 flex-1 rounded-xl border border-ink-100 bg-paper px-3 py-2 text-sm outline-none focus:border-ocean"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-ink-900 text-white transition-colors disabled:opacity-40"
              aria-label="Send"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="m5 12 14-7-4 7 4 7-14-7Z" />
              </svg>
            </button>
          </form>
        </div>
      )}
    </>
  );
}
