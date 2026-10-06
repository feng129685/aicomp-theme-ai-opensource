import tempfile
import unittest
from pathlib import Path

from src.easyocr_provider import EasyOcrProvider, OcrEngineError, load_document_images


class FakeReader:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def readtext(self, image, detail=1, paragraph=False):
        self.calls.append((image, detail, paragraph))
        return self.result


class EasyOcrProviderTests(unittest.TestCase):
    def test_image_file_becomes_recognized_lines_with_coordinates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notice.png"
            path.write_bytes(b"synthetic-image")
            reader = FakeReader([([[10, 20], [110, 20], [110, 50], [10, 50]], "报名截止时间为2026年10月18日18:00", 0.93)])

            document = EasyOcrProvider(reader=reader, engine_version="easyocr-test").recognize_file(path)

        self.assertEqual(document.lines[0].text, "报名截止时间为2026年10月18日18:00")
        self.assertEqual(document.lines[0].page, 1)
        self.assertIn("区域(10,20,110,50)", document.lines[0].location)
        self.assertEqual(document.lines[0].confidence, 0.93)
        self.assertEqual(document.provenance.kind, "真实引擎输出")
        self.assertEqual(document.provenance.provider, "EasyOCR")
        self.assertFalse(document.provenance.is_measured_accuracy)

    def test_pdf_input_is_rendered_page_by_page(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scan.pdf"
            path.write_bytes(b"not-a-real-pdf")
            provider = EasyOcrProvider(reader=FakeReader([]), engine_version="easyocr-test")

            with self.assertRaises(OcrEngineError):
                provider.recognize_file(path)

    def test_missing_engine_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notice.png"
            path.write_bytes(b"image")

            with self.assertRaisesRegex(OcrEngineError, "OCR 引擎"):
                EasyOcrProvider(reader=None, engine_version=None).recognize_file(path)


if __name__ == "__main__":
    unittest.main()
