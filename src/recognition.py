from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Mapping, Optional, Tuple


class RecognitionError(ValueError):
    pass


@dataclass(frozen=True)
class RecognitionProvenance:
    kind: str
    provider: str
    engine_version: Optional[str]
    parameters: Mapping[str, str]
    is_measured_accuracy: bool


@dataclass(frozen=True)
class RecognizedLine:
    text: str
    location: str
    page: Optional[int]
    confidence: Optional[float]


@dataclass(frozen=True)
class RecognizedDocument:
    lines: Tuple[RecognizedLine, ...]
    provenance: RecognitionProvenance

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)


class FixtureOcrProvider:
    """Reads manually prepared truth files; it does not run an OCR engine."""

    def __init__(self, fixtures: Mapping[str, Path]):
        self._fixtures = dict(fixtures)

    def recognize(self, path: Path) -> RecognizedDocument:
        truth_path = self._fixtures.get(path.name)
        if truth_path is None:
            raise RecognitionError(f"没有与 {path.name} 对应的人工真值")
        lines = tuple(
            RecognizedLine(text=text.strip(), location=f"第1页第{number}行", page=1, confidence=None)
            for number, text in enumerate(truth_path.read_text(encoding="utf-8").splitlines(), start=1)
            if text.strip()
        )
        if not lines:
            raise RecognitionError("未识别到可用文字")
        return RecognizedDocument(
            lines=lines,
            provenance=RecognitionProvenance(
                kind="人工夹具",
                provider="fixture-ground-truth",
                engine_version=None,
                parameters={},
                is_measured_accuracy=False,
            ),
        )


class JsonOcrProvider:
    """Loads a recorded result exported by a real OCR engine."""

    def recognize(self, path: Path) -> RecognizedDocument:
        payload = json.loads(path.read_text(encoding="utf-8"))
        engine = payload.get("engine")
        engine_version = payload.get("engine_version")
        if not engine:
            raise RecognitionError("真实 OCR 结果缺少 engine")
        if not engine_version:
            raise RecognitionError("真实 OCR 结果缺少 engine_version")
        lines = []
        for raw in payload.get("lines", []):
            text = str(raw.get("text", "")).strip()
            if not text:
                continue
            confidence = raw.get("confidence")
            if confidence is not None and not 0 <= confidence <= 1:
                raise RecognitionError("行级 confidence 必须为 null 或 0 到 1")
            page = raw.get("page")
            if page is not None and (not isinstance(page, int) or page < 1):
                raise RecognitionError("page 必须为 null 或正整数")
            location = raw.get("location")
            if not location:
                raise RecognitionError("真实 OCR 行缺少 location")
            lines.append(RecognizedLine(text=text, location=location, page=page, confidence=confidence))
        if not lines:
            raise RecognitionError("未识别到可用文字")
        parameters = payload.get("parameters") or {}
        if not isinstance(parameters, dict):
            raise RecognitionError("parameters 必须为对象")
        return RecognizedDocument(
            lines=tuple(lines),
            provenance=RecognitionProvenance(
                kind="真实引擎输出",
                provider=str(engine),
                engine_version=str(engine_version),
                parameters={str(key): str(value) for key, value in parameters.items()},
                is_measured_accuracy=False,
            ),
        )
