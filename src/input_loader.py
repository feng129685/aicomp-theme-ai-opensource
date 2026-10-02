from pathlib import Path

from .recognition import RecognizedDocument, RecognizedLine, RecognitionProvenance


def load_text(path: Path) -> RecognizedDocument:
    lines = tuple(
        RecognizedLine(text=text.strip(), location=f"第{number}行", page=None, confidence=None)
        for number, text in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1)
        if text.strip()
    )
    return RecognizedDocument(
        lines=lines,
        provenance=RecognitionProvenance(
            kind="原始文本",
            provider="utf-8-text-loader",
            engine_version=None,
            parameters={},
            is_measured_accuracy=False,
        ),
    )
