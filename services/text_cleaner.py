import re
from collections import Counter


def clean(text: str) -> str:
    text = _remove_repeated_lines(text)
    text = _fix_hyphenation(text)
    text = _remove_artifacts(text)
    text = _normalize_whitespace(text)
    return text.strip()


def _remove_repeated_lines(text: str, min_repeats: int = 3) -> str:
    """Remove linhas que aparecem muitas vezes (cabeçalhos/rodapés)."""
    lines = text.splitlines()
    counts = Counter(line.strip() for line in lines if line.strip())
    repeated = {line for line, n in counts.items() if n >= min_repeats}
    return "\n".join(line for line in lines if line.strip() not in repeated)


def _fix_hyphenation(text: str) -> str:
    """Junta palavras quebradas por hifenização de OCR: 'pala-\nvra' → 'palavra'."""
    return re.sub(r"-\n(\w)", lambda m: m.group(1), text)


def _remove_artifacts(text: str) -> str:
    """Remove sequências de caracteres que não carregam informação."""
    text = re.sub(r"[|]{2,}", "", text)
    text = re.sub(r"[_\-]{4,}", "", text)
    text = re.sub(r"\.{4,}", "...", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text


def _normalize_whitespace(text: str) -> str:
    """Colapsa 3+ quebras de linha em 2."""
    return re.sub(r"\n{3,}", "\n\n", text)
