"""
extrator-infralize — Pipeline de Análise de Contratos de Construção Civil

Usage:
    python main.py analyze <pdf_path> [OPTIONS]
    python main.py analyze contrato.pdf --output-dir output/ --skip-analysis
    python main.py analyze contrato.pdf --log-level DEBUG
"""

from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

import click
from dotenv import load_dotenv
from loguru import logger

# Load .env before any module imports that use env vars
load_dotenv()

from src.extractor.pdf_reader import PDFReader
from src.parser.contract_parser import ContractParser
from src.analyzer.risk_analyzer import RiskAnalyzer
from src.schemas.contract_schema import ContractJSON
from src.schemas.analysis_schema import RiskAnalysisJSON
from src.utils.logger import setup_logging
from src.utils.error_handler import ExtractorError, ParsingError, AnalysisError


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline(
    pdf_path: Path,
    output_dir: Path,
    skip_analysis: bool = False,
    save_raw_text: bool = True,
) -> dict[str, Path]:
    """
    Execute the full extraction + analysis pipeline.

    Returns:
        Dict with paths to generated output files.
    """
    pdf_name = pdf_path.stem
    run_dir = output_dir / pdf_name
    run_dir.mkdir(parents=True, exist_ok=True)

    output_paths: dict[str, Path] = {}

    # ── Phase 1a: PDF → text ──────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(f"FASE 1: Extração de texto do PDF: {pdf_path.name}")
    logger.info("=" * 60)

    reader = PDFReader()
    try:
        pages = reader.read(pdf_path)
    except FileNotFoundError as exc:
        logger.error(str(exc))
        raise
    except Exception as exc:
        raise ExtractorError(f"Falha na leitura do PDF: {exc}") from exc

    extraction_summary = reader.extraction_summary(pages)
    logger.info(
        f"Resumo de extração: {extraction_summary['pages_processed']} páginas, "
        f"{extraction_summary['total_characters']:,} caracteres, "
        f"método: {extraction_summary['extraction_method']}"
    )

    # Save raw text for debugging
    if save_raw_text:
        raw_text_path = run_dir / "raw_text.txt"
        raw_lines = []
        for page in pages:
            raw_lines.append(f"{'='*40}")
            raw_lines.append(f"PÁGINA {page.page} [{page.method.upper()}]")
            raw_lines.append(f"{'='*40}")
            raw_lines.append(page.text)
            raw_lines.append("")
        raw_text_path.write_text("\n".join(raw_lines), encoding="utf-8")
        output_paths["raw_text"] = raw_text_path
        logger.debug(f"Texto bruto salvo em: {raw_text_path}")

    # ── Phase 1b: text → ContractJSON ─────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("FASE 2: Extração para JSON estruturado (LLM)")
    logger.info("=" * 60)

    parser = ContractParser()
    try:
        contract_json: ContractJSON = parser.parse(
            pages=pages,
            source_file=pdf_path.name,
            extraction_summary=extraction_summary,
        )
    except (ParsingError, Exception) as exc:
        logger.error(f"Falha na extração para JSON: {exc}")
        raise

    contract_path = run_dir / "contract.json"
    contract_path.write_text(
        contract_json.model_dump_json(indent=2, exclude_none=False),
        encoding="utf-8",
    )
    output_paths["contract_json"] = contract_path
    logger.info(f"Contract JSON salvo em: {contract_path}")

    if skip_analysis:
        logger.info("Análise de risco ignorada (--skip-analysis).")
        return output_paths

    # ── Phase 2: ContractJSON → RiskAnalysisJSON ──────────────────────────────
    logger.info("=" * 60)
    logger.info("FASE 3: Análise de risco (LLM)")
    logger.info("=" * 60)

    analyzer = RiskAnalyzer()
    try:
        analysis_json: RiskAnalysisJSON = analyzer.analyze(contract_json)
    except (AnalysisError, Exception) as exc:
        logger.error(f"Falha na análise de risco: {exc}")
        raise

    analysis_path = run_dir / "analysis.json"
    analysis_path.write_text(
        analysis_json.model_dump_json(indent=2, exclude_none=False),
        encoding="utf-8",
    )
    output_paths["analysis_json"] = analysis_path
    logger.info(f"Analysis JSON salvo em: {analysis_path}")

    return output_paths


def print_summary(output_paths: dict[str, Path]) -> None:
    """Print a human-readable summary to the console."""
    analysis_path = output_paths.get("analysis_json")
    if not analysis_path or not analysis_path.exists():
        return

    with analysis_path.open(encoding="utf-8") as f:
        data = json.load(f)

    click.echo("\n" + "=" * 60)
    click.echo("  RESUMO DA ANÁLISE DE RISCO")
    click.echo("=" * 60)

    summary = data.get("contract_summary", {})
    click.echo(f"\nDescrição: {summary.get('brief_description', 'N/D')}")
    click.echo(f"Partes:    {summary.get('parties_summary', 'N/D')}")
    click.echo(f"Valor:     {summary.get('value_summary', 'N/D')}")
    click.echo(f"Prazo:     {summary.get('duration_summary', 'N/D')}")

    level = data.get("overall_risk_level", "N/D").upper()
    score = data.get("severity_score", 0)
    level_colors = {
        "CRITICAL": "red",
        "HIGH": "yellow",
        "MEDIUM": "cyan",
        "LOW": "green",
    }
    color = level_colors.get(level, "white")
    click.echo(
        f"\nNível de risco: {click.style(level, fg=color, bold=True)} "
        f"(score: {score:.1f}/10)"
    )

    risks = data.get("detected_risks", [])
    click.echo(f"\nRiscos detectados: {len(risks)}")
    for risk in risks[:5]:   # show top 5
        sev = risk.get("severity", "?").upper()
        sev_color = level_colors.get(sev, "white")
        click.echo(
            f"  [{click.style(sev, fg=sev_color)}] "
            f"{risk.get('id', '?')} — {risk.get('title', '?')}"
        )
    if len(risks) > 5:
        click.echo(f"  ... e mais {len(risks) - 5} risco(s). Veja o JSON completo.")

    missing = data.get("missing_information", [])
    if missing:
        click.echo(f"\nInformações ausentes: {len(missing)}")
        for item in missing[:3]:
            click.echo(f"  [{item.get('importance', '?').upper()}] {item.get('field', '?')}")

    recs = data.get("recommendations", [])
    if recs:
        click.echo(f"\nRecomendações prioritárias:")
        for rec in recs[:3]:
            prio = rec.get("priority", "?").upper()
            click.echo(f"  [{prio}] {rec.get('action', '?')}")

    click.echo("\nArquivos gerados:")
    for label, path in output_paths.items():
        click.echo(f"  {label:15} → {path}")

    click.echo("\n" + "=" * 60)
    click.echo("AVISO: Esta análise não substitui revisão jurídica profissional.")
    click.echo("=" * 60 + "\n")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

@click.group()
def cli():
    """Extrator e analisador de contratos de construção civil."""


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir", "-o",
    default=None,
    type=click.Path(path_type=Path),
    help="Diretório de saída (padrão: env OUTPUT_DIR ou ./output)",
)
@click.option(
    "--skip-analysis",
    is_flag=True,
    default=False,
    help="Executar apenas extração (sem análise de risco).",
)
@click.option(
    "--log-level",
    default=None,
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
    help="Nível de log (padrão: env LOG_LEVEL ou INFO).",
)
@click.option(
    "--no-raw-text",
    is_flag=True,
    default=False,
    help="Não salvar o texto bruto extraído.",
)
def analyze(
    pdf_path: Path,
    output_dir: Path | None,
    skip_analysis: bool,
    log_level: str | None,
    no_raw_text: bool,
):
    """Analisar um contrato de construção civil em PDF.

    PDF_PATH: Caminho para o arquivo PDF do contrato.

    Exemplo:
        python main.py analyze contrato.pdf --output-dir resultados/
    """
    # Resolve settings
    resolved_log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    resolved_output_dir = output_dir or Path(os.getenv("OUTPUT_DIR", "output"))
    save_raw_text = not no_raw_text and os.getenv("SAVE_RAW_TEXT", "true").lower() == "true"

    # Setup file logging
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file = resolved_output_dir / pdf_path.stem / f"pipeline_{run_id}.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    setup_logging(log_level=resolved_log_level, log_file=log_file)

    logger.info(f"extrator-infralize — Iniciando análise de: {pdf_path.name}")
    logger.info(f"Saída em: {resolved_output_dir / pdf_path.stem}")

    # Verify API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        logger.error(
            "ANTHROPIC_API_KEY não configurada. "
            "Copie .env.example para .env e preencha a chave."
        )
        sys.exit(1)

    try:
        output_paths = run_pipeline(
            pdf_path=pdf_path,
            output_dir=resolved_output_dir,
            skip_analysis=skip_analysis,
            save_raw_text=save_raw_text,
        )
        output_paths["log"] = log_file
        print_summary(output_paths)

    except FileNotFoundError as exc:
        logger.error(f"Arquivo não encontrado: {exc}")
        sys.exit(1)
    except (ExtractorError, ParsingError, AnalysisError) as exc:
        logger.error(f"Erro na pipeline: {exc}")
        sys.exit(1)
    except Exception as exc:
        logger.exception(f"Erro inesperado: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
