"""
Pydantic v2 models for the risk analysis JSON (Phase 2 output).

The LLM analyst receives the ContractJSON and returns a RiskAnalysisJSON.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

class RiskCategory(str, Enum):
    FINANCIAL = "financial"
    LEGAL = "legal"
    SCHEDULE = "schedule"
    SCOPE = "scope"
    TECHNICAL = "technical"
    PENALTIES = "penalties"
    MEASUREMENT = "measurement"
    RESCISSION = "rescission"
    COMPLIANCE = "compliance"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskType(str, Enum):
    FACT = "fact"
    INFERENCE = "inference"
    RECOMMENDATION = "recommendation"


class OverallRiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Priority(str, Enum):
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ── Section models ────────────────────────────────────────────────────────────

class ContractSummary(BaseModel):
    brief_description: str
    parties_summary: str
    value_summary: str
    duration_summary: str
    object_summary: str
    key_dates: List[str] = Field(default_factory=list)


class DetectedRisk(BaseModel):
    id: str                                           # e.g. "RISK-001"
    category: RiskCategory
    title: str
    description: str
    severity: Severity
    evidence: str                                     # verbatim from contract JSON
    clause_reference: Optional[str] = None
    type: RiskType
    uncertainty: Optional[str] = None                # filled when type == "inference"
    recommendations: List[str] = Field(default_factory=list)


class MissingInformation(BaseModel):
    field: str                                        # JSON path, e.g. "financial_terms.total_value"
    importance: Severity
    risk_implication: str
    recommendation: str


class AbnormalClause(BaseModel):
    clause_reference: Optional[str] = None
    content: str
    issue: str
    severity: Severity
    legal_basis: Optional[str] = None                # e.g. "Art. 413 CC/2002"
    recommendation: str


class EvidenceEntry(BaseModel):
    risk_id: str
    source_field: str
    evidence_text: str
    page: Optional[int] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class EvidenceMap(BaseModel):
    used_fields: List[str] = Field(default_factory=list)
    source_pages: List[int] = Field(default_factory=list)
    average_confidence: float = Field(0.0, ge=0.0, le=1.0)
    low_confidence_fields: List[str] = Field(default_factory=list)
    evidence_entries: List[EvidenceEntry] = Field(default_factory=list)


class Recommendation(BaseModel):
    priority: Priority
    action: str
    justification: str
    related_risks: List[str] = Field(default_factory=list)   # list of risk IDs


class ModelNotes(BaseModel):
    analysis_date: str
    model_used: str
    disclaimer: str
    uncertainty_flags: List[str] = Field(default_factory=list)
    analysis_limitations: List[str] = Field(default_factory=list)


# ── Root model ────────────────────────────────────────────────────────────────

class RiskAnalysisJSON(BaseModel):
    """
    Root model for Phase 2 output: LLM risk analysis of the contract JSON.
    """
    schema_version: str = "1.0.0"
    analysis_timestamp: str
    source_contract_file: str

    contract_summary: ContractSummary
    overall_risk_level: OverallRiskLevel
    severity_score: float = Field(0.0, ge=0.0, le=10.0)   # 0 = no risk, 10 = critical

    detected_risks: List[DetectedRisk] = Field(default_factory=list)
    missing_information: List[MissingInformation] = Field(default_factory=list)
    abnormal_clauses: List[AbnormalClause] = Field(default_factory=list)

    evidence_map: EvidenceMap = Field(default_factory=EvidenceMap)
    recommendations: List[Recommendation] = Field(default_factory=list)
    model_notes: ModelNotes
