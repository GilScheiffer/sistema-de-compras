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

    def reconhece(
        self, descricao: str, marca: str | None = None, marcas: "Marcas | None" = None
    ) -> unidades.Quantidade | None:
        """Quantidade do produto se a descrição for deste item, senão None.

        `marcas` permite reconhecer nomes que começam pela marca ("Tio João Arroz Branco 5kg").
        """
        texto = normalizar(descricao)
        inicio = _sem_marca(texto, marca)
        if marcas:
            inicio = marcas.sem_prefixo(inicio)
        if self.comeca and not any(_comeca(inicio, c) for c in self.comeca):
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


class Marcas:
    """Marcas conhecidas (vindas das lojas que informam a marca), para lojas que não informam."""

    def __init__(self, nomes):
        unicas = {normalizar(n): n for n in nomes if n and len(normalizar(n)) >= 2}
        self._ordem = sorted(unicas, key=len, reverse=True)  # "tio joao" antes de "tio"
        self._original = unicas
        self._re = re.compile(r"\b(" + "|".join(re.escape(m) for m in self._ordem) + r")\b") if unicas else None

    def sem_prefixo(self, texto: str) -> str:
        """Tira uma marca do início: 'tio joao arroz branco' -> 'arroz branco'."""
        for m in self._ordem:
            if texto.startswith(m + " "):
                return texto[len(m) + 1 :]
        return texto

    def encontrar(self, descricao: str) -> str | None:
        """Primeira marca conhecida que aparece no nome (a mais longa, se houver empate de posição)."""
        if not self._re:
            return None
        achadas = list(self._re.finditer(normalizar(descricao)))
        if not achadas:
            return None
        primeira = min(achadas, key=lambda m: (m.start(), -len(m.group(1))))
        return self._original[primeira.group(1)]


def carregar(caminho: Path = ARQUIVO) -> list[ItemCatalogo]:
    with open(caminho, "rb") as f:
        dados = tomllib.load(f)
    itens = [ItemCatalogo(**d) for d in dados["item"]]
    ids = [i.id for i in itens]
    repetidos = {i for i in ids if ids.count(i) > 1}
    if repetidos:
        raise ValueError(f"ids repetidos no catálogo: {repetidos}")
    return itens
