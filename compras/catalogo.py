"""Catálogo de itens genéricos e o reconhecimento de produtos das lojas."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from compras import unidades
from compras.texto import normalizar

ARQUIVO = Path(__file__).resolve().parents[1] / "catalogo.toml"


@dataclass(frozen=True)
class ItemCatalogo:
    id: str
    nome: str
    categoria: str
    unidade: str
    busca: str
    incluir: list[str] = field(default_factory=list)
    excluir: list[str] = field(default_factory=list)
    comeca: list[str] = field(default_factory=list)  # o nome precisa começar por um destes
    padrao: float | None = None  # quantidade assumida quando o nome não diz (ex.: escova = 1 un)

    def reconhece(self, descricao: str, marca: str | None = None) -> unidades.Quantidade | None:
        """Quantidade do produto se a descrição for deste item, senão None."""
        texto = normalizar(descricao)
        if self.comeca and not any(_comeca(_sem_marca(texto, marca), c) for c in self.comeca):
            return None
        if not all(any(_tem(texto, alt) for alt in termo.split("|")) for termo in self.incluir):
            return None
        if any(_tem(texto, termo) for termo in (*self.excluir, *EXCLUIR_SEMPRE)):
            return None
        q = unidades.extrair(descricao, preferir=self.unidade)
        if q is not None and q.unidade == self.unidade:
            return q
        if self.padrao and not _RE_MULTIPACK.search(texto):
            return unidades.Quantidade(self.padrao, self.unidade)
        return None


_RE_MULTIPACK = re.compile(r"\d+\s*x\s*\d+|\b(kit|pack|leve|pague|embalagem economica|refil)\b")


# Nunca são o item genérico: combos, kits e porções vendidas por peso aproximado.
EXCLUIR_SEMPRE = ("kit", "combo", "aprox", "racao", "caes", "gatos")


def _tem(texto: str, termo: str) -> bool:
    return re.search(rf"\b{re.escape(normalizar(termo))}\b", texto) is not None


def _comeca(texto: str, prefixo: str) -> bool:
    return re.match(rf"{re.escape(normalizar(prefixo))}\b", texto) is not None


def _sem_marca(texto: str, marca: str | None) -> str:
    """'qualita ketchup tradicional' -> 'ketchup tradicional' (alguns nomes começam pela marca)."""
    for m in filter(None, (normalizar(marca or ""), "qualita")):
        if texto.startswith(m + " "):
            return texto[len(m) + 1 :]
    return texto


def carregar(caminho: Path = ARQUIVO) -> list[ItemCatalogo]:
    with open(caminho, "rb") as f:
        dados = tomllib.load(f)
    itens = [ItemCatalogo(**d) for d in dados["item"]]
    ids = [i.id for i in itens]
    repetidos = {i for i in ids if ids.count(i) > 1}
    if repetidos:
        raise ValueError(f"ids repetidos no catálogo: {repetidos}")
    return itens
