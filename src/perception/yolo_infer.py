from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict
from ultralytics import YOLO

@dataclass
class Detection:
    cls_name: str
    conf: float
    xyxy: List[float]

class YoloInfer:
    def __init__(self, weights_path: str, device: str, conf_threshold: float, imgsz: int):
        self.model = YOLO(weights_path)
        self.device = device
        self.conf = float(conf_threshold)
        self.imgsz = int(imgsz)
        self.names: Dict[int, str] = self.model.names

    def infer(self, bgr_img) -> List[Detection]:
        res = self.model.predict(
            source=bgr_img,
            device=self.device,
            conf=self.conf,
            imgsz=self.imgsz,
            verbose=False,
        )[0]
        dets: List[Detection] = []
        if res.boxes is None:
            return dets
        for i in range(len(res.boxes)):
            cls_id = int(res.boxes.cls[i].item())
            conf = float(res.boxes.conf[i].item())
            xyxy = res.boxes.xyxy[i].tolist()
            dets.append(Detection(self.names[cls_id], conf, xyxy))
        return dets

    def annotate(self, bgr_img):
        res = self.model.predict(
            source=bgr_img,
            device=self.device,
            conf=self.conf,
            imgsz=self.imgsz,
            verbose=False,
        )[0]
        return res.plot()
