from __future__ import annotations

from pathlib import Path

from src.checkpoint_definitions import CHECKPOINTS
from src.schemas import CheckpointResult, InspectionRunSummary
from src.utils.io import write_json
from src.utils.time_utils import utc_now_iso


def _checkpoint_data_dir(checkpoint_id: str) -> Path:
    # Map CP-01 -> data/checkpoint_01/images
    cp_num = checkpoint_id.split("-")[1]
    return Path("data") / f"checkpoint_{cp_num}" / "images"


def _pick_image_reference(checkpoint_id: str) -> str:
    """
    For demo: pick the first image if available, else return a placeholder reference.
    """
    img_dir = _checkpoint_data_dir(checkpoint_id)
    if img_dir.exists():
        images = sorted([p for p in img_dir.iterdir() if p.is_file()])
        if images:
            return str(images[0])
    return f"{img_dir}/<no_image_provided>"


def _evaluate_demo(expected_value: str) -> tuple[str, str, float, str]:
    """
    Demo evaluator: assumes expected == observed so output is PASS.
    Replace this later with real rule-based / ML logic.
    """
    observed = expected_value
    result = "pass"
    confidence = 1.0
    notes = "demo_mode: observed assumed equal to expected"
    return observed, result, confidence, notes


def run_inspection(run_id: str = "001") -> None:
    ts = utc_now_iso()
    results: list[CheckpointResult] = []
    issues: list[dict] = []

    for cp in CHECKPOINTS:
        checkpoint_id = cp["checkpoint_id"]
        condition = cp["condition_type"]  # e.g., door_state
        expected_map = cp["expected_condition"]  # e.g., {"door_state": "closed"}
        expected_value = expected_map[condition]

        image_ref = _pick_image_reference(checkpoint_id)

        observed, outcome, conf, notes = _evaluate_demo(expected_value)

        if outcome != "pass":
            issues.append({"checkpoint_id": checkpoint_id, "issue": f"{condition} expected {expected_value} observed {observed}"})

        results.append(
            CheckpointResult(
                timestamp=ts,
                checkpoint_id=checkpoint_id,
                condition_evaluated=condition,
                expected=expected_value,
                observed=observed,
                result=outcome,
                image_reference=image_ref,
                confidence=conf,
                notes=notes,
            )
        )

    passed = sum(1 for r in results if r.result == "pass")
    flagged = sum(1 for r in results if r.result == "fail")
    total = len(results)

    summary = InspectionRunSummary(
        run_id=run_id,
        timestamp=ts,
        total_checkpoints=total,
        passed=passed,
        flagged=flagged,
        issues=issues,
    )

    # Outputs (as requested)
    write_json(Path("outputs") / f"iris_run_{run_id}.json", [r.to_dict() for r in results])
    write_json(Path("outputs") / f"iris_run_{run_id}_summary.json", summary.to_dict())