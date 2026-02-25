from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import yaml

from src.perception.yolo_infer import YoloInfer
from src.inspection.evaluator import evaluate

# Run + I/O helpers (you already have these modules)
from src.inspection.schema import make_run_id, utc_now_iso
from src.inspection.run_io import (
    current_dir,
    write_json,
    build_report_from_events,
    write_csv,
)
from src.inspection.writer import append_event, update_latest, save_image


class IRISInspector(Node):
    def __init__(self, cfg_topics: Dict, cfg_checkpoints: Dict, cfg_model: Dict):
        super().__init__("iris_inspector")
        self.bridge = CvBridge()

        # ---- Config ----
        self.topics = cfg_topics["camera_topics"]
        self.checkpoints = {c["id"]: c for c in cfg_checkpoints["checkpoints"]}

        # ---- Run metadata (for demo-ready UI) ----
        self.run_id = make_run_id()
        self.run_start_utc = utc_now_iso()
        self.run_state = "IN_PROGRESS"   # IN_PROGRESS / COMPLETED
        self.robot_state = "TRIGGERED"   # ARRIVED / TRIGGERED / EVALUATING / COMPLETED

        # Stable checkpoint ordering
        checkpoint_ids = list(self.topics.keys())
        self.seq_map = {cid: i + 1 for i, cid in enumerate(checkpoint_ids)}

        # Human-friendly names
        self.cp_name = {}
        for cid in checkpoint_ids:
            cfg = self.checkpoints.get(cid, {})
            self.cp_name[cid] = cfg.get("name") or cfg.get("display_name") or cid

        # ---- Throttling ----
        self.throttle_hz = float(cfg_model.get("throttle_hz", 2))
        self.min_dt = 1.0 / self.throttle_hz
        self.last_t: Dict[str, float] = {cid: 0.0 for cid in self.topics.keys()}

        # ---- Perception ----
        self.yolo = YoloInfer(
            weights_path=cfg_model["weights_path"],
            device=cfg_model["device"],
            conf_threshold=cfg_model["conf_threshold"],
            imgsz=cfg_model["imgsz"],
        )

        # ---- Output paths (stable "outputs/current") ----
        self.out_dir = current_dir()
        self.events_path = self.out_dir / "events.jsonl"
        self.latest_path = self.out_dir / "latest.json"
        self.images_dir = self.out_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)

        # ---- Subscriptions ----
        for cid, topic in self.topics.items():
            self.get_logger().info(f"Subscribing {cid} -> {topic}")
            self.create_subscription(Image, topic, lambda msg, _cid=cid: self.cb(_cid, msg), 10)

        # Initialize run.json immediately so UI has something to show even before frames arrive
        self._write_run_and_reports()

    def cb(self, cid: str, msg: Image):
        now = time.time()
        if now - self.last_t[cid] < self.min_dt:
            return
        self.last_t[cid] = now

        # If you want stronger framing during activity:
        self.robot_state = "EVALUATING"

        bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        dets = self.yolo.infer(bgr)
        annotated = self.yolo.annotate(bgr)

        expected = self.checkpoints[cid]["expected"]
        conds = evaluate(expected, dets)

        # pass/fail: ignore panel_power placeholder
        gating = [c for c in conds if getattr(c, "name", "") != "panel_power"]
        passed_all = all(c.passed for c in gating) if gating else False
        result = "PASS" if passed_all else "FAIL"

        img_path = self.images_dir / f"{cid}.jpg"
        save_image(img_path, annotated)

        reason = ""
        for c in gating:
            if not c.passed:
                reason = f"{c.name}: expected {c.expected}, observed {c.observed}"
                break

        event = {
            "timestamp_utc": utc_now_iso(),
            "run_id": self.run_id,
            "run_start_utc": self.run_start_utc,
            "run_state": self.run_state,
            "robot_state": self.robot_state,

            "checkpoint_id": cid,
            "checkpoint_name": self.cp_name.get(cid, cid),
            "checkpoint_sequence": self.seq_map.get(cid, -1),
            "camera_id": cid,
            "camera_topic": self.topics.get(cid, ""),

            "result": result,
            "conditions": [
                {
                    # backward-compatible + explicit
                    "name": c.name,
                    "condition_name": c.name,
                    "expected": c.expected,
                    "observed": c.observed,
                    "pass": c.passed,      # keep for existing UI
                    "passed": c.passed,    # explicit for new UI
                    "confidence": c.confidence,
                }
                for c in conds
            ],
            "image_ref": str(img_path),
        }

        # Append to events.jsonl
        append_event(self.events_path, event)

        # Update latest.json
        update_latest(
            self.latest_path,
            cid,
            {
                "updated_utc": event["timestamp_utc"],
                "run_id": self.run_id,
                "run_start_utc": self.run_start_utc,
                "checkpoint_sequence": self.seq_map.get(cid, -1),
                "checkpoint_name": self.cp_name.get(cid, cid),

                "result": result,
                "reason": reason,
                "image": f"images/{cid}.jpg",
                "conditions": event["conditions"],
            },
        )

        # Refresh run.json + report exports
        self._write_run_and_reports()

    def _write_run_and_reports(self) -> None:
        """
        Writes:
          - outputs/current/run.json
          - outputs/current/report.json
          - outputs/current/report.csv
        """
        try:
            latest_data = {}
            if self.latest_path.exists():
                latest_data = json.loads(self.latest_path.read_text(encoding="utf-8"))

            total = len(self.seq_map)
            passed = sum(
                1
                for v in latest_data.values()
                if isinstance(v, dict) and v.get("result") == "PASS"
            )
            failed = total - passed

            run_json = {
                "run_id": self.run_id,
                "start_time_utc": self.run_start_utc,
                "run_state": self.run_state,
                "robot_state": self.robot_state,
                "summary": {
                    "total": total,
                    "passed": passed,
                    "failed": failed,
                    "last_updated_utc": utc_now_iso(),
                    "status": "PASS" if failed == 0 else "FAIL",
                },
            }

            write_json(self.out_dir / "run.json", run_json)

            report_rows = build_report_from_events(self.events_path)
            write_json(self.out_dir / "report.json", report_rows)
            write_csv(self.out_dir / "report.csv", report_rows)

        except Exception as e:
            self.get_logger().warn(f"Failed to write run/report artifacts: {e}")


def load_yaml(p: str) -> Dict:
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    cfg_topics = load_yaml("configs/topics.yaml")
    cfg_checkpoints = load_yaml("configs/checkpoints.yaml")
    cfg_model = load_yaml("configs/model.yaml")

    rclpy.init()
    node = IRISInspector(cfg_topics, cfg_checkpoints, cfg_model)
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()