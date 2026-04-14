"""
Serviço de OCR.

Converte cada página do PDF em imagem (via pdf2image/Poppler) e
executa o Tesseract em cada uma delas. O texto de todas as páginas
é concatenado e a confiança retornada é a média global.
"""

from dataclasses import dataclass

import pytesseract
from pdf2image import convert_from_bytes


@dataclass
class OCRResult:
    text: str
    mean_confidence: float  # 0–100


def extract_text(pdf_bytes: bytes, lang: str = "por+eng") -> OCRResult:
    """
    Extrai texto de um PDF usando Tesseract.

    Retorna o texto e a confiança média (0–100).
    Confiança < 40 geralmente indica scan ruim ou texto ilegível.
    """
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

    return OCRResult(text=combined_text, mean_confidence=mean_confidence)
