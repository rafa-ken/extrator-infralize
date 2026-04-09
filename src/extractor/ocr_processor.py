"""
OCR processor for scanned PDFs.

Requires:
  - Tesseract-OCR installed and accessible (see TESSERACT_CMD in .env)
  - Poppler binaries for pdf2image (on Windows: add to PATH or set poppler_path)
"""

import os
from pathlib import Path
from loguru import logger

try:
    from pdf2image import convert_from_path
    from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not installed. OCR will not be available.")

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("pytesseract or Pillow not installed. OCR will not be available.")


def _configure_tesseract() -> None:
    """Set Tesseract executable path from environment variable."""
    tesseract_cmd = os.getenv("TESSERACT_CMD")
    if tesseract_cmd and TESSERACT_AVAILABLE:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd


class OCRProcessor:
    """
    Converts PDF pages to images and extracts text via Tesseract OCR.
    """

    def __init__(
        self,
        lang: str | None = None,
        dpi: int | None = None,
        poppler_path: str | None = None,
    ):
        self.lang = lang or os.getenv("OCR_LANG", "por")
        self.dpi = dpi or int(os.getenv("OCR_DPI", "300"))
        self.poppler_path = poppler_path or os.getenv("POPPLER_PATH")
        _configure_tesseract()

    def is_available(self) -> bool:
        """Check if all OCR dependencies are installed."""
        return PDF2IMAGE_AVAILABLE and TESSERACT_AVAILABLE

    def process_page(self, image: "Image.Image") -> str:
        """
        Run Tesseract on a single PIL Image.

        Args:
            image: PIL Image of a PDF page.

        Returns:
            Extracted text string.
        """
        if not TESSERACT_AVAILABLE:
            raise RuntimeError("pytesseract is not installed.")

        config = "--psm 3"   # automatic page segmentation
        text = pytesseract.image_to_string(image, lang=self.lang, config=config)
        return text

    def process_pdf(
        self,
        pdf_path: str | Path,
        page_numbers: list[int] | None = None,
    ) -> list[tuple[int, str]]:
        """
        OCR one or more pages from a PDF.

        Args:
            pdf_path: Path to the PDF file.
            page_numbers: 1-based page numbers to process. If None, process all.

        Returns:
            List of (page_number, extracted_text) tuples.
        """
        if not self.is_available():
            raise RuntimeError(
                "OCR dependencies (pdf2image + pytesseract) are not installed. "
                "See requirements.txt and install Tesseract-OCR on your system."
            )

        pdf_path = Path(pdf_path)
        logger.info(f"OCR: converting {pdf_path.name} to images (DPI={self.dpi})")

        convert_kwargs: dict = {"dpi": self.dpi, "fmt": "PNG"}
        if self.poppler_path:
            convert_kwargs["poppler_path"] = self.poppler_path
        if page_numbers:
            # pdf2image uses first_page / last_page (1-based)
            convert_kwargs["first_page"] = min(page_numbers)
            convert_kwargs["last_page"] = max(page_numbers)

        try:
            images = convert_from_path(str(pdf_path), **convert_kwargs)
        except PDFInfoNotInstalledError:
            raise RuntimeError(
                "Poppler not found. Install poppler-utils (Linux/Mac) or "
                "poppler for Windows and set POPPLER_PATH in .env."
            )
        except PDFPageCountError as exc:
            raise RuntimeError(f"Cannot read PDF: {exc}") from exc

        results: list[tuple[int, str]] = []
        start_page = min(page_numbers) if page_numbers else 1

        for idx, image in enumerate(images):
            page_num = start_page + idx
            if page_numbers and page_num not in page_numbers:
                continue
            logger.debug(f"OCR: processing page {page_num}")
            text = self.process_page(image)
            results.append((page_num, text))

        return results
