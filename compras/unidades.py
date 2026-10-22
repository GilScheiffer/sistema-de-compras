"""Leitura e normalização de quantidades: '5kg', '900 ml', '12 rolos', '6x350ml', 'lata 350ml c/12'.

Tudo é convertido para uma de três unidades base: kg, L ou un.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from compras import ErroCompras

BASES = ("kg", "L", "un")

# unidade escrita -> (unidade base, fator de conversão)
_UNIDADES = {
    "mg": ("kg", 1e-6),
    "g": ("kg", 1e-3),
    "gr": ("kg", 1e-3),
    "grs": ("kg", 1e-3),
    "kg": ("kg", 1.0),
    "kilo": ("kg", 1.0),
    "kilos": ("kg", 1.0),
    "ml": ("L", 1e-3),
    "l": ("L", 1.0),
    "lt": ("L", 1.0),
    "lts": ("L", 1.0),
    "litro": ("L", 1.0),
    "litros": ("L", 1.0),
    "un": ("un", 1.0),
    "und": ("un", 1.0),
    "unid": ("un", 1.0),
    "unidade": ("un", 1.0),
    "unidades": ("un", 1.0),
    "rolo": ("un", 1.0),
    "rolos": ("un", 1.0),
    "folhas": ("un", 1.0),
    "sachês": ("un", 1.0),
    "saches": ("un", 1.0),
    "cápsulas": ("un", 1.0),
    "capsulas": ("un", 1.0),
}

_NUM = r"\d+(?:[.,]\d+)?"
_NOMES = "|".join(re.escape(u) for u in sorted(_UNIDADES, key=len, reverse=True))
_RE_QTD = re.compile(rf"(?:(\d+)\s*x\s*)?({_NUM})\s*({_NOMES})(?![a-zà-ú])", re.IGNORECASE)
_RE_PACK = re.compile(r"(?:c/|com|pack|kit|leve)\s*(\d+)(?!\s*[.,]?\d)", re.IGNORECASE)


@dataclass(frozen=True)
class Quantidade:
    valor: float
    unidade: str  # sempre uma de BASES


def _num(texto: str) -> float:
    return float(texto.replace(",", "."))


def unidade_base(nome: str) -> str:
    """'g' -> 'kg', 'litros' -> 'L'. Aceita também as próprias bases."""
    chave = nome.strip().lower()
    if chave in _UNIDADES:
        return _UNIDADES[chave][0]
    raise ErroCompras(f"Unidade desconhecida: {nome!r} (use kg, g, L, ml ou un)")


def extrair(texto: str) -> Quantidade | None:
    """Encontra a quantidade dentro de uma descrição de produto. None se não achar."""
    m = _RE_QTD.search(texto)
    if not m:
        return None
    multiplicador, numero, nome = m.groups()
    base, fator = _UNIDADES[nome.lower()]
    valor = _num(numero) * fator
    if multiplicador:
        valor *= int(multiplicador)
    elif base != "un":
        # "lata 350ml c/12" -> 12 x 350ml
        for pack in _RE_PACK.finditer(texto):
            if pack.start() >= m.end() or pack.end() <= m.start():
                valor *= int(pack.group(1))
                break
    return Quantidade(round(valor, 9), base)


def ler(texto: str, unidade_padrao: str | None = None) -> Quantidade:
    """Lê uma quantidade digitada. Número puro ('2') usa a unidade_padrao."""
    limpo = texto.strip()
    if unidade_padrao and re.fullmatch(_NUM, limpo):
        return Quantidade(_num(limpo), unidade_padrao)
    q = extrair(limpo)
    if q is None:
        raise ErroCompras(f"Não entendi a quantidade {texto!r} (ex.: 5kg, 900ml, 12un)")
    return q


def formatar(q: Quantidade | float, unidade: str | None = None) -> str:
    """Quantidade(0.5, 'kg') -> '500 g'; Quantidade(2, 'L') -> '2 L'."""
    if not isinstance(q, Quantidade):
        q = Quantidade(q, unidade or "un")
    v, u = q.valor, q.unidade
    if u == "kg" and v < 1:
        v, u = v * 1000, "g"
    elif u == "L" and v < 1:
        v, u = v * 1000, "ml"
    texto = f"{v:.3f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{texto} {u}"
