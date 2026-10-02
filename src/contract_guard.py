from __future__ import annotations

from typing import Any


class ContractError(ValueError):
    pass


PARSE_KEYS = {"parse_result_id", "document_id", "status", "fields", "course_assessment", "notice", "warnings", "errors"}
EVIDENCE_KEYS = {"field_id", "field_name", "value", "value_type", "confidence", "source_quote", "location", "page", "needs_confirmation", "conflict", "evidence_kind"}
NOTICE_KEYS = {"matter_id", "version", "based_on_version", "title", "audience", "deadline", "location", "materials", "conditions", "submit_method", "extensions", "evidence_field_ids"}
NOTICE_MAP_KEYS = {"title", "audience", "deadline", "location", "materials", "conditions", "submit_method", "team_size", "defense_time", "supplement"}
PROPOSAL_KEYS = {"proposal_id", "matter_id", "old_document_id", "new_document_id", "field_diffs", "affected_task_ids", "old_value", "suggested_value", "evidence", "confirmation_status", "confirmed_at", "confirmed_by"}
DIFF_KEYS = {"diff_id", "field_name", "type", "old", "new", "needs_confirmation", "reason", "evidence_field_ids", "affected_task_ids"}


def _exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    extra = set(value) - expected
    missing = expected - set(value)
    if extra:
        raise ContractError(f"{label} 包含额外字段: {sorted(extra)}")
    if missing:
        raise ContractError(f"{label} 缺少字段: {sorted(missing)}")


def validate_parse_result(result: dict[str, Any]) -> None:
    _exact_keys(result, PARSE_KEYS, "ParseResult")
    if result["status"] not in {"处理中", "成功", "部分成功", "失败", "需人工确认"}:
        raise ContractError("ParseResult status 不在 v1 枚举中")
    if (result["course_assessment"] is None) == (result["notice"] is None):
        raise ContractError("course_assessment 与 notice 必须且只能填写一个")
    field_ids = set()
    for field in result["fields"]:
        _exact_keys(field, EVIDENCE_KEYS, "EvidenceField")
        if field["evidence_kind"] not in {"原文", "推断/计算", "无法确认"}:
            raise ContractError("evidence_kind 不在 v1 枚举中")
        confidence = field["confidence"]
        if confidence is not None and not 0 <= confidence <= 1:
            raise ContractError("confidence 必须为 null 或 0 到 1")
        field_ids.add(field["field_id"])
    if result["notice"] is not None:
        notice = result["notice"]
        _exact_keys(notice, NOTICE_KEYS, "Notice")
        _exact_keys(notice["extensions"], {"team_size", "defense_time", "supplement"}, "Notice.extensions")
        _exact_keys(notice["evidence_field_ids"], NOTICE_MAP_KEYS, "Notice.evidence_field_ids")
        missing_refs = set(notice["evidence_field_ids"].values()) - field_ids
        if missing_refs:
            raise ContractError(f"证据引用不存在: {sorted(missing_refs)}")


def validate_change_proposal(proposal: dict[str, Any]) -> None:
    _exact_keys(proposal, PROPOSAL_KEYS, "ChangeProposal")
    if proposal["confirmation_status"] not in {"待确认", "已接受", "已拒绝", "冲突待选择"}:
        raise ContractError("confirmation_status 不在 v1 枚举中")
    for diff in proposal["field_diffs"]:
        _exact_keys(diff, DIFF_KEYS, "FieldDiff")
        if diff["type"] not in {"新增", "修改", "撤销", "未变化", "冲突待确认"}:
            raise ContractError("差异类型不在 v1 枚举中")
