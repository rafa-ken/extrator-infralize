# Extrator Infralize

API para análise de riscos em contratos de construção civil a partir de PDFs.

Recebe um PDF do contrato, faz OCR página por página e usa IA (Groq) para identificar cláusulas suspeitas, ambíguas ou abusivas. A resposta é um JSON estruturado em português do Brasil.

> Esta ferramenta não substitui revisão jurídica profissional.

---

## Como funciona

```
PDF → pdf2image (Poppler) → páginas → OCR (Tesseract) → texto → Groq → JSON com riscos
```

Se a qualidade do OCR estiver baixa, a resposta inclui um aviso explícito.

---

## Pré-requisitos

- Python 3.11+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) instalado no sistema
  - Durante a instalação, marque os pacotes de idioma **Português** e **English**
- [Poppler](https://github.com/oschwartz10612/poppler-windows/releases) instalado no sistema (necessário para o `pdf2image`)
  - Windows: baixe, extraia e adicione a pasta `bin/` ao PATH
- Chave de API da [Groq](https://console.groq.com/keys)

---

## Instalação

```bash
# 1. Crie e ative o ambiente virtual
python -m venv .venv
source .venv/Scripts/activate   # Windows
# source .venv/bin/activate     # Linux/macOS

# 2. Instale as dependências
pip install -r requirements.txt

# 3. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env e preencha GROQ_API_KEY
```

---

## Rodando

```bash
uvicorn main:app --reload
```

A API sobe em `http://localhost:8000`.
Documentação interativa disponível em `http://localhost:8000/docs`.

---

## Endpoints

### `POST /analyze-contract`

Recebe um PDF do contrato e retorna a análise.

**Formato aceito:** PDF  
**Tamanho máximo:** 20 MB

```bash
curl -X POST http://localhost:8000/analyze-contract \
  -F "file=@pdfs/contrato.pdf"
```

**Resposta:**

```json
{
  "ocr_warning": {
    "has_warning": false,
    "message": ""
  },
  "texto_extraido": "...",
  "analise": {
    "tipo_documento": "Contrato de Empreitada",
    "confianca_geral": 0.85,
    "resumo": "Contrato de construção com prazo de 120 dias...",
    "riscos": [
      {
        "trecho_clausula": "Cláusula 5ª — multa de 20%",
        "categoria": "multa",
        "gravidade": "alta",
        "por_que_importa": "Multa aplicada apenas ao contratante, sem reciprocidade.",
        "evidencia": "O CONTRATANTE pagará multa de 20% sobre o valor total.",
        "pergunta_sugerida": "A multa também se aplica ao contratado em caso de atraso?",
        "confianca": 0.9
      }
    ],
    "informacoes_faltantes": ["Prazo de garantia da obra"],
    "recomendacao": "Consulte um advogado antes de assinar. Esta análise não é um parecer jurídico."
  }
}
```

### `GET /health`

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

---

## Variáveis de ambiente

| Variável | Obrigatória | Padrão | Descrição |
|---|---|---|---|
| `GROQ_API_KEY` | sim | — | Chave da API Groq |
| `GROQ_MODEL` | não | `llama-3.3-70b-versatile` | Modelo a usar |
| `OCR_CONFIDENCE_THRESHOLD` | não | `40.0` | Confiança mínima do OCR (0–100) antes de emitir aviso |
| `TESSERACT_LANG` | não | `por+eng` | Idiomas do Tesseract |

---

## Estrutura do projeto

```
extrator-infralize/
├── main.py                    # App FastAPI e rotas
├── services/
│   ├── ocr.py                 # OCR com pytesseract (substituível)
│   └── llm.py                 # Análise via Claude
├── schemas/
│   └── contract_analysis.py   # Modelos Pydantic da resposta
├── core/
│   └── config.py              # Configurações via .env
├── requirements.txt
└── .env.example
```

---

## Trocando o motor de OCR

O serviço de OCR está isolado em `services/ocr.py`. Para usar outro motor (Google Vision, AWS Textract, etc.), implemente uma função com a mesma assinatura e substitua a chamada em `main.py`:

```python
# services/ocr.py
def extract_text(image_bytes: bytes, lang: str = "por+eng") -> OCRResult:
    ...
```
