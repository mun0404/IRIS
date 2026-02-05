"""
IRIS - Inspection & Reporting Intelligence System

Checkpoint definitions for the demo inspection scenario.

Checkpoints define:
- WHAT is being inspected (description)
- WHERE inputs are organized (checkpoint_id maps to data/checkpoint_XX/)
- WHAT is expected (expected_condition)

Condition evaluation is handled separately by reusable evaluators:
- door_state
- indicator_light_state
- pathway_clearance
"""

CHECKPOINTS = [
    {
        "checkpoint_id": "CP-01",
        "description": "Main entry door to equipment room",
        "condition_type": "door_state",
        "expected_condition": {"door_state": "closed"},
    },
    {
        "checkpoint_id": "CP-02",
        "description": "Primary network rack access door",
        "condition_type": "door_state",
        "expected_condition": {"door_state": "closed"},
    },
    {
        "checkpoint_id": "CP-03",
        "description": "Cold aisle containment panels and end-of-aisle seals",
        "condition_type": "pathway_clearance",
        "expected_condition": {"pathway_clearance": "clear"},
    },
    {
        "checkpoint_id": "CP-04",
        "description": "Core network switch status indicator light",
        "condition_type": "indicator_light_state",
        "expected_condition": {"indicator_light_state": "on"},
    },
    {
        "checkpoint_id": "CP-05",
        "description": "Cold aisle walkway sightline between equipment racks",
        "condition_type": "pathway_clearance",
        "expected_condition": {"pathway_clearance": "clear"},
    },
    {
        "checkpoint_id": "CP-07",
        "description": "Emergency exit indicator light above exit door",
        "condition_type": "indicator_light_state",
        "expected_condition": {"indicator_light_state": "on"},
    },
]