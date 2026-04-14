from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class Gravidade(str, Enum):
    baixa = "baixa"
    media = "media"
    alta = "alta"


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
