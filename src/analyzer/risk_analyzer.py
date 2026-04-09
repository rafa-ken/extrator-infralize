"""
Phase 2 analyzer: ContractJSON → RiskAnalysisJSON via LLM.

The model receives ONLY the structured contract JSON. It never sees the raw PDF.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import anthropic
from loguru import logger

from src.analyzer.prompts import ANALYSIS_SYSTEM_PROMPT, ANALYSIS_USER_TEMPLATE
from src.schemas.contract_schema import ContractJSON
from src.schemas.analysis_schema import RiskAnalysisJSON
from src.utils.error_handler import (
    AnalysisError,
    LLMError,
    extract_json_from_response,
    retry_with_backoff,
)
from src.parser.validators import validate_analysis_json


class RiskAnalyzer:
    """
    Analyzes a ContractJSON for risks using Claude.
    """

    def __init__(
        self,
        model: str | None = None,
        max_tokens: int | None = None,
        max_retries: int | None = None,
    ):
        self.model = model or os.getenv("CLAUDE_ANALYSIS_MODEL", "claude-sonnet-4-6")
        self.max_tokens = max_tokens or int(os.getenv("CLAUDE_MAX_TOKENS", "8192"))
        self.max_retries = max_retries or int(os.getenv("LLM_MAX_RETRIES", "3"))
        self._client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # ── Public API ─────────────────────────────────────────────────────────────

    def analyze(self, contract: ContractJSON) -> RiskAnalysisJSON:
        """
        Produce a risk analysis JSON from a validated ContractJSON.

        Args:
            contract: Validated contract data from Phase 1.

        Returns:
            Validated RiskAnalysisJSON model.

        Raises:
            AnalysisError: If LLM call or parsing fails after all retries.
        """
        # Serialize contract JSON for the prompt
        # Exclude raw_text_pages to reduce token usage (already captured in evidence)
        contract_dict = contract.model_dump(exclude={"raw_text_pages"})
        contract_json_str = json.dumps(contract_dict, ensure_ascii=False, indent=2)

        logger.info(
            f"Sending {len(contract_json_str):,} chars of contract JSON to "
            f"analysis model ({self.model})"
        )

        user_prompt = ANALYSIS_USER_TEMPLATE.format(
            contract_json=contract_json_str,
        )

        raw_response = self._call_llm_with_retry(user_prompt)
        analysis_data = self._parse_llm_response(raw_response)

        # Inject runtime metadata
        now = datetime.now(timezone.utc).isoformat()
        analysis_data["analysis_timestamp"] = now
        analysis_data["source_contract_file"] = contract.source_file
        analysis_data["schema_version"] = "1.0.0"

        # Ensure model_notes has correct values
        if "model_notes" not in analysis_data or not analysis_data["model_notes"]:
            analysis_data["model_notes"] = {}
        analysis_data["model_notes"]["analysis_date"] = now
        analysis_data["model_notes"]["model_used"] = self.model
        if "disclaimer" not in analysis_data["model_notes"]:
            analysis_data["model_notes"]["disclaimer"] = (
                "Esta análise é baseada exclusivamente nos dados estruturados extraídos "
                "do contrato e não substitui revisão jurídica profissional. "
                "Campos com baixa confiança de extração podem conter imprecisões."
            )

        validated = validate_analysis_json(analysis_data)

        risk_counts = {sev: 0 for sev in ["critical", "high", "medium", "low"]}
        for risk in validated.detected_risks:
            risk_counts[risk.severity.value] += 1

        logger.info(
            f"Analysis complete — overall risk: {validated.overall_risk_level.value} "
            f"(score {validated.severity_score:.1f}/10) | "
            f"Risks: {risk_counts} | "
            f"Missing info: {len(validated.missing_information)} | "
            f"Abnormal clauses: {len(validated.abnormal_clauses)}"
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
                system=ANALYSIS_SYSTEM_PROMPT,
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
            raise AnalysisError(f"Failed to parse LLM analysis response: {exc}") from exc
