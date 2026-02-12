from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from src.perception.yolo_infer import Detection

DOOR = {"door_open", "door_closed", "door_semi"}

@dataclass
class ConditionResult:
    name: str
    expected: str
    observed: str
    passed: bool
    confidence: Optional[float]

def best_door(dets: List[Detection]) -> Tuple[Optional[str], Optional[float]]:
    best = None
    best_conf = None
    for d in dets:
        if d.cls_name in DOOR and (best_conf is None or d.conf > best_conf):
            best, best_conf = d.cls_name, d.conf
    return best, best_conf

def evaluate(expected: Dict, dets: List[Detection]) -> List[ConditionResult]:
    out: List[ConditionResult] = []

    if "door_state" in expected:
        cls, conf = best_door(dets)
        if cls is None:
            obs = "UNKNOWN"
            passed = False
        else:
            obs = {"door_closed":"CLOSED","door_open":"OPEN","door_semi":"SEMI"}[cls]
            passed = (obs == expected["door_state"])
        out.append(ConditionResult("door_state", expected["door_state"], obs, passed, conf))

    if "debris" in expected:
        debris = [d for d in dets if d.cls_name not in DOOR]
        obs = "PRESENT" if debris else "ABSENT"
        conf = max([d.conf for d in debris], default=None)
        passed = (obs == expected["debris"])
        out.append(ConditionResult("debris", expected["debris"], obs, passed, conf))

    if "panel_power" in expected:
        out.append(ConditionResult("panel_power", expected["panel_power"], "NOT_IMPLEMENTED", False, None))

    return out
