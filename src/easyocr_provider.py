from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Optional

from .recognition import RecognizedDocument, RecognizedLine, RecognitionProvenance


class OcrEngineError(RuntimeError):
    pass


def _bbox_location(points: Any, page: int) -> str:
    try:
        xs = [int(point[0]) for point in points]
        ys = [int(point[1]) for point in points]
        return f"第{page}页区域({min(xs)},{min(ys)},{max(xs)},{max(ys)})"
    except (TypeError, ValueError, IndexError):
        return f"第{page}页区域未知"


def load_document_images(path: Path, dpi: int = 180) -> list[tuple[int, Any]]:
    suffix = path.suffix.lower()
    if suffix != ".pdf":
        if not path.exists():
            raise OcrEngineError(f"文件不存在: {path}")
        return [(1, str(path))]
    try:
        import fitz
        document = fitz.open(path)
    except Exception as exc:
        raise OcrEngineError(f"PDF 无法打开或渲染: {exc}") from exc
    images = []
    scale = dpi / 72
    matrix = fitz.Matrix(scale, scale)
    try:
        for index, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            images.append((index, pixmap.tobytes("png")))
    finally:
        document.close()
    if not images:
        raise OcrEngineError("PDF 没有页面")
    return images


class EasyOcrProvider:
    def __init__(
        self,
        reader: Optional[Any] = None,
        *,
        languages: tuple[str, ...] = ("ch_sim", "en"),
        engine_version: Optional[str] = None,
        gpu: bool = False,
        model_storage_directory: Optional[str] = None,
        dpi: int = 180,
    ):
        self.reader = reader
        self.languages = languages
        self.engine_version = engine_version
        self.gpu = gpu
        self.model_storage_directory = model_storage_directory
        self.dpi = dpi

    def _reader(self) -> Any:
        if self.reader is not None:
            return self.reader
        if not self.engine_version:
            raise OcrEngineError("未配置 OCR 引擎版本")
        try:
            import easyocr
            self.reader = easyocr.Reader(
                list(self.languages),
                gpu=self.gpu,
                model_storage_directory=self.model_storage_directory,
            )
            return self.reader
        except Exception as exc:
            raise OcrEngineError(f"OCR 引擎 EasyOCR 初始化失败: {exc}") from exc

    def recognize_file(self, path: Path) -> RecognizedDocument:
        if self.reader is None and not self.engine_version:
            raise OcrEngineError("未配置 OCR 引擎版本")
        reader = self._reader()
        lines: list[RecognizedLine] = []
        for page, image in load_document_images(path, dpi=self.dpi):
            try:
                raw_lines = reader.readtext(image, detail=1, paragraph=False)
            except Exception as exc:
                raise OcrEngineError(f"EasyOCR 识别失败，第{page}页: {exc}") from exc
            for raw in raw_lines:
                if len(raw) < 3:
                    continue
                points, text, confidence = raw[0], str(raw[1]).strip(), raw[2]
                if not text:
                    continue
                try:
                    numeric_confidence = float(confidence)
                except (TypeError, ValueError):
                    numeric_confidence = None
                if numeric_confidence is not None and not 0 <= numeric_confidence <= 1:
                    raise OcrEngineError("EasyOCR 返回了越界置信度")
                lines.append(RecognizedLine(text=text, location=_bbox_location(points, page), page=page, confidence=numeric_confidence))
        if not lines:
            raise OcrEngineError("EasyOCR 未识别到可用文字")
        return RecognizedDocument(
            lines=tuple(lines),
            provenance=RecognitionProvenance(
                kind="真实引擎输出",
                provider="EasyOCR",
                engine_version=self.engine_version,
                parameters={"languages": ",".join(self.languages), "gpu": str(self.gpu), "dpi": str(self.dpi)},
                is_measured_accuracy=False,
            ),
        )
