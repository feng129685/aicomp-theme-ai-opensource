import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_parse_text_writes_contract_shaped_result(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            input_path = base / "course.md"
            request_path = base / "request.json"
            output_path = base / "result.json"
            input_path.write_text("《软件工程》课程考核说明\n平时成绩占总评成绩的40%。\n期末考试成绩占总评成绩的60%。\n", encoding="utf-8")
            request_path.write_text(json.dumps({"document_id":"doc-course-001","category":"课程考核","sample_id":"COURSE-001-SIMPLE"}, ensure_ascii=False), encoding="utf-8")

            completed = subprocess.run([sys.executable, "cli.py", "parse-text", "--request", str(request_path), "--input", str(input_path), "--output", str(output_path)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(result["course_assessment"]["items"][0]["weight"], 0.4)
            self.assertEqual(result["errors"], [])

    def test_parse_fixture_adds_non_accuracy_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            image = base / "OCR-001-CLEAR.png"
            truth = base / "OCR-001-CLEAR.txt"
            request = base / "request.json"
            output = base / "result.json"
            image.write_bytes(b"fixture")
            truth.write_text("《软件工程》课程考核说明\n平时成绩占总评成绩的40%。\n期末考试成绩占总评成绩的60%。\n", encoding="utf-8")
            request.write_text(json.dumps({"document_id":"doc-course-ocr-001","category":"课程考核","sample_id":"COURSE-001-SIMPLE"}, ensure_ascii=False), encoding="utf-8")

            completed = subprocess.run([sys.executable, "cli.py", "parse-fixture", "--request", str(request), "--input", str(image), "--ground-truth", str(truth), "--output", str(output)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")

            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertIn("人工夹具", result["warnings"][0])
            self.assertIn("不代表真实OCR准确率", result["warnings"][0])

    def test_self_check_returns_success(self):
        completed = subprocess.run([sys.executable, "cli.py", "self-check"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("self-check passed", completed.stdout)


if __name__ == "__main__":
    unittest.main()
