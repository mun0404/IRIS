from __future__ import annotations
import csv, json
from pathlib import Path
from typing import Any, Dict, List, Optional

def _ensure(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def current_dir(base: str = "outputs") -> Path:
    d = Path(base) / "current"
    _ensure(d)
    return d

def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj) + "\n")

def build_report_from_events(events_jsonl: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not events_jsonl.exists():
        return rows
    for line in events_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        e = json.loads(line)
        rows.append(e)
    return rows

def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    # Flatten conditions for CSV readability
    fieldnames = ["run_id","run_start_utc","timestamp_utc","checkpoint_id","checkpoint_sequence","result","image_ref","conditions"]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({
                "run_id": r.get("run_id"),
                "run_start_utc": r.get("run_start_utc"),
                "timestamp_utc": r.get("timestamp_utc"),
                "checkpoint_id": r.get("checkpoint_id"),
                "checkpoint_sequence": r.get("checkpoint_sequence"),
                "result": r.get("result"),
                "image_ref": r.get("image_ref"),
                "conditions": json.dumps(r.get("conditions", [])),
            })
