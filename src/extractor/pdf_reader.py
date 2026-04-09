"""
PDF text extractor with automatic OCR fallback for scanned pages.

Strategy:
  1. Try native text extraction with pdfplumber.
  2. If a page has fewer than MIN_CHARS_NATIVE characters, flag it for OCR.
  3. Run OCR on flagged pages (requires Tesseract + poppler).
  4. Return a list of RawTextPage objects for the pipeline.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from loguru import logger

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    logger.warning("pdfplumber not installed.")

from .ocr_processor import OCRProcessor
from .text_cleaner import clean_page_text


@dataclass
class PageResult:
    page: int
    text: str
    method: str          # "native" | "ocr" | "empty"
    char_count: int
    needs_ocr: bool = False


class PDFReader:
    """
    Reads a PDF and returns per-page text with provenance metadata.
    """

    def __init__(
        self,
        min_chars_native: int | None = None,
        ocr_processor: OCRProcessor | None = None,
    ):
        self.min_chars_native = min_chars_native or int(
            os.getenv("MIN_CHARS_NATIVE", "100")
        )
        self._ocr = ocr_processor or OCRProcessor()

    # ── Public API ────────────────────────────────────────────────────────────

    def read(self, pdf_path: str | Path) -> list[PageResult]:
        """
        Extract text from all pages of a PDF.

        Returns:
            Ordered list of PageResult (one per page).
        """
        if not PDFPLUMBER_AVAILABLE:
            raise RuntimeError(
                "pdfplumber is not installed. Run: pip install pdfplumber"
            )

        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        logger.info(f"Reading PDF: {pdf_path.name}")

        pages: list[PageResult] = []
        pages_needing_ocr: list[int] = []

        with pdfplumber.open(str(pdf_path)) as pdf:
            total_pages = len(pdf.pages)
            logger.info(f"PDF has {total_pages} page(s)")

            for i, page in enumerate(pdf.pages, start=1):
                raw_text = page.extract_text() or ""
                char_count = len(raw_text.strip())

                if char_count >= self.min_chars_native:
                    cleaned = clean_page_text(raw_text, is_ocr=False)
                    pages.append(
                        PageResult(
                            page=i,
                            text=cleaned,
                            method="native",
                            char_count=len(cleaned),
                        )
                    )
                    logger.debug(f"Page {i}: native ({char_count} chars)")
                else:
                    # Not enough text — mark for OCR
                    pages.append(
                        PageResult(
                            page=i,
                            text="",
                            method="ocr",
                            char_count=0,
                            needs_ocr=True,
                        )
                    )
                    pages_needing_ocr.append(i)
                    logger.debug(
                        f"Page {i}: insufficient native text ({char_count} chars) → OCR"
                    )

        # Run OCR on pages that need it
        if pages_needing_ocr:
            pages = self._apply_ocr(pdf_path, pages, pages_needing_ocr)

        # Summarize
        native_count = sum(1 for p in pages if p.method == "native")
        ocr_count = sum(1 for p in pages if p.method == "ocr")
        logger.info(
            f"Extraction complete: {native_count} native pages, {ocr_count} OCR pages"
        )

        return pages

    # ── Private helpers ───────────────────────────────────────────────────────

    def _apply_ocr(
        self,
        pdf_path: Path,
        pages: list[PageResult],
        pages_needing_ocr: list[int],
    ) -> list[PageResult]:
        """Run OCR on flagged pages and merge results back."""
        if not self._ocr.is_available():
            logger.warning(
                f"{len(pages_needing_ocr)} page(s) need OCR but OCR is not available. "
                "Install pytesseract + pdf2image + Tesseract to process scanned pages. "
                "Affected pages will be empty."
            )
            return pages

        logger.info(
            f"Running OCR on {len(pages_needing_ocr)} page(s): {pages_needing_ocr}"
        )

        try:
            ocr_results = self._ocr.process_pdf(pdf_path, page_numbers=pages_needing_ocr)
        except Exception as exc:
            logger.error(f"OCR failed: {exc}. Affected pages will be empty.")
            return pages

        # Build lookup: page_num → ocr_text
        ocr_map = {page_num: text for page_num, text in ocr_results}

        # Merge into pages list
        for result in pages:
            if result.needs_ocr:
                raw_ocr_text = ocr_map.get(result.page, "")
                cleaned = clean_page_text(raw_ocr_text, is_ocr=True)
                result.text = cleaned
                result.char_count = len(cleaned)
                result.method = "ocr" if cleaned else "empty"

        return pages

    def extraction_summary(self, pages: list[PageResult]) -> dict:
        """Return a summary dict for logging and confidence_summary."""
        native = [p for p in pages if p.method == "native"]
        ocr = [p for p in pages if p.method == "ocr"]
        empty = [p for p in pages if p.method == "empty"]
        total_chars = sum(p.char_count for p in pages)

        ocr_used = len(ocr) > 0
        method = (
            "native_pdf" if not ocr_used
            else "ocr" if not native
            else "hybrid"
        )

        return {
            "pages_processed": len(pages),
            "native_pages": len(native),
            "ocr_pages": len(ocr),
            "empty_pages": len(empty),
            "total_characters": total_chars,
            "ocr_used": ocr_used,
            "extraction_method": method,
        }
