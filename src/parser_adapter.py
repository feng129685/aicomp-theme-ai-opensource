from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from .recognition import RecognizedDocument, RecognizedLine


NOTICE_FIELDS = ("title", "audience", "deadline", "location", "materials", "conditions", "submit_method")
EXTENSION_FIELDS = ("team_size", "defense_time", "supplement")


def _iso_datetime(value: str) -> str:
    compact = re.sub(r"\s+", "", value)
    match = re.fullmatch(r"(\d{4})年(\d{1,2})月(\d{1,2})日(\d{1,2}):([0-5]\d)", compact)
    if not match:
        raise ValueError(f"无法规范化时间: {value}")
    year, month, day, hour, minute = (int(part) for part in match.groups())
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00+08:00"


def _find_line(lines: Iterable[RecognizedLine], pattern: str) -> tuple[Optional[RecognizedLine], Optional[re.Match[str]]]:
    compiled = re.compile(pattern)
    for line in lines:
        match = compiled.search(line.text)
        if match:
            return line, match
    return None, None


@dataclass
class _EvidenceBuilder:
    document_id: str
    fields: list[dict[str, Any]]

    def add(
        self,
        name: str,
        value: Any,
        value_type: str,
        line: Optional[RecognizedLine],
        *,
        suffix: Optional[str] = None,
        needs_confirmation: bool = False,
        conflict: Optional[str] = None,
        evidence_kind: str = "原文",
    ) -> str:
        token = self.document_id.removeprefix("doc-")
        field_id = f"field-{token}-{suffix or name.replace('_', '-')}"
        self.fields.append(
            {
                "field_id": field_id,
                "field_name": name,
                "value": value,
                "value_type": value_type,
                "confidence": line.confidence if line else None,
                "source_quote": line.text if line else None,
                "location": line.location if line else "原文未提供",
                "page": line.page if line else None,
                "needs_confirmation": needs_confirmation,
                "conflict": conflict,
                "evidence_kind": evidence_kind,
            }
        )
        return field_id


class ParserAdapter:
    def parse(self, request: dict[str, Any], document: RecognizedDocument) -> dict[str, Any]:
        document_id = request["document_id"]
        base = {
            "parse_result_id": f"parse-{document_id.removeprefix('doc-')}",
            "document_id": document_id,
            "status": "失败",
            "fields": [],
            "course_assessment": None,
            "notice": None,
            "warnings": [],
            "errors": [],
        }
        if not document.lines:
            base["errors"].append("未识别到可用文字")
            return base
        if request.get("category") == "课程考核":
            return self._parse_course(request, document, base)
        return self._parse_notice(request, document, base)

    def _parse_course(self, request: dict[str, Any], document: RecognizedDocument, result: dict[str, Any]) -> dict[str, Any]:
        evidence = _EvidenceBuilder(request["document_id"], result["fields"])
        title_line, title_match = _find_line(document.lines, r"《([^》]+)》")
        course_name = title_match.group(1) if title_match else request.get("sample_id", "未命名课程")
        evidence.add("course_title", course_name, "string", title_line)

        items: list[dict[str, Any]] = []
        nested_line, nested = _find_line(
            document.lines,
            r"过程性考核占总评成绩的\s*(\d+(?:\.\d+)?)%.*?作业占过程性考核的\s*(\d+(?:\.\d+)?)%.*?实验占过程性考核的\s*(\d+(?:\.\d+)?)%.*?期末考试占总评成绩的\s*(\d+(?:\.\d+)?)%",
        )
        if nested:
            top, homework, lab, final = (float(value) / 100 for value in nested.groups())
            top_id = evidence.add("weight", top, "number", nested_line, suffix="process-weight")
            homework_id = evidence.add("weight", homework, "number", nested_line, suffix="homework-weight")
            lab_id = evidence.add("weight", lab, "number", nested_line, suffix="lab-weight")
            final_id = evidence.add("weight", final, "number", nested_line, suffix="final-weight")
            items = [
                {"item_id": "item-process", "name": "过程性考核", "weight": top, "children": [
                    {"item_id": "item-homework", "name": "作业", "weight": homework, "children": [], "evidence_field_ids": [homework_id]},
                    {"item_id": "item-lab", "name": "实验", "weight": lab, "children": [], "evidence_field_ids": [lab_id]},
                ], "evidence_field_ids": [top_id]},
                {"item_id": "item-final", "name": "期末考试成绩", "weight": final, "children": [], "evidence_field_ids": [final_id]},
            ]
        else:
            weight_pattern = re.compile(r"(平时成绩|平时表现|实验|期末考试成绩|期末考试)占总评成绩的\s*(\d+(?:\.\d+)?)%")
            for line in document.lines:
                match = weight_pattern.search(line.text)
                if not match:
                    continue
                name, raw_weight = match.groups()
                field_id = evidence.add("weight", float(raw_weight) / 100, "number", line, suffix=f"{len(items) + 1}-weight")
                items.append({"item_id": f"item-{len(items) + 1}", "name": name, "weight": float(raw_weight) / 100, "children": [], "evidence_field_ids": [field_id]})
            missing_line, missing = _find_line(document.lines, r"(期末考试(?:成绩)?)占总评成绩的一部分.*?(?:具体比例|权重).*(?:另行通知|未给出)")
            if missing:
                field_id = evidence.add("weight", None, "null", missing_line, suffix="final-weight", needs_confirmation=True, conflict="期末考试权重未给出", evidence_kind="无法确认")
                items.append({"item_id": f"item-{len(items) + 1}", "name": missing.group(1), "weight": None, "children": [], "evidence_field_ids": [field_id]})

        missing_weight = next((item for item in items if item["weight"] is None), None)
        top_sum_valid = bool(items) and missing_weight is None and abs(sum(item["weight"] for item in items) - 1.0) < 1e-9
        child_sums_valid = all(not item["children"] or abs(sum(child["weight"] for child in item["children"]) - 1.0) < 1e-9 for item in items)
        sums_valid = top_sum_valid and child_sums_valid
        block_reason = f"{missing_weight['name']}权重未给出" if missing_weight else (None if sums_valid else "同一层权重合计必须为1")
        result["course_assessment"] = {
            "course_id": f"course-{request.get('sample_id', request['document_id']).lower()}",
            "formula_type": "weighted_sum",
            "items": items,
            "calculable": sums_valid,
            "calculation_block_reason": block_reason,
        }
        result["status"] = "成功" if sums_valid else "需人工确认"
        if not items:
            result["status"] = "失败"
            result["errors"].append("未识别到受支持的课程权重结构")
        return result

    def _parse_notice(self, request: dict[str, Any], document: RecognizedDocument, result: dict[str, Any]) -> dict[str, Any]:
        evidence = _EvidenceBuilder(request["document_id"], result["fields"])
        values: dict[str, Any] = {}
        evidence_ids: dict[str, str] = {}

        title_line = document.lines[0]
        title = re.sub(r"^[#\s]+", "", title_line.text)
        title = re.sub(r"（[^）]*(?:修订稿|虚构样例)[^）]*）", "", title).strip()
        if title.startswith("关于开展") and title.endswith("的说明"):
            title = title.removeprefix("关于开展").removesuffix("的说明").strip() + "通知"
        values["title"] = title
        evidence_ids["title"] = evidence.add("title", title, "string", title_line)

        extractors = {
            "audience": r"((?:20\s*\d{2}\s*级[^。；，]*?本科生)|(?:软件工程专业\s*20\s*\d{2}\s*级本科生)|全校在籍本科生|全校本科生)",
            "location": r"(?:地点(?:仍是|为|：)?|培训地点：|比赛地点：)\s*([^。；，]+)",
            "conditions": r"(?:须|条件为|报名条件为)([^。；]+)",
            "submit_method": r"((?:通过|提交方式为)[^。；，]*(?:系统|在线提交)[^。；，]*)",
        }
        for name, pattern in extractors.items():
            line, match = _find_line(document.lines, pattern)
            value = match.group(1).strip() if match else None
            if name == "audience" and value:
                value = re.sub(r"\s+", "", value)
                audience_year = re.search(r"(20\d{2})级", value)
                if audience_year and value.startswith("软件工程专业"):
                    value = f"{audience_year.group(1)}级软件工程专业本科生"
            if name == "location" and value:
                value = re.sub(r"\s+", "", value)
            if name == "conditions" and value:
                value = value.removeprefix("已经")
            if name == "submit_method" and value:
                value = re.sub(r"^提交方式为", "", value).strip()
            values[name] = value
            evidence_ids[name] = evidence.add(name, value, "string" if value is not None else "null", line, needs_confirmation=value is None, evidence_kind="原文" if value is not None else "无法确认")

        system_line, _ = _find_line(document.lines, r"学院事务系统")
        if system_line and re.search(r"(?:提交报名信息|报名信息.*提交至学院事务系统)", system_line.text):
            values["submit_method"] = "通过学院事务系统提交报名信息"
            for field in result["fields"]:
                if field["field_id"] == evidence_ids["submit_method"]:
                    field.update({"value": values["submit_method"], "value_type": "string", "source_quote": system_line.text, "location": system_line.location, "page": system_line.page, "confidence": system_line.confidence, "needs_confirmation": False, "evidence_kind": "原文"})

        materials_line, materials_match = _find_line(document.lines, r"(?:请携带|需带|报名材料为|材料：)([^。；]+)")
        materials = None
        if materials_match:
            raw = re.split(r"，?并于|，?报名", materials_match.group(1))[0].strip()
            materials = [part.strip() for part in re.split(r"[、，和]", raw) if part.strip()]
        values["materials"] = materials
        evidence_ids["materials"] = evidence.add("materials", materials, "string_array" if materials is not None else "null", materials_line, needs_confirmation=materials is None, evidence_kind="原文" if materials is not None else "无法确认")

        deadline_hits: list[tuple[RecognizedLine, str]] = []
        deadline_pattern = re.compile(r"(?:报名)?截止(?:时间|：)?(?:为)?\s*(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日\s*\d{1,2}:[0-5]\d)")
        for line in document.lines:
            for match in deadline_pattern.finditer(line.text):
                deadline_hits.append((line, _iso_datetime(match.group(1))))
        if not deadline_hits:
            before_pattern = re.compile(r"(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日\s*\d{1,2}:[0-5]\d)\s*前")
            for line in document.lines:
                for match in before_pattern.finditer(line.text):
                    deadline_hits.append((line, _iso_datetime(match.group(1))))
        unique_deadlines = list(dict.fromkeys(value for _, value in deadline_hits))
        if len(unique_deadlines) == 1:
            values["deadline"] = unique_deadlines[0]
            evidence_ids["deadline"] = evidence.add("deadline", unique_deadlines[0], "datetime", deadline_hits[0][0])
        elif len(unique_deadlines) > 1:
            conflict = "候选截止时间冲突：" + "；".join(unique_deadlines)
            values["deadline"] = None
            evidence_ids["deadline"] = evidence.add("deadline", None, "null", deadline_hits[0][0], needs_confirmation=True, conflict=conflict, evidence_kind="无法确认")
        else:
            values["deadline"] = None
            evidence_ids["deadline"] = evidence.add("deadline", None, "null", None, needs_confirmation=True, evidence_kind="无法确认")

        extension_ids = {}
        for name in EXTENSION_FIELDS:
            extension_ids[name] = evidence.add(name, None, "null", None, needs_confirmation=True, evidence_kind="无法确认")

        result["notice"] = {
            "matter_id": request.get("matter_id", f"matter-{request.get('sample_id', request['document_id']).lower()}"),
            "version": request.get("version", "v1"),
            "based_on_version": request.get("based_on_version"),
            **values,
            "extensions": {name: None for name in EXTENSION_FIELDS},
            "evidence_field_ids": {**evidence_ids, **extension_ids},
        }
        has_conflict = len(unique_deadlines) > 1
        missing = [name for name in NOTICE_FIELDS if values.get(name) is None]
        result["status"] = "需人工确认" if has_conflict else ("部分成功" if missing else "成功")
        if missing and not has_conflict:
            result["warnings"].append("以下字段未从原文确认：" + "、".join(missing))
        return result
