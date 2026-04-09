# extrator-infralize

Pipeline de análise de contratos de construção civil em PDF usando Claude.

## Arquitetura

```
PDF
 │
 ▼ Fase 1 — Extração de texto
PDFReader (pdfplumber + OCR fallback)
 │
 ▼ Fase 2 — Estruturação via LLM
ContractParser → contract.json   (schema: ContractJSON)
 │
 ▼ Fase 3 — Análise de risco via LLM
RiskAnalyzer  → analysis.json   (schema: RiskAnalysisJSON)
```

```
extrator-infralize/
├── main.py                      # CLI + orquestrador da pipeline
├── src/
│   ├── extractor/
│   │   ├── pdf_reader.py        # PDF → texto por página (nativo + OCR)
│   │   ├── ocr_processor.py     # Tesseract OCR para PDFs escaneados
│   │   └── text_cleaner.py      # Normalização e limpeza de texto
│   ├── parser/
│   │   ├── contract_parser.py   # Texto → ContractJSON via LLM
│   │   └── validators.py        # Validação Pydantic com fallback parcial
│   ├── analyzer/
│   │   ├── risk_analyzer.py     # ContractJSON → RiskAnalysisJSON via LLM
│   │   └── prompts.py           # System prompts e templates de usuário
│   ├── schemas/
│   │   ├── contract_schema.py   # Pydantic: estrutura do contrato extraído
│   │   └── analysis_schema.py   # Pydantic: estrutura da análise de risco
│   └── utils/
│       ├── logger.py            # Logging via loguru
│       └── error_handler.py     # Exceções customizadas + retry com backoff
└── output/                      # Gerado automaticamente
    └── <nome-do-pdf>/
        ├── contract.json
        ├── analysis.json
        ├── raw_text.txt
        └── pipeline_<timestamp>.log
```

## Pré-requisitos

### Python
Python 3.11+

### Dependências do sistema

**Para PDFs escaneados (OCR):**

- **Tesseract OCR** — [instalação](https://github.com/tesseract-ocr/tesseract)
  - Windows: baixe o instalador em https://github.com/UB-Mannheim/tesseract/wiki
  - Linux: `sudo apt install tesseract-ocr tesseract-ocr-por`
  - Mac: `brew install tesseract`

- **Poppler** (necessário pelo pdf2image)
  - Windows: baixe em https://github.com/oschwartz10612/poppler-windows/releases e adicione ao PATH
  - Linux: `sudo apt install poppler-utils`
  - Mac: `brew install poppler`

## Instalação

```bash
# 1. Clone o repositório
git clone <repo-url>
cd extrator-infralize

# 2. Crie e ative o ambiente virtual
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 3. Instale as dependências Python
pip install -r requirements.txt

# 4. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env e preencha ANTHROPIC_API_KEY e (se necessário) TESSERACT_CMD
```

## Uso

```bash
# Análise completa (extração + risco)
python main.py analyze contrato.pdf

# Apenas extração (sem análise de risco)
python main.py analyze contrato.pdf --skip-analysis

# Diretório de saída customizado
python main.py analyze contrato.pdf --output-dir resultados/

# Log detalhado
python main.py analyze contrato.pdf --log-level DEBUG
```

## Saída

### `contract.json` — Contrato Estruturado

Cada campo extraído segue o padrão:
```json
{
  "value": "R$ 1.500.000,00",
  "confidence": 0.97,
  "evidence": "O valor global da obra é de R$ 1.500.000,00...",
  "page": 2
}
```

### `analysis.json` — Análise de Risco

```json
{
  "overall_risk_level": "high",
  "severity_score": 7.2,
  "detected_risks": [
    {
      "id": "RISK-001",
      "category": "financial",
      "severity": "high",
      "title": "Ausência de índice de reajuste",
      "type": "fact",
      "evidence": "..."
    }
  ]
}
```

Categorias: `financial` · `legal` · `schedule` · `scope` · `technical` · `penalties` · `measurement` · `rescission` · `compliance`

Severidades: `critical` · `high` · `medium` · `low`

## Notas

- Esta análise **não substitui revisão jurídica profissional**.
- Campos com `confidence < 0.7` devem ser revisados manualmente.
- OCR é opcional — PDFs com texto nativo funcionam sem Tesseract/Poppler.
- Cada análise realiza **2 chamadas ao Claude** (extração + análise de risco).
