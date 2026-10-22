"""Robô de coleta: busca os itens do catálogo numa loja e grava no Supabase.

Uso:
    python -m compras.coletar pao_de_acucar             # coleta e grava
    python -m compras.coletar pao_de_acucar --teste     # só mostra o que encontraria
    python -m compras.coletar pao_de_acucar --item cafe-po --teste
"""

from __future__ import annotations

import argparse
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone

from compras import catalogo
from compras.coletores import ProdutoColetado
from compras.coletores import pao_de_acucar
from compras.supabase import Supabase

PAGINAS_POR_ITEM = 4
LOJAS = {"pao_de_acucar": pao_de_acucar}


@dataclass
class Encontrado:
    item: catalogo.ItemCatalogo
    quantidade: float
    produto: ProdutoColetado


def log(msg: str) -> None:
    print(msg, flush=True)


def buscar_tudo(modulo, itens: list[catalogo.ItemCatalogo]) -> tuple[dict[str, Encontrado], list[str]]:
    """sku -> produto reconhecido; e a lista de itens cuja busca falhou."""
    cliente = modulo.Cliente()
    encontrados: dict[str, Encontrado] = {}
    falhas = []
    for item in itens:
        try:
            antes = len(encontrados)
            pagina, total = 1, 1
            while pagina <= min(total, PAGINAS_POR_ITEM):
                produtos, total = cliente.buscar(item.busca, pagina)
                for p in produtos:
                    if p.sku in encontrados:
                        continue  # já reconhecido pela busca de outro item
                    q = item.reconhece(p.descricao, p.marca)
                    if q:
                        encontrados[p.sku] = Encontrado(item, q.valor, p)
                pagina += 1
            log(f"  {item.id}: {len(encontrados) - antes} produtos")
        except Exception as e:  # uma busca ruim não derruba a coleta inteira
            falhas.append(item.id)
            log(f"  {item.id}: ERRO {e}")
    return encontrados, falhas


def sincronizar_catalogo(db: Supabase, itens: list[catalogo.ItemCatalogo]) -> None:
    db.upsert(
        "catalogo",
        [
            {
                "id": i.id,
                "nome": i.nome,
                "categoria": i.categoria,
                "unidade": i.unidade,
                "busca": i.busca,
                "incluir": i.incluir,
                "excluir": i.excluir,
                "ativo": True,
            }
            for i in itens
        ],
        conflito="id",
    )
    ids = {i.id for i in itens}
    for antigo in db.select("catalogo", ativo="eq.true"):
        if antigo["id"] not in ids:
            db.update("catalogo", {"ativo": False}, id=f"eq.{antigo['id']}")


def gravar(db: Supabase, loja_id: str, encontrados: dict[str, Encontrado]) -> int:
    """Atualiza produtos e registra no histórico os preços que mudaram. Devolve nº de mudanças."""
    agora = datetime.now(timezone.utc).isoformat()
    anteriores = {p["sku"]: p for p in db.select("produtos", loja_id=f"eq.{loja_id}")}
    linhas = [
        {
            "loja_id": loja_id,
            "sku": sku,
            "catalogo_id": e.item.id,
            "descricao": e.produto.descricao,
            "marca": e.produto.marca,
            "quantidade": e.quantidade,
            "unidade": e.item.unidade,
            "url": e.produto.url,
            "imagem": e.produto.imagem,
            "preco": e.produto.preco,
            "preco_regular": e.produto.preco_regular,
            "promocao": e.produto.promocao,
            "visto_em": agora,
        }
        for sku, e in encontrados.items()
    ]
    gravados = db.upsert("produtos", linhas, conflito="loja_id,sku", retornar="id,sku")
    ids = {g["sku"]: g["id"] for g in gravados}

    historico = []
    for sku, e in encontrados.items():
        antes = anteriores.get(sku)
        mudou = (
            antes is None
            or antes["preco"] is None
            or float(antes["preco"]) != e.produto.preco
            or (float(antes["preco_regular"]) if antes["preco_regular"] else None) != e.produto.preco_regular
        )
        if mudou:
            historico.append(
                {
                    "produto_id": ids[sku],
                    "preco": e.produto.preco,
                    "preco_regular": e.produto.preco_regular,
                    "em_promocao": e.produto.preco_regular is not None,
                    "coletado_em": agora,
                    "fonte": loja_id,
                }
            )
    db.insert("precos", historico)
    return len(historico)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("loja", choices=sorted(LOJAS))
    ap.add_argument("--teste", action="store_true", help="não grava nada, só mostra")
    ap.add_argument("--item", action="append", help="coletar só estes itens do catálogo")
    args = ap.parse_args(argv)

    itens = catalogo.carregar()
    if args.item:
        itens = [i for i in itens if i.id in args.item]

    db = None if args.teste else Supabase()
    coleta_id = None
    if db:
        sincronizar_catalogo(db, catalogo.carregar())
        coleta_id = db.insert("coletas", [{"loja_id": args.loja}], retornar="id")[0]["id"]

    log(f"Coletando {args.loja}: {len(itens)} itens")
    try:
        encontrados, falhas = buscar_tudo(LOJAS[args.loja], itens)
        if len(falhas) > len(itens) / 2:
            raise RuntimeError(f"{len(falhas)} de {len(itens)} buscas falharam: {', '.join(falhas)}")
        if args.teste:
            for e in sorted(encontrados.values(), key=lambda e: (e.item.id, e.produto.preco)):
                promo = f"  (de {e.produto.preco_regular})" if e.produto.preco_regular else ""
                log(f"{e.item.id:22} {e.produto.preco:8.2f}{promo}  {e.produto.descricao}")
            return 0
        mudancas = gravar(db, args.loja, encontrados)
        db.update(
            "coletas",
            {
                "terminada_em": datetime.now(timezone.utc).isoformat(),
                "status": "ok",
                "produtos": len(encontrados),
                "mudancas": mudancas,
                "erro": f"falharam: {', '.join(falhas)}" if falhas else None,
            },
            id=f"eq.{coleta_id}",
        )
        log(f"OK: {len(encontrados)} produtos, {mudancas} preços novos/alterados" + (f", {len(falhas)} falhas" if falhas else ""))
        return 0
    except Exception as e:
        if db and coleta_id:
            db.update(
                "coletas",
                {"terminada_em": datetime.now(timezone.utc).isoformat(), "status": "erro", "erro": str(e)[:2000]},
                id=f"eq.{coleta_id}",
            )
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
