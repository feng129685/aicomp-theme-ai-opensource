import copy
import tempfile
import unittest
from pathlib import Path

from src.contract_guard import ContractError, validate_change_proposal, validate_parse_result
from src.input_loader import load_text
from src.notice_diff_adapter import compare_parse_results
from src.parser_adapter import ParserAdapter


NOTICE_002_V1 = """# 实验室安全培训通知（虚构样例）
请 2026 级软件工程专业本科生参加实验室安全培训。
培训时间为 2026 年 10 月 15 日 14:00，地点为信息楼 301 室。请携带校园卡和签字笔，并于 2026 年 10 月 14 日 18:00 前通过学院事务系统提交报名信息。参加人员须完成线上安全课程。
"""

NOTICE_002_V2 = """# 关于开展实验室安全培训的说明（虚构样例）
本次培训面向软件工程专业 2026 级本科生。
培训安排在 2026 年 10 月 15 日 14:00，培训地点仍是信息楼 301 室。参训同学需带校园卡、签字笔；报名信息请在 2026 年 10 月 14 日 18:00 前提交至学院事务系统。报名条件为已经完成线上安全课程。
"""

NOTICE_003_V1 = """# 程序设计竞赛校内选拔通知（虚构样例）
面向全校在籍本科生。报名截止时间为 2026 年 10 月 18 日 18:00，比赛地点为计算中心 201 室。报名材料为队伍信息表，提交方式为竞赛系统在线提交。参赛者须以 2 至 3 人组队。
"""

NOTICE_003_V2 = """# 程序设计竞赛校内选拔通知（修订稿，虚构样例）
面向全校在籍本科生。正文写明报名截止时间为 2026 年 10 月 20 日 18:00，比赛地点为计算中心 201 室。报名材料为队伍信息表，提交方式为竞赛系统在线提交。参赛者须以 2 至 3 人组队。
附件说明：报名截止时间为 2026 年 10 月 21 日 18:00。
"""


def parse_notice(text, document_id, sample_id, matter_id, version, based_on_version=None):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / f"{sample_id}.md"
        path.write_text(text, encoding="utf-8")
        request = {"document_id": document_id, "category": "竞赛通知", "sample_id": sample_id, "matter_id": matter_id, "version": version, "based_on_version": based_on_version}
        return ParserAdapter().parse(request, load_text(path))


class NoticeIntegrationTests(unittest.TestCase):
    def test_n05_wording_only_change_has_no_affected_tasks(self):
        old = parse_notice(NOTICE_002_V1, "doc-notice-002-v1", "NOTICE-002-V1", "matter-lab-safety-002", "v1")
        new = parse_notice(NOTICE_002_V2, "doc-notice-002-v2", "NOTICE-002-V2", "matter-lab-safety-002", "v2", "v1")

        proposal = compare_parse_results(old, new, {"deadline": ["task-notice-002-registration"]})

        validate_parse_result(old)
        validate_parse_result(new)
        validate_change_proposal(proposal)
        self.assertEqual(old["notice"]["deadline"], "2026-10-14T18:00:00+08:00")
        self.assertEqual(new["notice"]["deadline"], "2026-10-14T18:00:00+08:00")
        self.assertEqual(proposal["affected_task_ids"], [])
        self.assertTrue(all(diff["type"] == "未变化" for diff in proposal["field_diffs"]))

    def test_n06_conflict_stays_unresolved_in_change_proposal(self):
        old = parse_notice(NOTICE_003_V1, "doc-notice-003-v1", "NOTICE-003-V1", "matter-programming-contest-003", "v1")
        new = parse_notice(NOTICE_003_V2, "doc-notice-003-v2", "NOTICE-003-V2", "matter-programming-contest-003", "v2", "v1")

        proposal = compare_parse_results(old, new, {"deadline": ["task-notice-003-registration"]})

        deadline = next(diff for diff in proposal["field_diffs"] if diff["field_name"] == "deadline")
        self.assertEqual(deadline["type"], "冲突待确认")
        self.assertIsNone(deadline["new"])
        self.assertIsNone(proposal["suggested_value"]["deadline"])
        self.assertEqual(proposal["confirmation_status"], "冲突待选择")

    def test_contract_guard_rejects_new_public_field(self):
        result = parse_notice(NOTICE_003_V1, "doc-notice-003-v1", "NOTICE-003-V1", "matter-programming-contest-003", "v1")
        changed = copy.deepcopy(result)
        changed["model_name"] = "not-in-v1"

        with self.assertRaisesRegex(ContractError, "额外字段"):
            validate_parse_result(changed)


if __name__ == "__main__":
    unittest.main()
