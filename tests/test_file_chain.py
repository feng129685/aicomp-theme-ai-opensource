import json
import tempfile
import unittest
from pathlib import Path

from src.contract_guard import validate_parse_result
from src.easyocr_provider import EasyOcrProvider
from src.input_loader import load_text
from src.parser_adapter import ParserAdapter


class FileChainTests(unittest.TestCase):
    def test_real_provider_output_flows_to_parser_without_schema_change(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notice.png"
            path.write_bytes(b"fixture-image")
            provider = EasyOcrProvider(
                reader=type("Reader", (), {"readtext": lambda self, image, detail=1, paragraph=False: [([[1, 2], [3, 2], [3, 4], [1, 4]], "报名截止时间为2026年10月18日18:00", 0.91)]})(),
                engine_version="1.7.2",
            )
            document = provider.recognize_file(path)
            result = ParserAdapter().parse(
                {"document_id":"doc-chain-001","category":"竞赛通知","sample_id":"NOTICE-003-V1","matter_id":"matter-chain-001","version":"v1","based_on_version":None},
                document,
            )

        validate_parse_result(result)
        self.assertEqual(result["notice"]["deadline"], "2026-10-18T18:00:00+08:00")
        self.assertEqual(result["fields"][-4]["page"], 1)
        self.assertEqual(result["fields"][-4]["confidence"], 0.91)


if __name__ == "__main__":
    unittest.main()
