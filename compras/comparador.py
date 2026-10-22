"""Compara preços entre lojas e monta o plano de compra mais barato.

1. Para cada item da lista e cada loja, escolhe o produto que atende a necessidade
   pelo menor custo (já com regras de desconto aplicadas).
2. Testa combinações de lojas (até `max_lojas`), manda cada item para a loja mais
   barata da combinação e soma frete / custo de ida.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, field
from datetime import date, timedelta
from itertools import combinations
from statistics import mean

from compras import db, regras
from compras.config import Config, Loja

JANELA_HISTORICO = timedelta(days=120)


@dataclass
class Oferta:
    loja: Loja
    produto: sqlite3.Row
    preco: float           # preço registrado
    preco_efetivo: float   # após regras da loja
    ajustes: list[str]
    pacotes: int
    custo: float           # pacotes * preco_efetivo
    preco_unitario: float  # preco_efetivo por kg/L/un
    data: date
    promocao: bool
    variacao: float | None  # preço atual vs média histórica (-0.15 = 15% abaixo)

    @property
    def idade_dias(self) -> int:
        return (date.today() - self.data).days


@dataclass
class Plano:
    lojas: tuple[Loja, ...]
    alocacao: dict[int, Oferta] = field(default_factory=dict)  # item_id -> oferta
    faltando: list[sqlite3.Row] = field(default_factory=list)
    subtotais: dict[str, float] = field(default_factory=dict)
    custos_fixos: dict[str, float] = field(default_factory=dict)

    @property
    def total(self) -> float:
        return sum(self.subtotais.values()) + sum(self.custos_fixos.values())

    @property
    def nome(self) -> str:
        return " + ".join(loja.nome for loja in self.lojas)


def _pacotes(necessidade: float | None, tamanho: float) -> int:
    if not necessidade:
        return 1
    return max(1, math.ceil(round(necessidade / tamanho, 6)))


def _variacao(hist: list[sqlite3.Row]) -> float | None:
    atual = hist[-1]
    limite = date.fromisoformat(atual["data"]) - JANELA_HISTORICO
    anteriores = [h["preco"] for h in hist[:-1] if date.fromisoformat(h["data"]) >= limite]
    if len(anteriores) < 2:
        return None
    return atual["preco"] / mean(anteriores) - 1


def melhor_oferta(
    conn: sqlite3.Connection, item: sqlite3.Row, necessidade: float | None, loja: Loja, perfil: dict
) -> Oferta | None:
    melhor = None
    for produto in db.produtos_do_item(conn, item["id"], loja.id):
        hist = db.historico(conn, produto["id"])
        if not hist:
            continue
        atual = hist[-1]
        efetivo, ajustes = regras.aplicar(atual["preco"], produto["marca"], produto["descricao"], loja.regras, perfil)
        pacotes = _pacotes(necessidade, produto["quantidade"])
        oferta = Oferta(
            loja=loja,
            produto=produto,
            preco=atual["preco"],
            preco_efetivo=efetivo,
            ajustes=ajustes,
            pacotes=pacotes,
            custo=round(pacotes * efetivo, 2),
            preco_unitario=efetivo / produto["quantidade"],
            data=date.fromisoformat(atual["data"]),
            promocao=bool(atual["promocao"]),
            variacao=_variacao(hist),
        )
        # Com necessidade definida vale o menor custo total; sem ela, o melhor custo-benefício.
        criterio = (oferta.custo, oferta.preco_unitario) if necessidade else (oferta.preco_unitario, oferta.custo)
        if melhor is None or criterio < melhor[0]:
            melhor = (criterio, oferta)
    return melhor[1] if melhor else None


def ofertas_da_lista(conn: sqlite3.Connection, cfg: Config) -> dict[int, dict[str, Oferta]]:
    """item_id -> {loja_id -> melhor oferta daquela loja}."""
    resultado = {}
    for item in db.lista_itens(conn):
        por_loja = {}
        for loja in cfg.lojas.values():
            oferta = melhor_oferta(conn, item, item["necessidade"], loja, cfg.perfil)
            if oferta:
                por_loja[loja.id] = oferta
        resultado[item["id"]] = por_loja
    return resultado


def planejar(
    itens: list[sqlite3.Row],
    ofertas: dict[int, dict[str, Oferta]],
    cfg: Config,
    max_lojas: int = 2,
) -> list[Plano]:
    """Todas as combinações úteis de até `max_lojas` lojas, da melhor para a pior.

    Ordena primeiro por quantos itens ficam faltando, depois pelo total.
    """
    candidatas = [cfg.lojas[lid] for lid in cfg.lojas if any(lid in o for o in ofertas.values())]
    planos = []
    for k in range(1, min(max_lojas, len(candidatas)) + 1):
        for combo in combinations(candidatas, k):
            plano = Plano(lojas=combo)
            for item in itens:
                disponiveis = [ofertas[item["id"]][l.id] for l in combo if l.id in ofertas[item["id"]]]
                if not disponiveis:
                    plano.faltando.append(item)
                    continue
                escolhida = min(disponiveis, key=lambda o: o.custo)
                plano.alocacao[item["id"]] = escolhida
                plano.subtotais[escolhida.loja.id] = plano.subtotais.get(escolhida.loja.id, 0.0) + escolhida.custo
            if len(plano.subtotais) < len(combo):
                continue  # alguma loja ficou sem item: uma combinação menor já cobre esse caso
            for loja in combo:
                plano.custos_fixos[loja.id] = loja.custo_fixo(plano.subtotais[loja.id], cfg.perfil)
            planos.append(plano)
    planos.sort(key=lambda p: (len(p.faltando), round(p.total, 2), len(p.lojas)))
    return planos
