import time
import json
import functools
from typing import Callable, TypeVar, Any
from loguru import logger

T = TypeVar("T")


# ── Custom Exceptions ────────────────────────────────────────────────────────

class ExtractorError(Exception):
    """Base error for the extraction pipeline."""


class OCRError(ExtractorError):
    """Raised when OCR processing fails."""


class ParsingError(ExtractorError):
    """Raised when text-to-JSON parsing fails."""


class AnalysisError(ExtractorError):
    """Raised when LLM risk analysis fails."""


class LLMError(ExtractorError):
    """Raised when LLM API call fails or returns invalid output."""

    def __init__(self, message: str, raw_response: str | None = None):
        super().__init__(message)
        self.raw_response = raw_response


class ValidationError(ExtractorError):
    """Raised when JSON schema validation fails."""


# ── Retry Decorator ───────────────────────────────────────────────────────────

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 30.0,
    exceptions: tuple = (LLMError, Exception),
    on_retry: Callable | None = None,
):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Initial delay in seconds.
        max_delay: Maximum delay cap in seconds.
        exceptions: Tuple of exception types to catch and retry.
        on_retry: Optional callback(attempt, exception) called before each retry.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt == max_retries:
                        logger.error(
                            f"[{func.__name__}] Attempt {attempt}/{max_retries} failed "
                            f"(no more retries): {exc}"
                        )
                        raise
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    logger.warning(
                        f"[{func.__name__}] Attempt {attempt}/{max_retries} failed: {exc}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    if on_retry:
                        on_retry(attempt, exc)
                    time.sleep(delay)
            raise last_exception  # type: ignore[misc]

        return wrapper
    return decorator


# ── JSON Extraction Helper ────────────────────────────────────────────────────

def extract_json_from_response(text: str) -> dict | list:
    """
    Extract a JSON object or array from a raw LLM response string.

    Handles cases where the LLM wraps JSON in markdown code fences.

    Raises:
        LLMError: If no valid JSON can be extracted.
    """
    # Strip markdown code fences if present
    cleaned = text.strip()
    for fence in ("```json", "```JSON", "```"):
        if cleaned.startswith(fence):
            cleaned = cleaned[len(fence):]
            break
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to find the first { or [ and extract from there
    for start_char, end_char in [('{', '}'), ('[', ']')]:
        start = cleaned.find(start_char)
        end = cleaned.rfind(end_char)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except json.JSONDecodeError:
                pass

    raise LLMError(
        "LLM response does not contain valid JSON.",
        raw_response=text[:2000],
    )
