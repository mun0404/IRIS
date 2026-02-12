from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict
import cv2

def ensure_run_dir() -> Path:
    base = Path("outputs/runs")
    base.mkdir(parents=True, exist_ok=True)

    # "current" will point to latest run folder (real folder, not symlink)
    current = Path("outputs/current")
    current.mkdir(parents=True, exist_ok=True)
    (current / "images").mkdir(parents=True, exist_ok=True)
    (current / "events.jsonl").touch(exist_ok=True)
    if not (current / "latest.json").exists():
        (current / "latest.json").write_text("{}")
    return current

def append_event(path: Path, event: Dict[str, Any]) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(event) + "\n")

def update_latest(path: Path, checkpoint_id: str, data: Dict[str, Any]) -> None:
    latest = json.loads(path.read_text() or "{}")
    latest[checkpoint_id] = data
    path.write_text(json.dumps(latest, indent=2))

def save_image(path: Path, bgr_img) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), bgr_img)
