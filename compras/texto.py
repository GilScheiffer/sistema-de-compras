"""Utilitários de texto e formatação."""

from __future__ import annotations

import unicodedata

from compras import ErroCompras


def normalizar(texto: str) -> str:
    """Minúsculas, sem acentos, hífen vira espaço: 'Lava-Louças  Qualitá' -> 'lava loucas qualita'."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(sem_acento.lower().replace("-", " ").split())


def ler_dinheiro(texto: str) -> float:
    """Aceita '27,90', '27.90', 'R$ 1.234,56'."""
    limpo = texto.replace("R$", "").replace(" ", "").strip()
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    try:
        valor = float(limpo)
    except ValueError:
        raise ErroCompras(f"Preço inválido: {texto!r}") from None
    if valor <= 0:
        raise ErroCompras(f"Preço precisa ser positivo: {texto!r}")
    return valor


def brl(valor: float) -> str:
    """27.9 -> 'R$ 27,90'."""
    return "R$ " + f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
