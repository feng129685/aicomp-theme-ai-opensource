from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.easyocr_provider import EasyOcrProvider


ROOT = Path(__file__).resolve().parents[1]
input_path = ROOT / "samples" / "ocr" / "OCR-001-CLEAR.png"
record = {
    "engine": "EasyOCR",
    "engine_version": "1.7.2",
    "languages": ["ch_sim", "en"],
    "gpu": False,
    "input": str(input_path),
    "status": "未测量",
    "accuracy": None,
}
try:
    document = EasyOcrProvider(engine_version="1.7.2", languages=("ch_sim", "en"), gpu=False).recognize_file(input_path)
    record["status"] = "成功"
    record["lines"] = [
        {"text": line.text, "location": line.location, "page": line.page, "confidence": line.confidence}
        for line in document.lines
    ]
except Exception as exc:
    record["status"] = "失败"
    record["error_type"] = type(exc).__name__
    record["error"] = str(exc)

output_path = ROOT / "samples" / "outputs" / "easyocr-real-run.json"
output_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(record, ensure_ascii=False, indent=2))
