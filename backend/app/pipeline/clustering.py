"""Deterministic fire-detection clustering.

FIRMS returns tens of thousands of individual thermal anomalies. We never send
individual detections to an LLM; we cluster them deterministically first.

Method (documented for the methodology page):
- Greedy single-pass clustering with a fixed haversine radius
  (default 5 km, configurable via FIRE_CLUSTER_RADIUS_KM).
- Detections are sorted by (latitude, longitude, acquired_at) so the result is
  deterministic for a given input.
- Each detection is assigned to the first cluster whose centroid is within
  radius; otherwise a new cluster is seeded.
- Cluster centroids are the arithmetic mean of member coordinates.

Honesty note: a cluster is a "thermal-anomaly cluster", not a confirmed
wildfire perimeter or burn area.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@dataclass
class FireCluster:
    centroid_lat: float
    centroid_lon: float
    detection_count: int = 0
    sum_lat: float = 0.0
    sum_lon: float = 0.0
    min_lat: float = 90.0
    max_lat: float = -90.0
    min_lon: float = 180.0
    max_lon: float = -180.0
    frp_sum: float = 0.0
    max_frp: float = 0.0
    confidence_counts: dict[str, int] = field(default_factory=dict)
    first_detected_at: datetime | None = None
    last_detected_at: datetime | None = None

    def add(self, detection: dict[str, Any]) -> None:
        lat = float(detection["latitude"])
        lon = float(detection["longitude"])
        frp = float(detection.get("frp") or 0.0)
        confidence = str(detection.get("confidence") or "unknown")
        acquired_at = detection.get("acquired_at")

        self.detection_count += 1
        self.sum_lat += lat
        self.sum_lon += lon
        self.centroid_lat = self.sum_lat / self.detection_count
        self.centroid_lon = self.sum_lon / self.detection_count
        self.min_lat = min(self.min_lat, lat)
        self.max_lat = max(self.max_lat, lat)
        self.min_lon = min(self.min_lon, lon)
        self.max_lon = max(self.max_lon, lon)
        self.frp_sum += frp
        self.max_frp = max(self.max_frp, frp)
        self.confidence_counts[confidence] = self.confidence_counts.get(confidence, 0) + 1

        if isinstance(acquired_at, datetime):
            if self.first_detected_at is None or acquired_at < self.first_detected_at:
                self.first_detected_at = acquired_at
            if self.last_detected_at is None or acquired_at > self.last_detected_at:
                self.last_detected_at = acquired_at

    def to_dict(self) -> dict[str, Any]:
        mean_frp = self.frp_sum / self.detection_count if self.detection_count else 0.0
        return {
            "cluster_key": f"{round(self.centroid_lat, 2)}_{round(self.centroid_lon, 2)}",
            "centroid_lat": self.centroid_lat,
            "centroid_lon": self.centroid_lon,
            "geometry": {"type": "Point", "coordinates": [self.centroid_lon, self.centroid_lat]},
            "bbox": {
                "min_lat": self.min_lat,
                "max_lat": self.max_lat,
                "min_lon": self.min_lon,
                "max_lon": self.max_lon,
            },
            "detection_count": self.detection_count,
            "mean_frp": round(mean_frp, 4),
            "max_frp": round(self.max_frp, 4),
            "confidence_distribution": self.confidence_counts,
            "confidence": _confidence_score(self.confidence_counts),
            "first_detected_at": self.first_detected_at,
            "last_detected_at": self.last_detected_at,
        }


def _confidence_score(counts: dict[str, int]) -> float:
    """Aggregate confidence 0-100 from the distribution of detection confidences."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    weight = {"low": 0.3, "nominal": 0.6, "high": 1.0}
    score = 0.0
    for conf, count in counts.items():
        score += count * weight.get(conf, 0.5)
    return round(score / total * 100.0, 2)


def cluster_fire_detections(detections: list[dict[str, Any]], radius_km: float = 5.0) -> list[dict[str, Any]]:
    """Cluster detections deterministically and return cluster dicts."""
    if not detections:
        return []

    ordered = sorted(
        detections,
        key=lambda d: (
            round(float(d.get("latitude") or 0.0), 6),
            round(float(d.get("longitude") or 0.0), 6),
            str(d.get("acquired_at") or ""),
        ),
    )

    clusters: list[FireCluster] = []
    for detection in ordered:
        lat = float(detection["latitude"])
        lon = float(detection["longitude"])
        matched = False
        for cluster in clusters:
            if haversine_km(lat, lon, cluster.centroid_lat, cluster.centroid_lon) <= radius_km:
                cluster.add(detection)
                matched = True
                break
        if not matched:
            cluster = FireCluster(centroid_lat=lat, centroid_lon=lon)
            cluster.add(detection)
            clusters.append(cluster)

    return [c.to_dict() for c in clusters]
