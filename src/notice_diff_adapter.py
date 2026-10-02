from __future__ import annotations

from typing import Any

from .notice_diff import compare


def _comparison_input(result: dict[str, Any]) -> dict[str, Any]:
    notice = result["notice"]
    if notice is None:
        raise ValueError("只能比较通知 ParseResult")
    value = {**notice, "document_id": result["document_id"]}
    deadline_id = notice["evidence_field_ids"]["deadline"]
    deadline_field = next(field for field in result["fields"] if field["field_id"] == deadline_id)
    if deadline_field["conflict"]:
        value["deadline_conflict"] = deadline_field["conflict"]
        value["deadline_conflict_evidence"] = [deadline_id]
    return value


def compare_parse_results(
    old_result: dict[str, Any],
    new_result: dict[str, Any],
    affected_task_ids_by_field: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    return compare(_comparison_input(old_result), _comparison_input(new_result), affected_task_ids_by_field)
