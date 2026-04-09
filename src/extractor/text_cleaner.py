"""
Text normalization utilities for post-OCR and post-extraction cleanup.
"""

import re
import unicodedata


def normalize_unicode(text: str) -> str:
    """Normalize unicode characters (fix common encoding artifacts)."""
    # NFC normalization
    text = unicodedata.normalize("NFC", text)
    # Replace common OCR unicode artifacts
    replacements = {
        "\u2019": "'",    # right single quotation mark
        "\u2018": "'",    # left single quotation mark
        "\u201c": '"',    # left double quotation mark
        "\u201d": '"',    # right double quotation mark
        "\u2013": "-",    # en dash
        "\u2014": "-",    # em dash
        "\u00a0": " ",    # non-breaking space
        "\ufffd": "",     # replacement character
        "\x0c": "\n",     # form feed → newline
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)
    return text


def rejoin_hyphenated_words(text: str) -> str:
    """
    Re-join words broken by end-of-line hyphens (common OCR artifact).
    E.g.: "cons-\ntruir" → "construir"
    """
    return re.sub(r"(\w)-\n(\w)", r"\1\2", text)


def collapse_whitespace(text: str) -> str:
    """Collapse multiple spaces/tabs into a single space; preserve newlines."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_headers_footers(text: str, max_line_len: int = 80) -> str:
    """
    Heuristic removal of repeated header/footer lines.
    Lines shorter than max_line_len that appear identically on multiple pages
    are likely headers/footers, but this requires multi-page context.
    Here we apply a simple pass: remove isolated single-character lines and
    page number patterns.
    """
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip isolated single chars (often OCR noise)
        if len(stripped) == 1 and not stripped.isalnum():
            continue
        # Skip pure page number lines like "- 3 -" or "Página 3 de 15"
        if re.fullmatch(r"[-–]\s*\d+\s*[-–]", stripped):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def normalize_monetary(text: str) -> str:
    """
    Normalize common Brazilian monetary formats for readability.
    Does NOT parse to float — that happens in the LLM extraction step.
    """
    # Ensure "R$" has a space after it: "R$1.000" → "R$ 1.000"
    text = re.sub(r"R\$\s*", "R$ ", text)
    return text


def clean_page_text(text: str, is_ocr: bool = False) -> str:
    """
    Full cleaning pipeline for a single page's text.

    Args:
        text: Raw text from PDF reader or OCR.
        is_ocr: If True, applies more aggressive cleanup.
    """
    text = normalize_unicode(text)

    if is_ocr:
        text = rejoin_hyphenated_words(text)

    text = remove_headers_footers(text)
    text = normalize_monetary(text)
    text = collapse_whitespace(text)

    return text


def merge_pages(pages: list[tuple[int, str, str]]) -> str:
    """
    Merge a list of (page_number, text, method) tuples into a single
    document string with page markers for the LLM.

    Args:
        pages: List of (page_number, cleaned_text, method).

    Returns:
        Full document text with page delimiters.
    """
    parts = []
    for page_num, text, _method in pages:
        if text.strip():
            parts.append(f"[PÁGINA {page_num}]\n{text.strip()}")
    return "\n\n".join(parts)
