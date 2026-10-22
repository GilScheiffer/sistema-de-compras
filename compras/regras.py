"""Regras de preço por loja (ex.: 20% de desconto em Qualitá com o cartão Pão de Açúcar)."""

from __future__ import annotations

from compras import ErroCompras
from compras.texto import normalizar


def _bate_marca(regra: dict, marca: str | None, descricao: str) -> bool:
    alvo = normalizar(regra["marca"])
    texto = normalizar((marca or "") + " " + descricao)
    return f" {alvo} " in f" {texto} "


def aplicar(preco: float, marca: str | None, descricao: str, regras: list[dict], perfil: dict) -> tuple[float, list[str]]:
    """Devolve o preço efetivo e a lista de ajustes aplicados (para mostrar ao usuário)."""
    ajustes = []
    for regra in regras:
        condicao = regra.get("condicao")
        if condicao and not perfil.get(condicao):
            continue
        tipo = regra.get("tipo")
        if tipo == "desconto_marca":
            if _bate_marca(regra, marca, descricao):
                pct = float(regra["percentual"])
                preco *= 1 - pct / 100
                ajustes.append(f"-{pct:g}% {regra['marca']}")
        else:
            raise ErroCompras(f"Tipo de regra desconhecido: {tipo!r}")
    return round(preco, 2), ajustes
