"""
Phase 1 parser: raw contract text → ContractJSON via LLM.

This module calls the Claude API with the extraction prompt and returns a
validated ContractJSON. It handles retries and partial-data fallback.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic
from loguru import logger

from src.analyzer.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_TEMPLATE
from src.extractor.pdf_reader import PageResult
from src.extractor.text_cleaner import merge_pages
from src.schemas.contract_schema import ContractJSON
from src.utils.error_handler import (
    LLMError,
    ParsingError,
    extract_json_from_response,
    retry_with_backoff,
)
from .validators import validate_contract_json


class ContractParser:
    """
    Extracts structured contract data from raw text using Claude.
    """

    def __init__(
        self,
        model: str | None = None,
        max_tokens: int | None = None,
        max_retries: int | None = None,
    ):
        self.model = model or os.getenv("CLAUDE_EXTRACTION_MODEL", "claude-sonnet-4-6")
        self.max_tokens = max_tokens or int(os.getenv("CLAUDE_MAX_TOKENS", "8192"))
        self.max_retries = max_retries or int(os.getenv("LLM_MAX_RETRIES", "3"))
        self._client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # ── Public API ─────────────────────────────────────────────────────────────

    def parse(
        self,
        pages: list[PageResult],
        source_file: str,
        extraction_summary: dict[str, Any],
    ) -> ContractJSON:
        """
        Convert extracted page text into a validated ContractJSON.

        Args:
            pages: Per-page extraction results from PDFReader.
            source_file: Original PDF file name (for provenance).
            extraction_summary: Summary dict from PDFReader.extraction_summary().

        Returns:
            Validated ContractJSON model.

        Raises:
            ParsingError: If LLM call or parsing fails after all retries.
        """
        merged_text = merge_pages(
            [(p.page, p.text, p.method) for p in pages]
        )

        if not merged_text.strip():
            raise ParsingError("No text could be extracted from the PDF.")

        logger.info(
            f"Sending {len(merged_text):,} characters to extraction model ({self.model})"
        )

        user_prompt = EXTRACTION_USER_TEMPLATE.format(
            source_file=source_file,
            ocr_used=str(extraction_summary.get("ocr_used", False)).lower(),
            pages_processed=extraction_summary.get("pages_processed", 0),
            total_characters=extraction_summary.get("total_characters", 0),
            extraction_method=extraction_summary.get("extraction_method", "native_pdf"),
            contract_text=merged_text,
        )

        raw_response = self._call_llm_with_retry(user_prompt)
        contract_data = self._parse_llm_response(raw_response)

        # Inject runtime metadata that the LLM cannot know
        contract_data["extraction_timestamp"] = datetime.now(timezone.utc).isoformat()
        contract_data["source_file"] = source_file
        contract_data["schema_version"] = "1.0.0"

        # Inject raw_text_pages for auditability
        contract_data["raw_text_pages"] = [
            {
                "page": p.page,
                "text": p.text[:500],     # truncate for JSON size
                "method": p.method,
                "char_count": p.char_count,
            }
            for p in pages
        ]

        validated = validate_contract_json(contract_data)
        logger.info(
            f"Extraction complete — confidence: "
            f"{validated.confidence_summary.overall_confidence:.2f}, "
            f"fields extracted: {validated.confidence_summary.fields_extracted}, "
            f"fields missing: {validated.confidence_summary.fields_missing}"
        )
        return validated

    # ── Private helpers ────────────────────────────────────────────────────────

    @retry_with_backoff(max_retries=3, base_delay=2.0, exceptions=(LLMError, Exception))
    def _call_llm_with_retry(self, user_prompt: str) -> str:
        """Call Claude and return the raw text response."""
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=EXTRACTION_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            content = response.content[0].text
            if not content:
                raise LLMError("LLM returned empty response.")
            logger.debug(
                f"LLM response received: {len(content):,} chars, "
                f"stop_reason={response.stop_reason}"
            )
            return content
        except anthropic.APIError as exc:
            raise LLMError(f"Anthropic API error: {exc}") from exc

    def _parse_llm_response(self, raw: str) -> dict[str, Any]:
        """Extract and parse JSON from raw LLM response."""
        try:
            data = extract_json_from_response(raw)
            if not isinstance(data, dict):
                raise LLMError("LLM response is not a JSON object.", raw_response=raw)
            return data
        except LLMError:
            raise
        except Exception as exc:
            raise ParsingError(f"Failed to parse LLM response: {exc}") from exc
