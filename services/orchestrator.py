"""
Orquestrador de análise contratual em duas fases.

Fase 1: Executa Passos 1-3 em paralelo (análises determinísticas).
Fase 2: Usa os resultados de Fase 1 como calibração para Passos 4-6.
"""

import asyncio
from typing import Tuple

from schemas.contract_analysis import (
    AnaliseFaltanteNossa,
    AnalisGraveNossa,
    AnalisMediaNossa,
    ContractAnalysis,
)
from services import llm


async def execute_contract_analysis(contract_text: str) -> ContractAnalysis:
    """
    Executa a análise completa de contrato em dois estágios.

    **Fase 1 (Paralela):** Executa Passos 1-3 simultaneamente
    - Passo 1: Análise de Riscos Graves (Deal-Breakers)
    - Passo 2: Análise de Desequilíbrios Contratuais
    - Passo 3: Análise de Omissões Críticas

    **Fase 2 (Sequencial):** Usa resultados da Fase 1 como calibração
    - Passo 4: Análise Geral de Riscos Graves
    - Passo 5: Análise Geral de Desequilíbrios
    - Passo 6: Análise Geral de Omissões

    Retorna a análise final consolidada (resultado do Passo 4).
    """

    # ──────────────────────────────────────────────────────────────────────
    # FASE 1: Análises Determinísticas em Paralelo
    # ──────────────────────────────────────────────────────────────────────

    # Executa Passos 1-3 em paralelo usando asyncio.gather
    # Para executar funções síncronas em paralelo sem bloquear, usamos
    # loop.run_in_executor para cada uma
    loop = asyncio.get_event_loop()

    grave_nossa, media_nossa, faltante_nossa = await asyncio.gather(
        loop.run_in_executor(None, llm.analyze_grave_nossa, contract_text),
        loop.run_in_executor(None, llm.analyze_media_nossa, contract_text),
        loop.run_in_executor(None, llm.analyze_faltante_nossa, contract_text),
    )

    # ──────────────────────────────────────────────────────────────────────
    # FASE 2: Análises Generalizadas com Calibração
    # ──────────────────────────────────────────────────────────────────────

    # Executa Passos 4-6 em paralelo, usando os resultados da Fase 1
    analysis_grave, analysis_media, analysis_faltante = await asyncio.gather(
        loop.run_in_executor(None, llm.analyze_grave_general, contract_text, grave_nossa),
        loop.run_in_executor(None, llm.analyze_media_general, contract_text, media_nossa),
        loop.run_in_executor(None, llm.analyze_faltante_general, contract_text, faltante_nossa),
    )

    # ──────────────────────────────────────────────────────────────────────
    # Consolidação: Retorna o resultado do Passo 4 (análise grave geral)
    # ──────────────────────────────────────────────────────────────────────
    # Nota: Se desejar consolidar os três resultados (grave + media + faltante),
    # implemente aqui a lógica de merge. Por enquanto, retornamos o do Passo 4.

    return analysis_grave
