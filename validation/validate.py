from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.contract_guard import validate_change_proposal, validate_parse_result


def main() -> None:
    output_dir = ROOT / "samples" / "outputs"
    parse_files = sorted(output_dir.glob("*.parse-result.json"))
    proposal_files = sorted(output_dir.glob("*.change-proposal.json"))
    if len(parse_files) != 9 or len(proposal_files) != 2:
        raise AssertionError(f"输出数量不符: ParseResult={len(parse_files)}, ChangeProposal={len(proposal_files)}")
    for path in parse_files:
        validate_parse_result(json.loads(path.read_text(encoding="utf-8")))
        print(f"PASS ParseResult: {path.name}")
    for path in proposal_files:
        validate_change_proposal(json.loads(path.read_text(encoding="utf-8")))
        print(f"PASS ChangeProposal: {path.name}")

    course_003 = json.loads((output_dir / "COURSE-003-INCOMPLETE.parse-result.json").read_text(encoding="utf-8"))
    assert course_003["course_assessment"]["calculable"] is False
    assert course_003["course_assessment"]["calculation_block_reason"] == "期末考试权重未给出"
    assert course_003["course_assessment"]["items"][2]["weight"] is None

    n05 = json.loads((output_dir / "NOTICE-002.change-proposal.json").read_text(encoding="utf-8"))
    assert n05["affected_task_ids"] == []
    assert all(diff["type"] == "未变化" for diff in n05["field_diffs"])

    n06 = json.loads((output_dir / "NOTICE-003.change-proposal.json").read_text(encoding="utf-8"))
    deadline = next(diff for diff in n06["field_diffs"] if diff["field_name"] == "deadline")
    assert deadline["type"] == "冲突待确认"
    assert deadline["new"] is None
    assert n06["suggested_value"]["deadline"] is None
    print("PASS frozen edge cases: incomplete course, unchanged notice, conflicting deadline")


if __name__ == "__main__":
    main()
