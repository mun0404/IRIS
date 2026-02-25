from __future__ import annotations
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def make_run_id(prefix: str = "IR") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    return f"{prefix}-{ts}"

@dataclass
class ConditionResult:
    condition_name: str
    expected: Any
    observed: Any
    passed: bool
    confidence: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CheckpointResult:
    checkpoint_id: str
    checkpoint_name: str
    sequence_number: int
    timestamp_utc: str
    result: str  # PASS/FAIL
    camera_id: str
    conditions: List[ConditionResult] = field(default_factory=list)
    image_ref: Optional[str] = None
    annotated_image_ref: Optional[str] = None

@dataclass
class RunSummary:
    total: int
    passed: int
    failed: int
    last_updated_utc: str
    status: str  # PASS/FAIL

@dataclass
class InspectionRun:
    run_id: str
    start_time_utc: str
    run_state: str = "IN_PROGRESS"  # IN_PROGRESS/COMPLETED
    robot_state: str = "TRIGGERED"  # ARRIVED/TRIGGERED/EVALUATING/COMPLETED
    checkpoints: List[CheckpointResult] = field(default_factory=list)
    summary: Optional[RunSummary] = None

    def finalize(self) -> None:
        total = len(self.checkpoints)
        passed = sum(1 for cp in self.checkpoints if cp.result == "PASS")
        failed = total - passed
        last = utc_now_iso()
        status = "PASS" if failed == 0 and total > 0 else "FAIL"
        self.run_state = "COMPLETED"
        self.robot_state = "COMPLETED"
        self.summary = RunSummary(total, passed, failed, last, status)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
