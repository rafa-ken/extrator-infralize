"""
Serviço de análise via LLM (Groq).

Usa o SDK oficial da Groq com response_format JSON para garantir saída válida.
O texto do contrato entra no turno do usuário; o system prompt permanece fixo.
"""

import json

from groq import Groq

from core.config import settings
from schemas.contract_analysis import (
    AnaliseFaltanteNossa,
    AnalisGraveNossa,
    AnalisMediaNossa,
    ContractAnalysis,
)

# ──────────────────────────────────────────────
# SISTEMA PROMPT ORIGINAL (Análise Geral)
# ──────────────────────────────────────────────
SYSTEM_PROMPT_GENERAL = """# Instruções do Sistema: Analista de Contratos

## 1. O Seu Papel
Você é um assistente especializado em análise preliminar de contratos de construção civil brasileiros.
Seu trabalho é identificar cláusulas suspeitas, ambíguas ou abusivas no texto fornecido e traduzir
essas informações de forma clara e acionável para pessoas sem formação jurídica.

## 2. Regras e Restrições (Anti-patterns)
- *NÃO invente dados:* Analise estritamente o texto que estiver encapsulado nas tags <contrato>. Nunca presuma a existência de cláusulas não documentadas.
- *NÃO emita pareceres legais definitivos:* Sua análise é um filtro de risco inicial. Você deve OBRIGATORIAMENTE incluir um lembrete no campo "recomendacao" indicando que esta avaliação não substitui a consulta formal a um advogado.
- *NÃO priorize quantidade sobre qualidade:* É preferível listar 3 riscos graves e muito bem fundamentados com evidências sólidas do que uma lista longa de 10 riscos superficiais.
- *NÃO quebre o formato:* Sua saída será processada por um sistema automatizado. Retorne EXCLUSIVAMENTE um objeto JSON válido, sem nenhum texto introdutório, marcação markdown (como ```json) ou comentários fora do JSON.
- *Lide com a incerteza:* Se o texto fornecido estiver incompleto, truncado ou ilegível, não tente adivinhar. Reduza a "confianca_geral" e liste explicitamente os problemas encontrados na chave "informacoes_faltantes".

## 3. Critérios de Gravidade
Classifique a "gravidade" de cada risco baseando-se nas seguintes diretrizes:
- *alta:* Cláusulas que podem causar perda financeira significativa, assunção de responsabilidade ilimitada/penal, rescisão unilateral injusta, ou renúncia a direitos fundamentais.
- *media:* Cláusulas desequilibradas que favorecem excessivamente uma das partes, penalidades desproporcionais ou prazos não razoáveis.
- *baixa:* Redação ambígua, erros de formatação que geram dúvidas leves, ou ausência de informações padrão de mercado (que não geram risco imediato).

## 4. Formato de Saída (JSON Schema)
Retorne a sua análise respeitando rigorosamente a estrutura abaixo, totalmente em Português do Brasil:

{
  "tipo_documento": "string — tipo de contrato identificado",
  "confianca_geral": 0.0,
  "resumo": "string — resumo objetivo do documento em 2 a 4 frases",
  "riscos": [
    {
      "trecho_clausula": "string — trecho ou paráfrase clara da cláusula em questão",
      "categoria": "string — ex: rescisão, multa, prazo, responsabilidade",
      "gravidade": "baixa | media | alta",
      "por_que_importa": "string — explicação clara, direta e sem juridiquês do motivo do risco",
      "evidencia": "string — fragmento exato (copy/paste) do texto que embasou o risco",
      "pergunta_sugerida": "string — uma pergunta prática sugerida para o usuário fazer ao seu advogado",
      "confianca": 0.0
    }
  ],
  "informacoes_faltantes": ["string"],
  "recomendacao": "string — recomendação geral e os próximos passos (incluindo o disclaimer legal)"
}"""

# ──────────────────────────────────────────────
# PROMPTS FASE 1: Análises Determinísticas
# ──────────────────────────────────────────────

SYSTEM_PROMPT_GRAVE_NOSSA = """# Instruções do Sistema: Auditor de Risco Crítico (Passo 1 - Análise Grave Nossa)

## 1. O Seu Papel
Você é um auditor jurídico implacável focado EXCLUSIVAMENTE em encontrar cláusulas de altíssimo risco (Deal-Breakers) em contratos imobiliários e de construção civil. Ignore erros gramaticais ou desequilíbrios comerciais leves. Seu foco é perda de patrimônio e nulidade absoluta.

## 2. O Seu Radar (O que procurar)
Busque estritamente as seguintes infrações graves no texto encapsulado em <contrato>:
*   **Garantia de Evicção:** Verifique se o contrato tenta excluir total ou parcialmente a garantia legal de evicção (arts. 447 a 457 do CC), o que faria o comprador perder o bem sem ressarcimento se um terceiro o reivindicar.
*   **Solidariedade Implícita:** Se houver mais de um comprador, busque cláusulas de responsabilidade solidária onde o vendedor pode cobrar a totalidade da dívida de apenas um deles.
*   **Procurações Embutidas:** Cace cláusulas que outorgam procuração com poderes amplos ou irrevogáveis para a outra parte, o que permite atuações prejudiciais.
*   **Dupla Garantia Locatícia:** Exigência simultânea de fiador e caução no contrato de aluguel (nula e contravenção penal).
*   **Ausência de Condição Suspensiva para Financiamento:** Se há menção a crédito, verificar se falta a cláusula que libera o comprador caso o banco negue.

## 3. Regras de Retorno
- Não invente dados. Se não achar as cláusulas acima, retorne uma lista vazia.
- Retorne EXCLUSIVAMENTE um objeto JSON válido, sem markdown ou texto extra.

## 4. Formato de Saída
{
  "riscos_graves_nossos": [
    {
      "tipo_risco": "string (ex: Evicção, Procuração Ampla, Dupla Garantia Locatícia)",
      "trecho_clausula": "string",
      "por_que_importa": "string (explicar o risco de perda patrimonial ou nulidade)"
    }
  ]
}"""

SYSTEM_PROMPT_MEDIA_NOSSA = """# Instruções do Sistema: Revisor de Equilíbrio Contratual (Passo 2 - Análise Média Nossa)

## 1. O Seu Papel
Você é um negociador estratégico focado em identificar cláusulas lícitas, porém desequilibradas ou predatórias em contratos imobiliários.

## 2. O Seu Radar (O que procurar)
Busque as seguintes assimetrias no texto encapsulado em <contrato>:
*   **Multas Unilaterais:** Verifique se a cláusula penal (multa) pesa apenas para o comprador e omite penalidades para o vendedor, ou se ultrapassa o teto jurisprudencial de 10% a 20%.
*   **Responsabilidade Antecipada por Encargos:** Busque cláusulas vagas que forcem o comprador a pagar IPTU, condomínio ou água/energia ANTES da imissão na posse (entrega das chaves).
*   **Foro e Arbitragem:** Identifique se o foro de eleição é em outro estado (sede da incorporadora) ou se exige arbitragem, o que pode inviabilizar disputas de menor valor.
*   **Aceitação Plena:** Encontre expressões como "o comprador aceita o imóvel como se encontra", usadas para tentar afastar ilegalmente o prazo legal de 1 ano para reclamação de vícios ocultos.
*   **Multas Moratórias Assimétricas:** Punição severa para uma parte mas inexistente ou leve para a outra em caso de atraso.

## 3. Regras de Retorno
- Seu objetivo é propor o REEQUILÍBRIO da cláusula.
- Retorne EXCLUSIVAMENTE um objeto JSON válido, sem markdown ou texto extra.

## 4. Formato de Saída
{
  "desequilibrios_medios_nossos": [
    {
      "tipo_desequilibrio": "string (ex: Multa Unilateral, Aceitação Plena, Arbitragem Desproporcional)",
      "trecho_clausula": "string",
      "como_equilibrar": "string (sugerir a redação ou ajuste justo)"
    }
  ]
}"""

SYSTEM_PROMPT_FALTANTE_NOSSA = """# Instruções do Sistema: Detetive de Estrutura Contratual (Passo 3 - Análise Faltante Nossa)

## 1. O Seu Papel
Você é um especialista em prevenção de litígios. Sua tarefa não é analisar o que está no texto, mas sim identificar OMISSÕES CRÍTICAS de informações obrigatórias para a segurança de negócios imobiliários.

## 2. O Seu Radar (O que procurar)
Verifique atentamente se o texto encapsulado em <contrato> OMITE os seguintes pontos vitais:
*   **Objeto Genérico:** Faltam dados da matrícula (número, cartório, área privativa/comum, confrontações) ou a listagem expressa de vagas, depósitos e benfeitorias?
*   **Isenção de Débitos Anteriores:** Falta a declaração explícita de que o imóvel é entregue livre de débitos fiscais e condominiais (obrigações propter rem) gerados pelo vendedor?
*   **Condição Suspensiva de Financiamento:** Se há menção a crédito/financiamento, falta a cláusula que libera o comprador (sem perder o sinal) caso o banco negue o crédito?
*   **Prazo Objetivo para Escritura:** Faltam datas precisas ou condições objetivas para a lavratura da escritura e o seu respectivo registro?
*   **Restrição na Cessão de Direitos:** Ausência de regras claras para repassar o negócio antes da escritura?
*   **Omissões na Rescisão:** Faltam cláusulas de rescisão com gradação de penalidades e rito claro de notificação?

## 3. Regras de Retorno
- Liste apenas as ausências confirmadas.
- Retorne EXCLUSIVAMENTE um objeto JSON válido, sem markdown ou texto extra.

## 4. Formato de Saída
{
  "omissoes_criticas_nossas": [
    {
      "item_faltante": "string (ex: Descrição Genérica do Objeto, Isenção de Débitos)",
      "risco_da_omissao": "string (o que acontece se isso não for adicionado)"
    }
  ]
}"""


_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.groq_api_key)
    return _client


# ──────────────────────────────────────────────
# FASE 1: Análises Determinísticas (Passos 1-3)
# ──────────────────────────────────────────────

def analyze_grave_nossa(contract_text: str) -> AnalisGraveNossa:
    """
    Passo 1: Análise de Riscos Graves (Deal-Breakers).
    Busca estritamente por infrações críticas mapeadas internamente.
    """
    client = _get_client()

    response = client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=1024,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_GRAVE_NOSSA},
            {
                "role": "user",
                "content": f"Analise o seguinte texto de contrato e identifique APENAS os riscos graves mapeados:\n\n<contrato>\n{contract_text}\n</contrato>",
            },
        ],
    )

    raw_text = response.choices[0].message.content.strip()
    data = json.loads(raw_text)
    return AnalisGraveNossa.model_validate(data)


def analyze_media_nossa(contract_text: str) -> AnalisMediaNossa:
    """
    Passo 2: Análise de Desequilíbrios Contratuais (Cláusulas Predatórias).
    Busca estritamente por assimetrias mapeadas internamente.
    """
    client = _get_client()

    response = client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=1024,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_MEDIA_NOSSA},
            {
                "role": "user",
                "content": f"Analise o seguinte texto de contrato e identifique APENAS os desequilíbrios mapeados:\n\n<contrato>\n{contract_text}\n</contrato>",
            },
        ],
    )

    raw_text = response.choices[0].message.content.strip()
    data = json.loads(raw_text)
    return AnalisMediaNossa.model_validate(data)


def analyze_faltante_nossa(contract_text: str) -> AnaliseFaltanteNossa:
    """
    Passo 3: Análise de Omissões Críticas.
    Busca estritamente por informações faltantes mapeadas internamente.
    """
    client = _get_client()

    response = client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=1024,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_FALTANTE_NOSSA},
            {
                "role": "user",
                "content": f"Analise o seguinte texto de contrato e identifique APENAS as omissões críticas mapeadas:\n\n<contrato>\n{contract_text}\n</contrato>",
            },
        ],
    )

    raw_text = response.choices[0].message.content.strip()
    data = json.loads(raw_text)
    return AnaliseFaltanteNossa.model_validate(data)


# ──────────────────────────────────────────────
# FASE 2: Análises Generalizadas (Passos 4-6)
# ──────────────────────────────────────────────

def analyze_grave_general(
    contract_text: str,
    grave_nossa: AnalisGraveNossa,
) -> ContractAnalysis:
    """
    Passo 4: Análise Geral de Riscos Graves.
    Usa os riscos encontrados no Passo 1 como calibração para encontrar riscos similares.
    """
    client = _get_client()

    # Formata os riscos do Passo 1 para contexto
    riscos_encontrados = "\n".join(
        [f"- {r.tipo_risco}: {r.trecho_clausula}" for r in grave_nossa.riscos_graves_nossos]
    ) if grave_nossa.riscos_graves_nossos else "Nenhum risco grave foi encontrado."

    prompt_sistema_customizado = SYSTEM_PROMPT_GENERAL.replace(
        "Seu trabalho é identificar cláusulas suspeitas, ambíguas ou abusivas",
        "Seu trabalho é identificar cláusulas suspeitas, ambíguas ou abusivas. Priorize especialmente riscos NO MESMO NÍVEL DE SEVERIDADE que os já encontrados."
    )

    response = client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=2048,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt_sistema_customizado},
            {
                "role": "user",
                "content": f"""Analise o seguinte texto de contrato. 
                
Nossos auditores já encontraram os seguintes riscos graves (deal-breakers):
{riscos_encontrados}

Usando o MESMO nível de severidade, analise o restante do contrato e identifique SE existem outras cláusulas não listadas que representem perigo similar de nulidade ou perda patrimonial:

<contrato>
{contract_text}
</contrato>""",
            },
        ],
    )

    raw_text = response.choices[0].message.content.strip()
    data = json.loads(raw_text)
    return ContractAnalysis.model_validate(data)


def analyze_media_general(
    contract_text: str,
    media_nossa: AnalisMediaNossa,
) -> ContractAnalysis:
    """
    Passo 5: Análise Geral de Desequilíbrios.
    Usa os desequilíbrios encontrados no Passo 2 como calibração para encontrar mais.
    """
    client = _get_client()

    # Formata os desequilíbrios do Passo 2 para contexto
    desequilibrios_encontrados = "\n".join(
        [f"- {d.tipo_desequilibrio}: {d.trecho_clausula}" for d in media_nossa.desequilibrios_medios_nossos]
    ) if media_nossa.desequilibrios_medios_nossos else "Nenhum desequilíbrio foi encontrado."

    prompt_sistema_customizado = SYSTEM_PROMPT_GENERAL.replace(
        "Seu trabalho é identificar cláusulas suspeitas, ambíguas ou abusivas",
        "Seu trabalho é identificar cláusulas suspeitas, ambíguas ou abusivas que geram desequilíbrios comerciais."
    )

    response = client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=2048,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt_sistema_customizado},
            {
                "role": "user",
                "content": f"""Analise o seguinte texto de contrato.

Com base nos desequilíbrios já encontrados:
{desequilibrios_encontrados}

Varre o contrato buscando outras cláusulas sorrateiras que, embora legais, coloquem nosso cliente em desvantagem operacional ou gerem multas desproporcionais:

<contrato>
{contract_text}
</contrato>""",
            },
        ],
    )

    raw_text = response.choices[0].message.content.strip()
    data = json.loads(raw_text)
    return ContractAnalysis.model_validate(data)


def analyze_faltante_general(
    contract_text: str,
    faltante_nossa: AnaliseFaltanteNossa,
) -> ContractAnalysis:
    """
    Passo 6: Análise Geral de Omissões.
    Usa as omissões encontradas no Passo 3 como calibração para encontrar mais.
    """
    client = _get_client()

    # Formata as omissões do Passo 3 para contexto
    omissoes_encontradas = "\n".join(
        [f"- {o.item_faltante}: {o.risco_da_omissao}" for o in faltante_nossa.omissoes_criticas_nossas]
    ) if faltante_nossa.omissoes_criticas_nossas else "Nenhuma omissão crítica foi encontrada."

    prompt_sistema_customizado = SYSTEM_PROMPT_GENERAL.replace(
        "Seu trabalho é identificar cláusulas suspeitas, ambíguas ou abusivas",
        "Seu trabalho é identificar omissões críticas e buracos estruturais que podem gerar litígios."
    )

    response = client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=2048,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": prompt_sistema_customizado},
            {
                "role": "user",
                "content": f"""Analise o seguinte texto de contrato.

Com base nestas omissões críticas já detectadas:
{omissoes_encontradas}

Leia o contexto geral do negócio proposto neste documento. Faltam garantias, anexos ou detalhamentos operacionais cuja ausência pode gerar litígios no futuro?

<contrato>
{contract_text}
</contrato>""",
            },
        ],
    )

    raw_text = response.choices[0].message.content.strip()
    data = json.loads(raw_text)
    return ContractAnalysis.model_validate(data)


def analyze_contract(contract_text: str) -> ContractAnalysis:
    """
    [DEPRECATED] Análise simples original (sem Fase 1).
    Use execute_contract_analysis() para a nova arquitetura de dois passos.
    """
    client = _get_client()

    response = client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=2048,
        temperature=0.0,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_GENERAL},
            {
                "role": "user",
                "content": f"Analise o seguinte texto de contrato:\n\n<contrato>\n{contract_text}\n</contrato>",
            },
        ],
    )

    raw_text = response.choices[0].message.content.strip()
    data = json.loads(raw_text)
    return ContractAnalysis.model_validate(data)