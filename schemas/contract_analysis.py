from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class Gravidade(str, Enum):
    baixa = "baixa"
    media = "media"
    alta = "alta"


# ──────────────────────────────────────────────
# FASE 1: Análises Determinísticas Internas
# ──────────────────────────────────────────────

class RiscoGraveNosso(BaseModel):
    """Risco crítico identificado pela análise determinística (Passo 1)"""
    tipo_risco: str = Field(description="Tipo de risco (ex: Evicção, Procuração Ampla, Dupla Garantia)")
    trecho_clausula: str = Field(description="Trecho exato da cláusula problemática")
    por_que_importa: str = Field(description="Explicação clara do risco de perda patrimonial ou nulidade")


class AnalisGraveNossa(BaseModel):
    """Resultado da análise de riscos graves (deal-breakers) - Passo 1"""
    riscos_graves_nossos: List[RiscoGraveNosso] = Field(
        default_factory=list,
        description="Lista de riscos críticos encontrados"
    )


class DesequilibrioMedioNosso(BaseModel):
    """Desequilíbrio contratual identificado pela análise determinística (Passo 2)"""
    tipo_desequilibrio: str = Field(description="Tipo de desequilíbrio (ex: Multa Unilateral, Aceitação Plena)")
    trecho_clausula: str = Field(description="Trecho exato da cláusula desequilibrada")
    como_equilibrar: str = Field(description="Sugestão de redação ou ajuste justo")


class AnalisMediaNossa(BaseModel):
    """Resultado da análise de desequilíbrios médios (cláusulas predatórias) - Passo 2"""
    desequilibrios_medios_nossos: List[DesequilibrioMedioNosso] = Field(
        default_factory=list,
        description="Lista de desequilíbrios encontrados"
    )


class OmissaoCriticaNossa(BaseModel):
    """Omissão crítica identificada pela análise determinística (Passo 3)"""
    item_faltante: str = Field(description="O que está faltando no contrato")
    risco_da_omissao: str = Field(description="Qual é o risco se isso não for adicionado")


class AnaliseFaltanteNossa(BaseModel):
    """Resultado da análise de omissões críticas - Passo 3"""
    omissoes_criticas_nossas: List[OmissaoCriticaNossa] = Field(
        default_factory=list,
        description="Lista de informações faltantes"
    )


# ──────────────────────────────────────────────
# Schemas originais (compatibilidade)
# ──────────────────────────────────────────────

class Risco(BaseModel):
    trecho_clausula: str = Field(description="Trecho exato ou parafrase da cláusula problemática")
    categoria: str = Field(description="Ex: rescisão, multa, responsabilidade, prazo, etc.")
    gravidade: Gravidade
    por_que_importa: str = Field(description="Explicação simples do risco para o leigo")
    evidencia: str = Field(description="Fragmento textual do contrato que embasou o risco")
    pergunta_sugerida: str = Field(description="Pergunta que o contratante deveria fazer ao advogado")
    confianca: float = Field(ge=0.0, le=1.0, description="Confiança do modelo nesta análise (0–1)")


class ContractAnalysis(BaseModel):
    tipo_documento: str = Field(description="Tipo de contrato identificado")
    confianca_geral: float = Field(ge=0.0, le=1.0, description="Confiança geral da análise (0–1)")
    resumo: str = Field(description="Resumo objetivo do contrato em 2–4 frases")
    riscos: List[Risco] = Field(default_factory=list)
    informacoes_faltantes: List[str] = Field(
        default_factory=list,
        description="Informações importantes que deveriam constar mas estão ausentes",
    )
    recomendacao: str = Field(description="Recomendação geral de ação")


class OCRWarning(BaseModel):
    has_warning: bool
    message: str


class AnalyzeContractResponse(BaseModel):
    ocr_warning: OCRWarning
    texto_extraido: str = Field(description="Texto bruto extraído do documento")
    analise: ContractAnalysis
