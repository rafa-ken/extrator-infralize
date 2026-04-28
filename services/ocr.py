"""
Serviço de extração de texto de PDFs.

Estratégia em duas camadas:
  1. pdfplumber — extração nativa da camada de texto do PDF (rápido, sem perda)
  2. Tesseract  — fallback para PDFs escaneados (imagens sem texto embutido)

O fallback só é acionado quando a extração nativa retorna menos de
MIN_NATIVE_CHARS caracteres úteis, o que indica PDF escaneado ou corrompido.
"""

from dataclasses import dataclass
from io import BytesIO

import pdfplumber

MIN_NATIVE_CHARS = 100  # abaixo disso, considera PDF escaneado e aciona OCR


@dataclass
class OCRResult:
    text: str
    mean_confidence: float  # 0–100; 100.0 = extração nativa (sem OCR)
    extraction_method: str  # "native" | "ocr"


def extract_text(pdf_bytes: bytes, lang: str = "por+eng") -> OCRResult:
    """
    Extrai texto de um PDF.

    Tenta extração nativa primeiro. Se o texto for insuficiente
    (PDF escaneado), aciona o Tesseract como fallback.
    """
    native_text = _extract_native(pdf_bytes)

    if len(native_text) >= MIN_NATIVE_CHARS:
        return OCRResult(text=native_text, mean_confidence=100.0, extraction_method="native")

    ocr_text, mean_confidence = _extract_ocr(pdf_bytes, lang)
    return OCRResult(text=ocr_text, mean_confidence=mean_confidence, extraction_method="ocr")


def _extract_native(pdf_bytes: bytes) -> str:
    """Extrai texto da camada nativa do PDF via pdfplumber."""
    pages: list[str] = []
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
            if text.strip():
                pages.append(text.strip())
    return "\n\n".join(pages)


def _extract_ocr(pdf_bytes: bytes, lang: str) -> tuple[str, float]:
    """Converte PDF em imagens e aplica Tesseract. Retorna (texto, confiança_média)."""
    import pytesseract
    from pdf2image import convert_from_bytes

    from core.config import settings

    if settings.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd

    pages = convert_from_bytes(pdf_bytes, dpi=150, poppler_path=settings.poppler_path)

    all_text: list[str] = []
    all_confidences: list[int] = []

    for page in pages:
        data = pytesseract.image_to_data(page, lang=lang, output_type=pytesseract.Output.DICT)
        confidences = [
            int(c) for c in data["conf"] if str(c).lstrip("-").isdigit() and int(c) >= 0
        ]
        all_confidences.extend(confidences)
        all_text.append(pytesseract.image_to_string(page, lang=lang))

    mean_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
    combined_text = "\n\n".join(block.strip() for block in all_text if block.strip())
    return combined_text, mean_confidence
