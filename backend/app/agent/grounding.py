"""Grounding validation.

Enforces "model output is a proposal to validate, not truth to display."

Checks:
1. Numeric grounding — numbers in generated factual prose must be traceable to
   source records / deterministic calculations / tool outputs.
2. Claim restrictions — words like "record", "unprecedented", "deadly",
   "catastrophic", "historic", "caused by", "will cause", "safe", "dangerous"
   are rejected unless an explicit trusted source establishes the claim.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

_RESTRICTED_WORDS = [
    "record",
    "unprecedented",
    "deadly",
    "catastrophic",
    "historic",
    "caused by",
    "will cause",
    "safe",
    "dangerous",
    "devastating",
    "apocalyptic",
]

_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


@dataclass
class GroundingResult:
    passed: bool
    issues: list[str] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "issues": self.issues, "checks": self.checks}


def _extract_numbers(text: str) -> list[float]:
    return [float(m) for m in _NUMBER_RE.findall(text or "")]


def _collect_allowed_numbers(facts: dict[str, Any]) -> list[float]:
    allowed: list[float] = []
    for key in ("significance_score", "confidence"):
        if key in facts and isinstance(facts[key], (int, float)):
            allowed.append(float(facts[key]))

    def _walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, list):
            for v in obj:
                _walk(v)
        elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
            allowed.append(float(obj))

    _walk(facts.get("metrics"))
    return allowed


def _matches(value: float, allowed: list[float], tol: float = 0.02) -> bool:
    for a in allowed:
        if abs(value - a) <= max(tol, abs(a) * 0.01):
            return True
    return False


def validate_grounding(generated: dict[str, Any], facts: dict[str, Any]) -> GroundingResult:
    """Validate generated prose against deterministic facts."""
    result = GroundingResult(passed=True)
    allowed = _collect_allowed_numbers(facts)

    # 1. Numeric grounding across all prose fields.
    prose_fields = [
        generated.get("headline"),
        generated.get("summary"),
        *(generated.get("why_notable") or []),
    ]
    for text in prose_fields:
        if not text:
            continue
        for num in _extract_numbers(str(text)):
            if not _matches(num, allowed):
                result.issues.append(f"unsupported number in generated text: {num}")
                result.checks.append({"check": "numeric_grounding", "number": num, "passed": False})
            else:
                result.checks.append({"check": "numeric_grounding", "number": num, "passed": True})

    # 2. Restricted claims.
    combined = " ".join(str(t) for t in prose_fields).lower()
    for word in _RESTRICTED_WORDS:
        if word in combined:
            result.issues.append(f"restricted claim: '{word}'")
            result.checks.append({"check": "restricted_claim", "word": word, "passed": False})

    # 3. Source claims must carry a source label.
    for claim in generated.get("source_claims") or []:
        if not isinstance(claim, dict) or not claim.get("source"):
            result.issues.append("source_claim missing source label")
            result.checks.append({"check": "source_claim", "passed": False})

    result.passed = len(result.issues) == 0
    return result
