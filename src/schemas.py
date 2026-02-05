from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class CheckpointResult:
    timestamp: str
    checkpoint_id: str
    condition_evaluated: str
    expected: str
    observed: str
    result: str  # "pass" | "fail" | "unknown"
    image_reference: str
    confidence: Optional[float] = None  # optional per scope
    notes: Optional[str] = None         # useful for demo/audit clarity

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class InspectionRunSummary:
    run_id: str
    timestamp: str
    total_checkpoints: int
    passed: int
    flagged: int
    issues: list[dict]  # minimal: [{"checkpoint_id": "...", "issue": "..."}]

    def to_dict(self) -> dict:
        return asdict(self)