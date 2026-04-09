"""
Validation helpers that bridge raw LLM dicts with Pydantic schema models.
"""

from __future__ import annotations

from typing import Any
from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from src.schemas.contract_schema import ContractJSON
from src.schemas.analysis_schema import RiskAnalysisJSON
from src.utils.error_handler import ValidationError


def validate_contract_json(data: dict[str, Any]) -> ContractJSON:
    """
    Validate and coerce a raw dict into a ContractJSON model.

    Raises:
        ValidationError: If validation fails after logging the issues.
    """
    try:
        return ContractJSON.model_validate(data)
    except PydanticValidationError as exc:
        errors = exc.errors()
        logger.warning(
            f"ContractJSON validation had {len(errors)} issue(s). "
            "Attempting partial model with defaults for missing/invalid fields."
        )
        for err in errors[:10]:   # log first 10 errors
            logger.debug(f"  Validation issue: {err['loc']} → {err['msg']}")

        # Try permissive approach: strip invalid fields and retry
        cleaned = _strip_invalid_fields(data, errors)
        try:
            return ContractJSON.model_validate(cleaned)
        except PydanticValidationError as exc2:
            raise ValidationError(
                f"ContractJSON validation failed: {exc2}"
            ) from exc2


def validate_analysis_json(data: dict[str, Any]) -> RiskAnalysisJSON:
    """
    Validate and coerce a raw dict into a RiskAnalysisJSON model.

    Raises:
        ValidationError: If validation fails after logging the issues.
    """
    try:
        return RiskAnalysisJSON.model_validate(data)
    except PydanticValidationError as exc:
        errors = exc.errors()
        logger.warning(
            f"RiskAnalysisJSON validation had {len(errors)} issue(s). "
            "Attempting partial model with defaults for missing/invalid fields."
        )
        for err in errors[:10]:
            logger.debug(f"  Validation issue: {err['loc']} → {err['msg']}")

        cleaned = _strip_invalid_fields(data, errors)
        try:
            return RiskAnalysisJSON.model_validate(cleaned)
        except PydanticValidationError as exc2:
            raise ValidationError(
                f"RiskAnalysisJSON validation failed: {exc2}"
            ) from exc2


def _strip_invalid_fields(
    data: dict[str, Any],
    errors: list[dict],
) -> dict[str, Any]:
    """
    Attempt to null-out or remove fields that failed validation so the model
    can still be instantiated with partial data.
    """
    import copy
    cleaned = copy.deepcopy(data)

    for err in errors:
        loc = err.get("loc", ())
        if not loc:
            continue
        # Navigate to the parent and remove/null the offending key
        obj = cleaned
        for key in loc[:-1]:
            if isinstance(obj, dict) and key in obj:
                obj = obj[key]
            elif isinstance(obj, list) and isinstance(key, int) and key < len(obj):
                obj = obj[key]
            else:
                obj = None
                break
        if obj is not None and isinstance(obj, dict):
            last_key = loc[-1]
            if last_key in obj:
                obj[last_key] = None   # null the invalid field

    return cleaned
