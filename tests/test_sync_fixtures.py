import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SyncFixtureTests(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / "samples" / name).read_text(encoding="utf-8"))

    def test_baseline_has_stable_course_asset_document_task_graph(self):
        data = self.load("sync-baseline-v1.json")
        self.assertEqual(data["contract_version"], "sync-fixture-v1")
        courses = data["courses"]
        self.assertEqual(len(courses), 2)
        course_ids = {item["course_id"] for item in courses}
        self.assertEqual(len(course_ids), 2)
        for course in courses:
            self.assertRegex(course["course_id"], r"^course-[a-z0-9-]+$")
            self.assertEqual(len(course["document_ids"]), 1)
            self.assertEqual(len(course["asset_ids"]), 1)
            self.assertEqual(len(course["task_ids"]), 1)
            document_id = course["document_ids"][0]
            asset_id = course["asset_ids"][0]
            task_id = course["task_ids"][0]
            self.assertIn(document_id, data["documents"])
            self.assertIn(asset_id, data["assets"])
            self.assertIn(task_id, data["tasks"])
            self.assertEqual(data["documents"][document_id]["course_id"], course["course_id"])
            self.assertEqual(data["documents"][document_id]["asset_id"], asset_id)
            self.assertEqual(data["assets"][asset_id]["document_id"], document_id)
            self.assertEqual(data["assets"][asset_id]["course_id"], course["course_id"])
            self.assertEqual(data["tasks"][task_id]["course_id"], course["course_id"])
            self.assertEqual(data["tasks"][task_id]["source_document_id"], document_id)

    def test_sync_cases_preserve_evidence_status_and_links(self):
        data = self.load("sync-cases-v1.json")
        self.assertEqual(
            {case["case_id"] for case in data["cases"]},
            {"SYNC-001-ONLINE", "SYNC-002-OFFLINE", "SYNC-003-FAILURE", "SYNC-004-CONFLICT"},
        )
        for case in data["cases"]:
            before = case["before"]
            after = case["after"]
            self.assertEqual(before["course_id"], after["course_id"])
            self.assertEqual(before["document_id"], after["document_id"])
            self.assertEqual(before["asset_id"], after["asset_id"])
            self.assertEqual(before["task_id"], after["task_id"])
            self.assertEqual(before["evidence_field_ids"], after["evidence_field_ids"])
            self.assertTrue(before["source_quotes"])
            self.assertTrue(after["source_quotes"])
            self.assertIn(case["expected"]["sync_status"], data["allowed_sync_statuses"])

    def test_offline_and_failure_never_claim_completed_sync(self):
        data = self.load("sync-cases-v1.json")
        cases = {case["case_id"]: case for case in data["cases"]}
        self.assertEqual(cases["SYNC-002-OFFLINE"]["expected"]["sync_status"], "离线待同步")
        self.assertEqual(cases["SYNC-003-FAILURE"]["expected"]["sync_status"], "同步失败")
        self.assertTrue(cases["SYNC-003-FAILURE"]["expected"]["local_copy_preserved"])
        self.assertNotEqual(cases["SYNC-002-OFFLINE"]["expected"]["sync_status"], "已同步")
        self.assertNotEqual(cases["SYNC-003-FAILURE"]["expected"]["sync_status"], "已同步")

    def test_conflict_keeps_both_values_and_blocks_silent_overwrite(self):
        data = self.load("sync-cases-v1.json")
        case = next(item for item in data["cases"] if item["case_id"] == "SYNC-004-CONFLICT")
        self.assertEqual(case["expected"]["sync_status"], "冲突待选择")
        self.assertEqual(case["expected"]["resolution"], "用户选择")
        self.assertEqual(case["expected"]["conflict_values"], {
            "device-a": "信息楼301",
            "device-b": "实验楼205",
        })
        self.assertTrue(case["expected"]["both_versions_preserved"])
        self.assertFalse(case["expected"]["silent_overwrite"])


if __name__ == "__main__":
    unittest.main()
