import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from core.config import settings
from schemas.contract_analysis import AnalyzeContractResponse, OCRWarning
from services import llm, ocr, text_cleaner

RESPOSTA_DIR = Path("resposta")
RESPOSTA_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="Extrator Infralize — Análise de Contratos",
    description="API para OCR e análise de riscos em contratos de construção civil.",
    version="0.1.0",
)

ALLOWED_TYPES = {"application/pdf"}
MAX_SIZE_MB = 20


@app.get("/health", tags=["infra"])
def health():
    return {"status": "ok"}


@app.post("/analyze-contract", response_model=AnalyzeContractResponse, tags=["análise"])
async def analyze_contract(file: UploadFile = File(..., description="PDF do contrato")):
    # ── Validação básica ─────────────────────────────────────────────────────
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Tipo de arquivo não suportado: {file.content_type}. Envie um PDF.",
        )

    image_bytes = await file.read()

    if len(image_bytes) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo muito grande. Tamanho máximo: {MAX_SIZE_MB} MB.",
        )

    # ── Extração de texto ────────────────────────────────────────────────────
    try:
        ocr_result = ocr.extract_text(image_bytes, lang=settings.tesseract_lang)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Falha na extração de texto: {exc}") from exc

    ocr_warning = OCRWarning(has_warning=False, message="")

    if not ocr_result.text:
        raise HTTPException(
            status_code=422,
            detail="Nenhum texto foi extraído do documento. Verifique se o PDF contém texto legível.",
        )

    if (
        ocr_result.extraction_method == "ocr"
        and ocr_result.mean_confidence < settings.ocr_confidence_threshold
    ):
        ocr_warning = OCRWarning(
            has_warning=True,
            message=(
                f"Qualidade do OCR baixa (confiança média: {ocr_result.mean_confidence:.1f}/100). "
                "O texto extraído pode conter erros. A análise pode ser imprecisa."
            ),
        )

    # ── Limpeza do texto ─────────────────────────────────────────────────────
    clean_text = text_cleaner.clean(ocr_result.text)

    # ── Análise via LLM ──────────────────────────────────────────────────────
    try:
        analysis = llm.analyze_contract(clean_text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Falha na análise do modelo: {exc}") from exc

    response = AnalyzeContractResponse(
        ocr_warning=ocr_warning,
        texto_extraido=clean_text,
        analise=analysis,
    )

    # ── Salva resultado em resposta/ ─────────────────────────────────────────
    stem = Path(file.filename).stem if file.filename else "contrato"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESPOSTA_DIR / f"{stem}_{timestamp}.json"
    output_path.write_text(response.model_dump_json(indent=2), encoding="utf-8")

    return response


# ── Handler de erros genéricos ───────────────────────────────────────────────
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Erro interno: {exc}"},
    )
