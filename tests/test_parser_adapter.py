import tempfile
import unittest
from pathlib import Path

from src.input_loader import load_text
from src.parser_adapter import ParserAdapter


def parse_text(text, request):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.md"
        path.write_text(text, encoding="utf-8")
        return ParserAdapter().parse(request, load_text(path))


class ParserAdapterTests(unittest.TestCase):
    def test_official_markdown_spacing_parses_simple_nested_and_incomplete_courses(self):
        simple = parse_text(
            "《软件工程》课程考核说明\n- 平时成绩占总评成绩的 40%；\n- 期末考试成绩占总评成绩的 60%。\n",
            {"document_id":"doc-course-001","category":"课程考核","sample_id":"COURSE-001-SIMPLE"},
        )
        nested = parse_text(
            "《数据库系统》课程考核说明\n过程性考核占总评成绩的 50%，其中作业占过程性考核的 40%，实验占过程性考核的 60%。期末考试占总评成绩的 50%。\n",
            {"document_id":"doc-course-002","category":"课程考核","sample_id":"COURSE-002-NESTED"},
        )
        incomplete = parse_text(
            "《计算机网络》课程考核说明\n- 平时表现占总评成绩的 30%；\n- 实验占总评成绩的 30%；\n- 期末考试占总评成绩的一部分，具体比例另行通知。\n",
            {"document_id":"doc-course-003","category":"课程考核","sample_id":"COURSE-003-INCOMPLETE"},
        )

        self.assertEqual([item["weight"] for item in simple["course_assessment"]["items"]], [0.4, 0.6])
        self.assertTrue(simple["course_assessment"]["calculable"])
        self.assertEqual(nested["course_assessment"]["items"][0]["children"][1]["weight"], 0.6)
        self.assertTrue(nested["course_assessment"]["calculable"])
        self.assertEqual([item["weight"] for item in incomplete["course_assessment"]["items"]], [0.3, 0.3, None])

    def test_simple_course_keeps_weight_quotes_and_is_calculable(self):
        result = parse_text(
            "# 《软件工程》课程考核说明\n平时成绩占总评成绩的40%。\n期末考试成绩占总评成绩的60%。\n",
            {"document_id": "doc-course-001", "category": "课程考核", "sample_id": "COURSE-001-SIMPLE"},
        )

        self.assertEqual(set(result), {"parse_result_id", "document_id", "status", "fields", "course_assessment", "notice", "warnings", "errors"})
        self.assertEqual(result["status"], "成功")
        self.assertIsNone(result["notice"])
        self.assertTrue(result["course_assessment"]["calculable"])
        self.assertEqual([item["weight"] for item in result["course_assessment"]["items"]], [0.4, 0.6])
        weight_fields = [field for field in result["fields"] if field["field_name"] == "weight"]
        self.assertEqual(weight_fields[0]["source_quote"], "平时成绩占总评成绩的40%。")
        self.assertEqual(weight_fields[0]["location"], "第2行")
        self.assertIsNone(weight_fields[0]["confidence"])
        self.assertFalse(weight_fields[0]["needs_confirmation"])

    def test_incomplete_course_does_not_guess_missing_final_weight(self):
        result = parse_text(
            "# 《计算机网络》课程考核说明\n平时表现占总评成绩的30%。\n实验占总评成绩的30%。\n期末考试占总评成绩的一部分，具体比例另行通知。\n",
            {"document_id": "doc-course-003", "category": "课程考核", "sample_id": "COURSE-003-INCOMPLETE"},
        )

        final_item = result["course_assessment"]["items"][2]
        self.assertIsNone(final_item["weight"])
        self.assertFalse(result["course_assessment"]["calculable"])
        self.assertEqual(result["course_assessment"]["calculation_block_reason"], "期末考试权重未给出")
        final_evidence = next(field for field in result["fields"] if field["field_id"] in final_item["evidence_field_ids"])
        self.assertIsNone(final_evidence["value"])
        self.assertTrue(final_evidence["needs_confirmation"])
        self.assertEqual(final_evidence["evidence_kind"], "无法确认")

    def test_notice_keeps_evidence_for_every_extracted_value(self):
        result = parse_text(
            "# 实验室安全培训通知\n请2026级软件工程专业本科生参加培训。\n报名截止时间为2026年10月14日18:00，地点为信息楼301室。\n请携带校园卡和签字笔，通过学院事务系统提交报名信息。\n参加人员须完成线上安全课程。\n",
            {"document_id": "doc-notice-002-v1", "category": "竞赛通知", "sample_id": "NOTICE-002-V1", "matter_id": "matter-lab-safety-002", "version": "v1", "based_on_version": None},
        )

        self.assertEqual(result["notice"]["deadline"], "2026-10-14T18:00:00+08:00")
        deadline_id = result["notice"]["evidence_field_ids"]["deadline"]
        deadline = next(field for field in result["fields"] if field["field_id"] == deadline_id)
        self.assertIn("2026年10月14日18:00", deadline["source_quote"])
        self.assertEqual(deadline["location"], "第3行")
        self.assertFalse(deadline["needs_confirmation"])

    def test_conflicting_deadlines_are_not_resolved_by_parser(self):
        result = parse_text(
            "# 程序设计竞赛校内选拔通知\n正文写明报名截止时间为2026年10月20日18:00。\n附件说明：报名截止时间为2026年10月21日18:00。\n",
            {"document_id": "doc-notice-003-v2", "category": "竞赛通知", "sample_id": "NOTICE-003-V2", "matter_id": "matter-programming-contest-003", "version": "v2", "based_on_version": "v1"},
        )

        self.assertEqual(result["status"], "需人工确认")
        self.assertIsNone(result["notice"]["deadline"])
        deadline = next(field for field in result["fields"] if field["field_name"] == "deadline")
        self.assertTrue(deadline["needs_confirmation"])
        self.assertIn("2026-10-20T18:00:00+08:00", deadline["conflict"])
        self.assertIn("2026-10-21T18:00:00+08:00", deadline["conflict"])


if __name__ == "__main__":
    unittest.main()
