import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    return json.loads((ROOT / "samples" / name).read_text(encoding="utf-8"))


def validate():
    baseline = load("sync-baseline-v1.json")
    cases = load("sync-cases-v1.json")
    ids = {
        "course_id": {item["course_id"] for item in baseline["courses"]},
        "document_id": set(baseline["documents"]),
        "asset_id": set(baseline["assets"]),
        "task_id": set(baseline["tasks"]),
    }

    for course in baseline["courses"]:
        document_id = course["document_ids"][0]
        asset_id = course["asset_ids"][0]
        task_id = course["task_ids"][0]
        assert document_id in ids["document_id"]
        assert asset_id in ids["asset_id"]
        assert task_id in ids["task_id"]
        document = baseline["documents"][document_id]
        asset = baseline["assets"][asset_id]
        task = baseline["tasks"][task_id]
        assert document["course_id"] == course["course_id"]
        assert document["asset_id"] == asset_id
        assert asset["document_id"] == document_id
        assert asset["course_id"] == course["course_id"]
        assert task["course_id"] == course["course_id"]
        assert task["source_document_id"] == document_id
    for case in cases["cases"]:
        for side in ("before", "after"):
            snapshot = case[side]
            for key, allowed in ids.items():
                assert snapshot[key] in allowed, f"{case['case_id']} {side} {key} 不在基线中"
            evidence = baseline["parse_evidence"][snapshot["document_id"]]
            assert snapshot["evidence_field_ids"] == evidence["evidence_field_ids"]
            assert snapshot["source_quotes"] == evidence["source_quotes"]
            assert snapshot["parse_status"] == evidence["status"]
        assert case["expected"]["sync_status"] in cases["allowed_sync_statuses"]

    assert baseline["not_synced"] == ["grade_scenario_inputs", "grade_scenario_results"]
    print(f"Validated {len(baseline['courses'])} courses and {len(cases['cases'])} sync cases")


if __name__ == "__main__":
    validate()
