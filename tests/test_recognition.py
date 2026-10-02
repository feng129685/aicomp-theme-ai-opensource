import tempfile
import unittest
from pathlib import Path

from src.input_loader import load_text
from src.recognition import FixtureOcrProvider, JsonOcrProvider, RecognitionError


class RecognitionTests(unittest.TestCase):
    def test_load_text_preserves_nonempty_line_locations(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notice.md"
            path.write_text("标题\n\n截止时间：2026年10月18日18:00\n", encoding="utf-8")

            document = load_text(path)

        self.assertEqual([line.text for line in document.lines], ["标题", "截止时间：2026年10月18日18:00"])
        self.assertEqual([line.location for line in document.lines], ["第1行", "第3行"])
        self.assertEqual([line.page for line in document.lines], [None, None])
        self.assertTrue(all(line.confidence is None for line in document.lines))
        self.assertEqual(document.provenance.kind, "原始文本")
        self.assertFalse(document.provenance.is_measured_accuracy)

    def test_fixture_provider_labels_output_as_fixture_not_real_accuracy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "OCR-001-CLEAR.png"
            truth = root / "OCR-001-CLEAR.txt"
            image.write_bytes(b"not-decoded-by-fixture-provider")
            truth.write_text("软件工程\n平时成绩占40%\n", encoding="utf-8")

            document = FixtureOcrProvider({image.name: truth}).recognize(image)

        self.assertEqual(document.lines[0].text, "软件工程")
        self.assertEqual(document.lines[0].page, 1)
        self.assertEqual(document.provenance.kind, "人工夹具")
        self.assertFalse(document.provenance.is_measured_accuracy)
        self.assertIsNone(document.provenance.engine_version)

    def test_fixture_provider_rejects_blank_ground_truth(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "OCR-004-BLANK.png"
            truth = root / "OCR-004-BLANK.txt"
            image.write_bytes(b"blank-image-placeholder")
            truth.write_text("\n", encoding="utf-8")

            with self.assertRaisesRegex(RecognitionError, "未识别到可用文字"):
                FixtureOcrProvider({image.name: truth}).recognize(image)

    def test_json_provider_requires_engine_version_and_keeps_line_confidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ocr-result.json"
            path.write_text(
                '{"engine":"PaddleOCR","engine_version":"3.0.0","parameters":{"lang":"ch"},'
                '"lines":[{"text":"报名截止时间为2026年10月18日18:00","location":"第1页区域(10,20,400,60)","page":1,"confidence":0.97}]}',
                encoding="utf-8",
            )

            document = JsonOcrProvider().recognize(path)

        self.assertEqual(document.provenance.kind, "真实引擎输出")
        self.assertEqual(document.provenance.engine_version, "3.0.0")
        self.assertFalse(document.provenance.is_measured_accuracy)
        self.assertEqual(document.lines[0].confidence, 0.97)

    def test_json_provider_rejects_missing_engine_version(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ocr-result.json"
            path.write_text('{"engine":"unknown","lines":[]}', encoding="utf-8")

            with self.assertRaisesRegex(RecognitionError, "engine_version"):
                JsonOcrProvider().recognize(path)


if __name__ == "__main__":
    unittest.main()
