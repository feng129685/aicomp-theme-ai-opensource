"""Pure ChangeProposal generation; no task or reminder side effects."""

from __future__ import annotations

import copy
from typing import Any

FIELDS = ("title", "audience", "deadline", "location", "materials", "conditions", "submit_method")


def compare(old: dict[str, Any], new: dict[str, Any], affected_task_ids_by_field: dict[str, list[str]] | None = None) -> dict[str, Any]:
    if old.get("matter_id") != new.get("matter_id"):
        raise ValueError("只能比较相同 matter_id 的通知")
    affected_task_ids_by_field = affected_task_ids_by_field or {}
    diffs = []
    evidence = []
    for field in FIELDS:
        old_value = old.get(field)
        new_value = new.get(field)
        kind = "未变化" if old_value == new_value else ("新增" if old_value is None else "撤销" if new_value is None else "修改")
        needs = kind != "未变化"
        reason = None
        if field == "deadline" and new.get("deadline_conflict"):
            kind, needs, new_value = "冲突待确认", True, None
            reason = new["deadline_conflict"]
        ids = list(affected_task_ids_by_field.get(field, [])) if needs else []
        old_document = str(old.get("document_id", "")).removeprefix("doc-")
        new_document = str(new.get("document_id", "")).removeprefix("doc-")
        field_key = field.replace("submit_method", "submit-method")
        old_id = f"field-{old_document}-{field_key}"
        new_id = f"field-{new_document}-{field_key}"
        refs = [old_id, new_id]
        if reason and new.get("deadline_conflict_evidence"):
            refs.extend(new["deadline_conflict_evidence"])
        evidence.extend(refs)
        # Keep the diff identifier stable across document revisions; the field
        # evidence IDs still distinguish the old and new source versions.
        diff_document = old_document.rsplit("-", 1)[0]
        diffs.append({"diff_id": f"diff-{diff_document}-{field_key}", "field_name": field, "type": kind, "old": old_value, "new": new_value, "needs_confirmation": needs, "reason": reason, "evidence_field_ids": refs, "affected_task_ids": ids})
    changed_fields = [d["field_name"] for d in diffs if d["type"] != "未变化"]
    snapshot_fields = changed_fields or list(FIELDS)
    old_value = {field: old.get(field) for field in snapshot_fields}
    suggested = {
        field: (None if d["type"] == "冲突待确认" else d["new"])
        for field, d in zip(FIELDS, diffs)
        if field in snapshot_fields
    }
    affected = sorted({task for d in diffs for task in d["affected_task_ids"]})
    conflict = any(d["type"] == "冲突待确认" for d in diffs)
    old_document = str(old["document_id"]).removeprefix("doc-")
    new_document = str(new["document_id"]).removeprefix("doc-")
    new_version = new_document.rsplit("-", 1)[-1]
    return {"proposal_id": f"proposal-{old_document}-to-{new_version}", "matter_id": old["matter_id"], "old_document_id": old["document_id"], "new_document_id": new["document_id"], "field_diffs": diffs, "affected_task_ids": affected, "old_value": old_value, "suggested_value": suggested, "evidence": evidence, "confirmation_status": "冲突待选择" if conflict else "待确认", "confirmed_at": None, "confirmed_by": None}
