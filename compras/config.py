"""Carrega config.toml: lojas, regras de preço e perfil do casal."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from compras import ErroCompras

TIPOS_LOJA = ("fisica", "online")


@dataclass
class Loja:
    id: str
    nome: str
    tipo: str
    custo_visita: float = 0.0
    frete: float = 0.0
    frete_gratis_acima: float | None = None
    frete_isento_se: str | None = None
    regras: list[dict] = field(default_factory=list)

    def custo_fixo(self, subtotal: float, perfil: dict) -> float:
        """Quanto custa usar a loja além dos produtos: ida até lá (física) ou frete (online)."""
        if self.tipo == "fisica":
            return self.custo_visita
        if self.frete_isento_se and perfil.get(self.frete_isento_se):
            return 0.0
        if self.frete_gratis_acima is not None and subtotal >= self.frete_gratis_acima:
            return 0.0
        return self.frete


@dataclass
class Config:
    lojas: dict[str, Loja]
    perfil: dict
    banco: Path

    def loja(self, loja_id: str) -> Loja:
        if loja_id not in self.lojas:
            raise ErroCompras(f"Loja {loja_id!r} não existe. Opções: {', '.join(self.lojas)}")
        return self.lojas[loja_id]


def localizar() -> Path:
    """COMPRAS_CONFIG, senão config.toml no diretório atual."""
    caminho = Path(os.environ.get("COMPRAS_CONFIG", "config.toml"))
    if not caminho.is_file():
        raise ErroCompras(f"Não achei {caminho}. Rode o comando na pasta do projeto ou defina COMPRAS_CONFIG.")
    return caminho


def carregar(caminho: Path | None = None) -> Config:
    caminho = caminho or localizar()
    with open(caminho, "rb") as f:
        dados = tomllib.load(f)

    lojas = {}
    for loja_id, d in dados.get("lojas", {}).items():
        if d.get("tipo") not in TIPOS_LOJA:
            raise ErroCompras(f"Loja {loja_id!r}: tipo deve ser 'fisica' ou 'online'")
        lojas[loja_id] = Loja(
            id=loja_id,
            nome=d.get("nome", loja_id),
            tipo=d["tipo"],
            custo_visita=float(d.get("custo_visita", 0.0)),
            frete=float(d.get("frete", 0.0)),
            frete_gratis_acima=d.get("frete_gratis_acima"),
            frete_isento_se=d.get("frete_isento_se"),
            regras=d.get("regras", []),
        )

    banco = caminho.parent / dados.get("geral", {}).get("banco", "dados/compras.db")
    return Config(lojas=lojas, perfil=dados.get("perfil", {}), banco=banco)
