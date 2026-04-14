"""
Serviço de análise via LLM (Groq).

Usa o SDK oficial da Groq com response_format JSON para garantir saída válida.
O texto do contrato entra no turno do usuário; o system prompt permanece fixo.
"""

import json

from groq import Groq

from core.config import settings
from schemas.contract_analysis import ContractAnalysis

# ──────────────────────────────────────────────
# Prompt do sistema — define o comportamento do modelo
# ──────────────────────────────────────────────
SYSTEM_PROMPT = """Você é um assistente especializado em análise preliminar de contratos de construção civil brasileiros.

Seu papel é identificar cláusulas suspeitas, ambíguas ou abusivas no texto fornecido e apresentar os resultados de forma clara para pessoas sem formação jurídica.

REGRAS ABSOLUTAS:
1. Analise SOMENTE o texto que for fornecido. Não invente cláusulas.
2. Se o texto estiver incompleto ou ilegível, reduza a confiança e informe nas "informacoes_faltantes".
3. Esta análise NÃO é um parecer jurídico. Indique isso na "recomendacao".
4. Toda a saída deve estar em português do Brasil.
5. Retorne EXCLUSIVAMENTE um JSON válido, sem texto fora do JSON.

FORMATO DE SAÍDA OBRIGATÓRIO (JSON):
{
  "tipo_documento": "string — tipo de contrato identificado",
  "confianca_geral": 0.0,
  "resumo": "string — resumo objetivo em 2-4 frases",
  "riscos": [
    {
      "trecho_clausula": "string — trecho ou paráfrase da cláusula",
      "categoria": "string — ex: rescisão, multa, prazo, responsabilidade",
      "gravidade": "baixa | media | alta",
      "por_que_importa": "string — explicação clara para leigo",
      "evidencia": "string — fragmento exato do texto que embasou o risco",
      "pergunta_sugerida": "string — pergunta para fazer ao advogado",
      "confianca": 0.0
    }
  ],
  "informacoes_faltantes": ["string"],
  "recomendacao": "string — recomendação geral + lembrete de que não é parecer jurídico"
}

CRITÉRIOS DE GRAVIDADE:
- alta: cláusula que pode causar perda financeira significativa, prisão de responsabilidade ilimitada, ou renúncia a direito fundamental
- media: cláusula desequilibrada ou que favorece excessivamente uma parte
- baixa: redação ambígua, prazo curto, ou ausência de informação relevante

Seja objetivo e direto. Prefira menos riscos bem fundamentados a uma lista longa e superficial."""


_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def analyze_contract(contract_text: str) -> ContractAnalysis:
    """
    Envia o texto do contrato ao modelo Groq e retorna a análise estruturada.

    response_format={"type": "json_object"} força o modelo a retornar JSON válido,
    eliminando a necessidade de limpar blocos de markdown na resposta.
    """
    client = _get_client()

    response = client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=2048,
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Analise o seguinte texto de contrato:\n\n<contrato>\n{contract_text}\n</contrato>",
            },
        ],
    )

    raw_text = response.choices[0].message.content.strip()
    data = json.loads(raw_text)
    return ContractAnalysis.model_validate(data)
