from __future__ import annotations

import json
import random
import yaml

from pathlib import Path
from flask import Flask, jsonify, render_template, send_from_directory, send_file
from src.inspection.schema import make_run_id, utc_now_iso

app = Flask(__name__)

# Resolve project root regardless of where you run python from
ROOT = Path(__file__).resolve().parents[2]          # .../IRIS_Final
OUT = ROOT / "outputs" / "current"
LATEST = OUT / "latest.json"
IMAGES = OUT / "images"
EVENTS = OUT / "events.jsonl"

CFG_CHECKPOINTS = ROOT / "configs" / "checkpoints.yaml"


def _read_json(path: Path, default):
    if not path.exists():
        return default
    txt = path.read_text(encoding="utf-8").strip()
    if not txt:
        return default
    return json.loads(txt)


def _write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _append_jsonl(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj) + "\n")


def _load_checkpoints_cfg():
    if not CFG_CHECKPOINTS.exists():
        return {"checkpoints": []}
    return yaml.safe_load(CFG_CHECKPOINTS.read_text(encoding="utf-8")) or {"checkpoints": []}


def _checkpoint_order():
    cfg = _load_checkpoints_cfg()
    cps = cfg.get("checkpoints", [])
    return [c.get("id") for c in cps if c.get("id")]


def _checkpoint_names():
    cfg = _load_checkpoints_cfg()
    cps = cfg.get("checkpoints", [])
    names = {}
    for c in cps:
        cid = c.get("id")
        if not cid:
            continue
        names[cid] = c.get("name") or c.get("description") or cid
    return names


def _fresh_run():
    ids = _checkpoint_order()
    now = utc_now_iso()
    return {
        "run_id": make_run_id(),
        "start_time_utc": now,
        "run_state": "IN_PROGRESS",
        "robot_state": "TRIGGERED",
        "summary": {
            "total": len(ids),
            "passed": 0,
            "failed": len(ids),
            "last_updated_utc": now,
            "status": "FAIL" if len(ids) else "UNKNOWN",
        },
    }


def _recompute_summary(latest: dict, run: dict):
    ids = _checkpoint_order()
    keys = ids if ids else list(latest.keys())
    total = len(keys)
    now = utc_now_iso()

    passed = 0
    failed = 0
    pending = 0

    for cid in keys:
        r = (latest.get(cid, {}) or {}).get("result")
        if r == "PASS":
            passed += 1
        elif r == "FAIL":
            failed += 1
        else:
            pending += 1

    if failed > 0:
        status = "FAIL"
    elif pending > 0:
        status = "PENDING"
    elif total > 0:
        status = "PASS"
    else:
        status = "UNKNOWN"

    run["summary"] = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "last_updated_utc": now,
        "status": status,
    }

    if status == "PASS":
        run["run_state"] = "COMPLETED"
        run["robot_state"] = "COMPLETED"

    return run


@app.get("/")
def home():
    return render_template("dashboard.html")


@app.get("/api/latest")
def api_latest():
    if not LATEST.exists():
        return jsonify({})
    return jsonify(json.loads(LATEST.read_text() or "{}"))


@app.get("/api/run")
def api_run():
    p = OUT / "run.json"
    if not p.exists():
        return jsonify({})
    return jsonify(json.loads(p.read_text(encoding="utf-8")))


@app.get("/download/json")
def download_json():
    p = OUT / "report.json"
    return send_file(p, as_attachment=True, download_name="inspection_report.json")


@app.get("/download/csv")
def download_csv():
    p = OUT / "report.csv"
    return send_file(p, as_attachment=True, download_name="inspection_report.csv")


@app.get("/images/<path:name>")
def images(name: str):
    return send_from_directory(IMAGES, name)


# -------------------------------
# Demo Control Mode (#6)
# -------------------------------

@app.post("/api/demo/start")
def demo_start():
    OUT.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)

    run = _fresh_run()
    _write_json(OUT / "run.json", run)

    # reset latest + events for a clean run
    ids = _checkpoint_order()
    names = _checkpoint_names()
    now = run["start_time_utc"]

    seed = {}
    for i, cid in enumerate(ids, start=1):
        seed[cid] = {
            "updated_utc": now,
            "run_id": run["run_id"],
            "run_start_utc": run["start_time_utc"],
            "checkpoint_sequence": i,
            "checkpoint_name": names.get(cid, cid),
            "result": "PENDING",
            "reason": "",
            "image": f"images/{cid}.jpg",
            "conditions": [],
        }

    _write_json(LATEST, seed)
    EVENTS.write_text("", encoding="utf-8")

    return jsonify({"ok": True, "run_id": run["run_id"]})


@app.post("/api/demo/reset")
def demo_reset():
    OUT.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)

    run = _fresh_run()
    _write_json(OUT / "run.json", run)

    ids = _checkpoint_order()
    names = _checkpoint_names()
    now = run["start_time_utc"]

    seed = {}
    for i, cid in enumerate(ids, start=1):
        seed[cid] = {
            "updated_utc": now,
            "run_id": run["run_id"],
            "run_start_utc": run["start_time_utc"],
            "checkpoint_sequence": i,
            "checkpoint_name": names.get(cid, cid),
            "result": "PENDING",
            "reason": "",
            "image": f"images/{cid}.jpg",
            "conditions": [],
        }

    _write_json(LATEST, seed)
    EVENTS.write_text("", encoding="utf-8")

    return jsonify({"ok": True})


def _simulate(result: str):
    OUT.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)

    run = _read_json(OUT / "run.json", _fresh_run())
    latest = _read_json(LATEST, {})

    ids = _checkpoint_order()
    names = _checkpoint_names()

    # pick next checkpoint that is still PENDING; else cycle from the start
    target = None
    for cid in ids:
        if latest.get(cid, {}).get("result") == "PENDING":
            target = cid
            break
    if target is None:
        target = ids[0] if ids else (next(iter(latest.keys()), "checkpoint_1"))

    now = utc_now_iso()
    seq = (ids.index(target) + 1) if target in ids else -1

    demo_conditions = []

    for i in range(5):
        if result == "PASS":
            confidence = round(random.uniform(0.90, 0.99), 3)
            observed = "OK"
            passed = True
        else:
            confidence = round(random.uniform(0.70, 0.89), 3)
            observed = random.choice(["NOT_OK", "ANOMALY", "NOT_OPERATIONAL"])
            passed = False
    
        demo_conditions.append({
            "condition_name": f"demo_condition_{i+1}",
            "expected": "OK",
            "observed": observed,
            "passed": passed,
            "confidence": confidence,
        })
    
    latest[target] = {
        "updated_utc": now,
        "run_id": run.get("run_id"),
        "run_start_utc": run.get("start_time_utc"),
        "checkpoint_sequence": seq,
        "checkpoint_name": names.get(target, target),
        "result": result,
        "reason": "" if result == "PASS" else "Simulated failure for demo",
        "image": f"images/{target}.jpg",
        "conditions": demo_conditions,
    }

    event = {
        "timestamp_utc": now,
        "run_id": run.get("run_id"),
        "run_start_utc": run.get("start_time_utc"),
        "checkpoint_id": target,
        "checkpoint_name": names.get(target, target),
        "checkpoint_sequence": seq,
        "result": result,
        "conditions": demo_conditions,
        "image_ref": str(IMAGES / f"{target}.jpg"),
        "demo": True,
    }
    _append_jsonl(EVENTS, event)

    run = _recompute_summary(latest, run)

    _write_json(LATEST, latest)
    _write_json(OUT / "run.json", run)

    return {"ok": True, "checkpoint": target, "result": result}


@app.post("/api/demo/simulate_pass")
def demo_pass():
    return jsonify(_simulate("PASS"))


@app.post("/api/demo/simulate_fail")
def demo_fail():
    return jsonify(_simulate("FAIL"))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)