from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.contract_guard import validate_change_proposal, validate_parse_result
from src.input_loader import load_text
from src.notice_diff_adapter import compare_parse_results
from src.parser_adapter import ParserAdapter
from src.recognition import FixtureOcrProvider, JsonOcrProvider, RecognizedDocument, RecognizedLine, RecognitionProvenance


def _read_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: str, value: dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _parse(request_path: str, document: RecognizedDocument, output_path: str) -> None:
    result = ParserAdapter().parse(_read_json(request_path), document)
    if document.provenance.kind == "人工夹具":
        result["warnings"].insert(0, "输入来自人工夹具，仅验证转换管线，不代表真实OCR准确率")
    elif document.provenance.kind == "真实引擎输出":
        result["warnings"].insert(0, f"输入来自真实OCR引擎 {document.provenance.provider} {document.provenance.engine_version}；本次解析结果不等同于准确率统计")
    validate_parse_result(result)
    _write_json(output_path, result)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage-five ParserAdapter reproducible CLI")
    commands = parser.add_subparsers(dest="command", required=True)

    for name in ("parse-text", "parse-real-ocr"):
        command = commands.add_parser(name)
        command.add_argument("--request", required=True)
        command.add_argument("--input", required=True)
        command.add_argument("--output", required=True)

    fixture = commands.add_parser("parse-fixture")
    fixture.add_argument("--request", required=True)
    fixture.add_argument("--input", required=True)
    fixture.add_argument("--ground-truth", required=True)
    fixture.add_argument("--output", required=True)

    compare_command = commands.add_parser("compare")
    compare_command.add_argument("--old", required=True)
    compare_command.add_argument("--new", required=True)
    compare_command.add_argument("--task-map")
    compare_command.add_argument("--output", required=True)

    commands.add_parser("self-check")
    args = parser.parse_args()

    if args.command == "parse-text":
        _parse(args.request, load_text(Path(args.input)), args.output)
    elif args.command == "parse-fixture":
        provider = FixtureOcrProvider({Path(args.input).name: Path(args.ground_truth)})
        _parse(args.request, provider.recognize(Path(args.input)), args.output)
    elif args.command == "parse-real-ocr":
        _parse(args.request, JsonOcrProvider().recognize(Path(args.input)), args.output)
    elif args.command == "compare":
        task_map = _read_json(args.task_map) if args.task_map else {}
        proposal = compare_parse_results(_read_json(args.old), _read_json(args.new), task_map)
        validate_change_proposal(proposal)
        _write_json(args.output, proposal)
    elif args.command == "self-check":
        document = RecognizedDocument(
            lines=(
                RecognizedLine("《软件工程》课程考核说明", "第1行", None, None),
                RecognizedLine("平时成绩占总评成绩的40%。", "第2行", None, None),
                RecognizedLine("期末考试成绩占总评成绩的60%。", "第3行", None, None),
            ),
            provenance=RecognitionProvenance("内置自检", "self-check", None, {}, False),
        )
        result = ParserAdapter().parse({"document_id": "doc-self-check", "category": "课程考核", "sample_id": "COURSE-001-SIMPLE"}, document)
        validate_parse_result(result)
        print("self-check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
