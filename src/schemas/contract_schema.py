"""
Pydantic v2 models for the structured contract JSON (Phase 1 output).

Each extracted field follows the ExtractedField pattern:
  value       → the normalized extracted value
  confidence  → 0.0–1.0 score
  evidence    → verbatim text snippet that supports the value
  page        → 1-based page number where the evidence was found
"""

from __future__ import annotations

from typing import Any, List, Optional
from pydantic import BaseModel, Field


# ── Primitive building block ──────────────────────────────────────────────────

class ExtractedField(BaseModel):
    """A single extracted value with provenance metadata."""
    value: Optional[Any] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    evidence: Optional[str] = None
    page: Optional[int] = None


# ── Sub-models ────────────────────────────────────────────────────────────────

class Party(BaseModel):
    name: Optional[ExtractedField] = None
    document: Optional[ExtractedField] = None        # CPF or CNPJ value
    document_type: Optional[str] = None              # "CPF" | "CNPJ"
    address: Optional[ExtractedField] = None
    legal_representative: Optional[ExtractedField] = None
    role: Optional[str] = None                        # "contratante" | "contratado" | etc.


class PaymentScheduleEntry(BaseModel):
    description: Optional[str] = None
    percentage: Optional[float] = None
    amount: Optional[float] = None
    condition: Optional[str] = None
    due_date: Optional[str] = None


class Milestone(BaseModel):
    description: Optional[str] = None
    date: Optional[str] = None
    percentage: Optional[float] = None
    value: Optional[float] = None


class LegalClause(BaseModel):
    number: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    page: Optional[int] = None
    risk_flag: bool = False
    risk_reason: Optional[str] = None


class ExtractionWarning(BaseModel):
    field: str
    warning: str
    severity: str = "low"    # "low" | "medium" | "high"


class RawTextPage(BaseModel):
    page: int
    text: str
    method: str              # "native" | "ocr"
    char_count: int


# ── Section models ────────────────────────────────────────────────────────────

class ContractMetadata(BaseModel):
    contract_number: Optional[ExtractedField] = None
    signing_date: Optional[ExtractedField] = None
    document_type: Optional[ExtractedField] = None
    version: Optional[str] = None


class Parties(BaseModel):
    contractor: Optional[Party] = None               # contratante
    hired: Optional[Party] = None                    # contratado / executante
    guarantor: Optional[Party] = None                # fiador / garantidor
    other_parties: List[Party] = Field(default_factory=list)


class WorkObject(BaseModel):
    description: Optional[ExtractedField] = None
    address: Optional[ExtractedField] = None
    registration: Optional[ExtractedField] = None    # matrícula do imóvel
    technical_specs: Optional[ExtractedField] = None
    art_rrt: Optional[ExtractedField] = None         # número ART/RRT


class FinancialTerms(BaseModel):
    total_value: Optional[ExtractedField] = None
    currency: str = "BRL"
    payment_method: Optional[ExtractedField] = None
    payment_schedule: List[PaymentScheduleEntry] = Field(default_factory=list)
    price_adjustment: Optional[ExtractedField] = None
    price_adjustment_index: Optional[ExtractedField] = None  # INCC, IPCA, etc.
    retentions: Optional[ExtractedField] = None
    retention_percentage: Optional[ExtractedField] = None
    advance_payment: Optional[ExtractedField] = None
    advance_percentage: Optional[ExtractedField] = None
    measurement_criteria: Optional[ExtractedField] = None


class Schedule(BaseModel):
    execution_term_days: Optional[ExtractedField] = None
    execution_term_months: Optional[ExtractedField] = None
    start_date: Optional[ExtractedField] = None
    end_date: Optional[ExtractedField] = None
    contractual_validity: Optional[ExtractedField] = None
    physical_financial_schedule: List[Milestone] = Field(default_factory=list)
    milestones: List[Milestone] = Field(default_factory=list)


class ExecutionTerms(BaseModel):
    measurements: Optional[ExtractedField] = None
    measurement_period: Optional[ExtractedField] = None
    work_acceptance: Optional[ExtractedField] = None
    technical_responsibility: Optional[ExtractedField] = None
    subcontracting: Optional[ExtractedField] = None
    subcontracting_limit: Optional[ExtractedField] = None
    quality_standards: Optional[ExtractedField] = None


class Penalties(BaseModel):
    contractual_fine: Optional[ExtractedField] = None
    fine_percentage: Optional[ExtractedField] = None
    delay_fine: Optional[ExtractedField] = None
    delay_fine_per_day: Optional[ExtractedField] = None
    other_penalties: List[ExtractedField] = Field(default_factory=list)


class Guarantees(BaseModel):
    guarantee_type: Optional[ExtractedField] = None
    guarantee_value: Optional[ExtractedField] = None
    guarantee_percentage: Optional[ExtractedField] = None
    guarantee_duration: Optional[ExtractedField] = None
    warranty_period: Optional[ExtractedField] = None
    defect_liability: Optional[ExtractedField] = None


class Responsibilities(BaseModel):
    technical_responsibility: Optional[ExtractedField] = None
    art_rrt_responsibility: Optional[ExtractedField] = None
    insurance: Optional[ExtractedField] = None
    insurance_types: List[ExtractedField] = Field(default_factory=list)
    labor_obligations: Optional[ExtractedField] = None
    environmental_obligations: Optional[ExtractedField] = None
    safety_obligations: Optional[ExtractedField] = None
    material_supply: Optional[ExtractedField] = None


class RescissionTerms(BaseModel):
    grounds_for_rescission: Optional[ExtractedField] = None
    notice_period: Optional[ExtractedField] = None
    consequences: Optional[ExtractedField] = None
    compensation_on_rescission: Optional[ExtractedField] = None


class LegalClauses(BaseModel):
    jurisdiction: Optional[ExtractedField] = None
    dispute_resolution: Optional[ExtractedField] = None
    applicable_law: Optional[ExtractedField] = None
    arbitration: Optional[ExtractedField] = None
    relevant_clauses: List[LegalClause] = Field(default_factory=list)


class ConfidenceSummary(BaseModel):
    overall_confidence: float = Field(0.0, ge=0.0, le=1.0)
    fields_extracted: int = 0
    fields_missing: int = 0
    ocr_used: bool = False
    pages_processed: int = 0
    total_characters: int = 0
    extraction_method: str = "native_pdf"   # "native_pdf" | "ocr" | "hybrid"
    extraction_warnings: List[ExtractionWarning] = Field(default_factory=list)


# ── Root model ────────────────────────────────────────────────────────────────

class ContractJSON(BaseModel):
    """
    Root model for Phase 1 output: structured contract data extracted from PDF.
    """
    schema_version: str = "1.0.0"
    extraction_timestamp: str
    source_file: str

    contract_metadata: Optional[ContractMetadata] = None
    parties: Optional[Parties] = None
    work_object: Optional[WorkObject] = None
    financial_terms: Optional[FinancialTerms] = None
    schedule: Optional[Schedule] = None
    execution_terms: Optional[ExecutionTerms] = None
    penalties: Optional[Penalties] = None
    guarantees: Optional[Guarantees] = None
    responsibilities: Optional[Responsibilities] = None
    rescission_terms: Optional[RescissionTerms] = None
    legal_clauses: Optional[LegalClauses] = None

    extracted_evidence: List[str] = Field(default_factory=list)
    raw_text_pages: List[RawTextPage] = Field(default_factory=list)
    confidence_summary: ConfidenceSummary = Field(default_factory=ConfidenceSummary)
