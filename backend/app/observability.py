"""Observability / tracing abstraction.

A lightweight in-process span tracer used across the pipeline, agent, and
validation. Backends: "memory" (tests/dev) or "null".
"""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from app.config import settings

logger = logging.getLogger("planet.tracing")

_span_stack: ContextVar[list[Span]] = ContextVar("span_stack", default=[])  # noqa: B039


class Span:
    def __init__(self, name: str, parent: Span | None = None):
        self.id = uuid.uuid4().hex
        self.name = name
        self.parent_id = parent.id if parent else None
        self.started = time.perf_counter()
        self.ended: float | None = None
        self.attributes: dict[str, Any] = {}
        self.error: str | None = None

    def set(self, **attrs: Any) -> None:
        self.attributes.update(attrs)

    def finish(self) -> None:
        self.ended = time.perf_counter()

    @property
    def duration_ms(self) -> float:
        if self.ended is None:
            return (time.perf_counter() - self.started) * 1000
        return (self.ended - self.started) * 1000


class NullTracer:
    def start(self, name: str) -> Span:
        return Span(name)

    def end(self, span: Span, error: str | None = None) -> None:
        span.error = error
        span.finish()


class MemoryTracer(NullTracer):
    def __init__(self) -> None:
        self.spans: list[Span] = []

    def start(self, name: str) -> Span:
        stack = _span_stack.get()
        parent = stack[-1] if stack else None
        span = Span(name, parent)
        stack.append(span)
        _span_stack.set(stack)
        return span

    def end(self, span: Span, error: str | None = None) -> None:
        span.error = error
        span.finish()
        stack = _span_stack.get()
        if stack and stack[-1] is span:
            stack.pop()
            _span_stack.set(stack)
        self.spans.append(span)


def _get_tracer() -> NullTracer:
    if settings.tracing_backend == "memory":
        return MemoryTracer()
    return NullTracer()


_tracer: NullTracer | None = None


def get_tracer() -> NullTracer:
    global _tracer
    if _tracer is None:
        _tracer = _get_tracer()
    return _tracer


@contextmanager
def span(name: str):
    """Trace a block of work. Never raises on telemetry errors."""
    tracer = get_tracer()
    s = tracer.start(name)
    try:
        yield s
    except Exception as exc:
        tracer.end(s, error=str(exc))
        raise
    else:
        tracer.end(s)

