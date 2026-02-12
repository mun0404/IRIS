from __future__ import annotations
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
from src.inspection.writer import ensure_run_dir, append_event, update_latest, save_image

def utc_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

class IRISInspector(Node):
    def __init__(self, cfg_topics: Dict, cfg_checkpoints: Dict, cfg_model: Dict):
        super().__init__("iris_inspector")
        self.bridge = CvBridge()

        self.topics = cfg_topics["camera_topics"]
        self.checkpoints = {c["id"]: c for c in cfg_checkpoints["checkpoints"]}

        self.throttle_hz = float(cfg_model.get("throttle_hz", 2))
        self.min_dt = 1.0 / self.throttle_hz
        self.last_t: Dict[str, float] = {cid: 0.0 for cid in self.topics.keys()}

        self.yolo = YoloInfer(
            weights_path=cfg_model["weights_path"],
            device=cfg_model["device"],
            conf_threshold=cfg_model["conf_threshold"],
            imgsz=cfg_model["imgsz"],
        )

        self.out_dir = ensure_run_dir()
        self.events_path = self.out_dir / "events.jsonl"
        self.latest_path = self.out_dir / "latest.json"
        self.images_dir = self.out_dir / "images"

        for cid, topic in self.topics.items():
            self.get_logger().info(f"Subscribing {cid} -> {topic}")
            self.create_subscription(Image, topic, lambda msg, _cid=cid: self.cb(_cid, msg), 10)

    def cb(self, cid: str, msg: Image):
        now = time.time()
        if now - self.last_t[cid] < self.min_dt:
            return
        self.last_t[cid] = now

        bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        dets = self.yolo.infer(bgr)
        annotated = self.yolo.annotate(bgr)

        expected = self.checkpoints[cid]["expected"]
        conds = evaluate(expected, dets)

        # pass/fail: ignore panel_power placeholder
        gating = [c for c in conds if c.name != "panel_power"]
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
            "timestamp_utc": utc_iso(),
            "checkpoint_id": cid,
            "result": result,
            "conditions": [
                {
                    "name": c.name,
                    "expected": c.expected,
                    "observed": c.observed,
                    "pass": c.passed,
                    "confidence": c.confidence,
                } for c in conds
            ],
            "image_ref": str(img_path),
        }
        append_event(self.events_path, event)

        update_latest(self.latest_path, cid, {
            "updated_utc": event["timestamp_utc"],
            "result": result,
            "reason": reason,
            "image": f"images/{cid}.jpg",
            "conditions": event["conditions"],
        })

def load_yaml(p: str) -> Dict:
    with open(p, "r") as f:
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
