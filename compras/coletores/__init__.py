"""Robôs que buscam preços nas lojas.

Lojas de busca têm um Cliente com buscar(termo, pagina, nome) -> (produtos, total de páginas);
`nome` é o nome do item no catálogo, para lojas que o usam como dica (Mercado Livre).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProdutoColetado:
    sku: str
    descricao: str
    preco: float                       # preço que se paga hoje (já com promoção da loja)
    marca: str | None = None
    preco_regular: float | None = None  # preço "de", quando em promoção
    promocao: dict | None = None
    url: str | None = None
    imagem: str | None = None
