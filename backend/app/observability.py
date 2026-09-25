"""Observability / tracing abstraction.

Two complementary mechanisms:

1. Span tracing (in-process) — a lightweight span tree used across the
   pipeline, agent, and validation. Backends: "memory" (tests/dev) or "null".

2. MLflow run logging — each logical unit of work (pipeline run, agent pass,
   daily brief) is logged as an MLflow run when `MLFLOW_TRACKING_URI` is set.
   MLflow is imported lazily so it never becomes a hard dependency, and any
   telemetry failure is isolated and never breaks the pipeline.
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


# ---------------------------------------------------------------------------
# MLflow
# ---------------------------------------------------------------------------


def mlflow_enabled() -> bool:
    return bool(settings.mlflow_tracking_uri)


def mlflow_log_run(
    run_name: str,
    metrics: dict[str, float] | None = None,
    params: dict[str, Any] | None = None,
    tags: dict[str, str] | None = None,
) -> str | None:
    """Log a single MLflow run. Returns the run id, or None if disabled/failed.

    Never raises — observability failures must not break the pipeline.
    """
    if not mlflow_enabled():
        return None
    try:
        import mlflow  # type: ignore

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        mlflow.set_experiment("planet")
        with mlflow.start_run(run_name=run_name) as run:
            if params:
                mlflow.log_params({k: str(v)[:500] for k, v in params.items()})
            if metrics:
                mlflow.log_metrics({k: float(v) for k, v in metrics.items()})
            if tags:
                mlflow.set_tags(tags)
            return run.info.run_id
    except Exception as exc:  # pragma: no cover - optional dependency
        logger.warning("MLflow logging failed (ignored): %s", exc)
        return None
