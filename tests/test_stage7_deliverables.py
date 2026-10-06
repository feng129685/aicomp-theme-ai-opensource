import json
import unittest
from pathlib import Path

from src.contract_guard import validate_change_proposal, validate_parse_result


ROOT = Path(__file__).resolve().parents[1]


class Stage7DeliverableTests(unittest.TestCase):
    def load_json(self, relative):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_course_relationships_keep_stable_ids_and_week_view_fields(self):
        relationship = self.load_json("samples/course-relationship-stage7.json")
        baselines = {
            item["document_id"]: item
            for item in (
                self.load_json("samples/baseline/COURSE-001-SIMPLE.parse-result.json"),
                self.load_json("samples/baseline/COURSE-002-NESTED.parse-result.json"),
                self.load_json("samples/baseline/COURSE-003-INCOMPLETE.parse-result.json"),
            )
        }
        courses = relationship["courses"]
        self.assertEqual(len(courses), 3)
        self.assertEqual(len({item["course_id"] for item in courses}), len(courses))
        for item in courses:
            self.assertRegex(item["course_id"], r"^course-[a-z0-9-]+$")
            self.assertEqual(
                set(item["week_view"]),
                {"name", "teacher", "location", "weekday", "start_time", "end_time", "teaching_weeks"},
            )
            self.assertTrue(item["document_ids"])
            self.assertTrue(item["asset_ids"])
            self.assertTrue(item["task_ids"])
            self.assertEqual(len(item["document_ids"]), 1)
            document_id = item["document_ids"][0]
            self.assertIn(document_id, baselines)
            self.assertEqual(
                item["course_id"],
                baselines[document_id]["course_assessment"]["course_id"],
            )
            for link_key in ("document_ids", "asset_ids", "task_ids"):
                self.assertEqual(len(item[link_key]), len(set(item[link_key])))

    def test_notice_004_is_non_conflicting_and_updates_a_stable_task(self):
        old_result = self.load_json("samples/outputs/NOTICE-004-V1.parse-result.json")
        new_result = self.load_json("samples/outputs/NOTICE-004-V2.parse-result.json")
        proposal = self.load_json("samples/outputs/NOTICE-004.change-proposal.json")

        validate_parse_result(old_result)
        validate_parse_result(new_result)
        validate_change_proposal(proposal)
        self.assertEqual(proposal["confirmation_status"], "待确认")
        self.assertEqual(proposal["affected_task_ids"], ["task-notice-004-registration"])
        changed = [diff for diff in proposal["field_diffs"] if diff["type"] != "未变化"]
        self.assertEqual([diff["field_name"] for diff in changed], ["deadline"])
        self.assertEqual(changed[0]["type"], "修改")
        self.assertEqual(changed[0]["affected_task_ids"], proposal["affected_task_ids"])
        self.assertEqual(
            proposal["old_value"],
            {"deadline": old_result["notice"]["deadline"]},
        )
        self.assertEqual(
            proposal["suggested_value"],
            {"deadline": new_result["notice"]["deadline"]},
        )
        self.assertFalse(any(diff["type"] == "冲突待确认" for diff in proposal["field_diffs"]))
        self.assertEqual(old_result["notice"]["matter_id"], new_result["notice"]["matter_id"])


if __name__ == "__main__":
    unittest.main()
