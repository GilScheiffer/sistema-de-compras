"""Interface de linha de comando: `compras --help`."""

from __future__ import annotations

from datetime import date
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from compras import ErroCompras, comparador, config, db, unidades
from compras.texto import brl, ler_dinheiro

app = typer.Typer(help="Comparador de preços de mercado da casa.", no_args_is_help=True)
item_app = typer.Typer(help="Itens que a casa compra (arroz, detergente...).", no_args_is_help=True)
preco_app = typer.Typer(help="Registrar e consultar preços.", no_args_is_help=True)
lista_app = typer.Typer(help="Lista de compras atual.", no_args_is_help=True)
app.add_typer(item_app, name="item")
app.add_typer(preco_app, name="preco")
app.add_typer(lista_app, name="lista")

console = Console()


def _abrir():
    cfg = config.carregar()
    return cfg, db.conectar(cfg.banco)


def _pct(v: float) -> str:
    return f"{v * 100:+.0f}%"


# --- lojas ---------------------------------------------------------------

@app.command()
def lojas():
    """Mostra as lojas configuradas e suas regras."""
    cfg = config.carregar()
    t = Table("id", "Loja", "Tipo", "Custo fixo", "Regras")
    for loja in cfg.lojas.values():
        if loja.tipo == "fisica":
            custo = f"ida: {brl(loja.custo_visita)}"
        elif loja.frete_isento_se and cfg.perfil.get(loja.frete_isento_se):
            custo = f"frete grátis ({loja.frete_isento_se})"
        else:
            custo = f"frete {brl(loja.frete)}"
            if loja.frete_gratis_acima is not None:
                custo += f", grátis acima de {brl(loja.frete_gratis_acima)}"
        descr = []
        for r in loja.regras:
            ativa = not r.get("condicao") or cfg.perfil.get(r["condicao"])
            txt = f"-{r['percentual']}% {r['marca']}" + (f" (se {r['condicao']})" if r.get("condicao") else "")
            descr.append(txt if ativa else f"[dim]{txt} [inativa][/dim]")
        t.add_row(loja.id, loja.nome, loja.tipo, custo, "\n".join(descr))
    console.print(t)


# --- itens ---------------------------------------------------------------

@item_app.command("add")
def item_add(
    nome: str,
    unidade: Annotated[str, typer.Option("--unidade", "-u", help="kg, L ou un")],
    categoria: Annotated[str | None, typer.Option("--categoria", "-c")] = None,
):
    """Cadastra um item. Ex.: compras item add Arroz -u kg -c mercearia"""
    _, conn = _abrir()
    db.criar_item(conn, nome, unidades.unidade_base(unidade), categoria)
    console.print(f"[green]Item {nome!r} cadastrado.[/green]")


@item_app.command("list")
def item_list():
    """Lista os itens cadastrados."""
    _, conn = _abrir()
    t = Table("Item", "Unidade", "Categoria", "Produtos")
    for item in db.listar_itens(conn):
        produtos = db.produtos_do_item(conn, item["id"])
        t.add_row(item["nome"], item["unidade"], item["categoria"] or "", str(len(produtos)))
    console.print(t)


@item_app.command("rm")
def item_rm(nome: str):
    """Remove um item (e seus produtos e preços)."""
    _, conn = _abrir()
    item = db.buscar_item(conn, nome)
    db.remover_item(conn, item["id"])
    console.print(f"Item {item['nome']!r} removido.")


# --- preços --------------------------------------------------------------

@preco_app.command("add")
def preco_add(
    loja: str,
    item: str,
    descricao: Annotated[str, typer.Argument(help='Como aparece na loja, ex.: "Arroz Tio João 5kg"')],
    preco: str,
    qtd: Annotated[str | None, typer.Option(help="Tamanho da embalagem, se não estiver na descrição")] = None,
    marca: Annotated[str | None, typer.Option()] = None,
    promo: Annotated[bool, typer.Option("--promo", help="Preço promocional")] = False,
    data: Annotated[str | None, typer.Option(help="AAAA-MM-DD (padrão: hoje)")] = None,
    url: Annotated[str | None, typer.Option()] = None,
):
    """Registra um preço visto. Ex.: compras preco add guanabara arroz "Arroz Tio João 5kg" 27,90"""
    cfg, conn = _abrir()
    loja_cfg = cfg.loja(loja)
    item_row = db.buscar_item(conn, item)

    q = unidades.ler(qtd, item_row["unidade"]) if qtd else unidades.extrair(descricao)
    if q is None:
        raise ErroCompras("Não achei o tamanho na descrição. Informe com --qtd (ex.: --qtd 5kg).")
    if q.unidade != item_row["unidade"]:
        raise ErroCompras(f"{item_row['nome']} é medido em {item_row['unidade']}, mas o produto está em {q.unidade}.")

    valor = ler_dinheiro(preco)
    dia = date.fromisoformat(data) if data else None
    produto_id = db.salvar_produto(conn, item_row["id"], loja_cfg.id, descricao, q.valor, marca, url)
    db.registrar_preco(conn, produto_id, valor, dia, promo)

    efetivo, ajustes = comparador.regras.aplicar(valor, marca, descricao, loja_cfg.regras, cfg.perfil)
    extra = f" -> {brl(efetivo)} ({', '.join(ajustes)})" if ajustes else ""
    console.print(
        f"[green]OK[/green] {loja_cfg.nome}: {descricao} = {brl(valor)}{extra} "
        f"[dim]({brl(efetivo / q.valor)}/{item_row['unidade']})[/dim]"
    )


@preco_app.command("historico")
def preco_historico(item: str):
    """Histórico de preços de um item em todas as lojas."""
    cfg, conn = _abrir()
    item_row = db.buscar_item(conn, item)
    t = Table("Data", "Loja", "Produto", "Preço", f"R$/{item_row['unidade']}", "Fonte", title=item_row["nome"])
    linhas = []
    for produto in db.produtos_do_item(conn, item_row["id"]):
        loja = cfg.lojas.get(produto["loja_id"])
        for h in db.historico(conn, produto["id"]):
            linhas.append((h["data"], loja.nome if loja else produto["loja_id"], produto, h))
    for data_, nome_loja, produto, h in sorted(linhas, key=lambda x: x[0], reverse=True):
        preco_txt = brl(h["preco"]) + (" [yellow]promo[/yellow]" if h["promocao"] else "")
        t.add_row(data_, nome_loja, produto["descricao"], preco_txt, brl(h["preco"] / produto["quantidade"]), h["fonte"])
    console.print(t)


# --- lista ---------------------------------------------------------------

@lista_app.command("add")
def lista_add(
    item: str,
    quantidade: Annotated[str | None, typer.Argument(help="Ex.: 5kg, 2L, 12 (na unidade do item)")] = None,
):
    """Coloca um item na lista. Sem quantidade = uma embalagem de melhor custo-benefício."""
    _, conn = _abrir()
    item_row = db.buscar_item(conn, item)
    valor = None
    if quantidade:
        q = unidades.ler(quantidade, item_row["unidade"])
        if q.unidade != item_row["unidade"]:
            raise ErroCompras(f"{item_row['nome']} é medido em {item_row['unidade']}.")
        valor = q.valor
    db.lista_definir(conn, item_row["id"], valor)
    console.print(f"[green]{item_row['nome']} na lista[/green]" + (f": {unidades.formatar(valor, item_row['unidade'])}" if valor else ""))


@lista_app.command("rm")
def lista_rm(item: str):
    """Tira um item da lista."""
    _, conn = _abrir()
    db.lista_remover(conn, db.buscar_item(conn, item)["id"])


@lista_app.command("limpar")
def lista_limpar():
    """Esvazia a lista."""
    _, conn = _abrir()
    db.lista_limpar(conn)
    console.print("Lista vazia.")


@lista_app.command("show")
def lista_show():
    """Mostra a lista atual."""
    _, conn = _abrir()
    t = Table("Item", "Quantidade", "Categoria")
    for item in db.lista_itens(conn):
        qtd = unidades.formatar(item["necessidade"], item["unidade"]) if item["necessidade"] else "1 embalagem"
        t.add_row(item["nome"], qtd, item["categoria"] or "")
    console.print(t)


# --- comparar ------------------------------------------------------------

@app.command()
def comparar(
    max_lojas: Annotated[int, typer.Option("--max-lojas", "-n", help="Máximo de lojas no plano")] = 2,
    planos: Annotated[int, typer.Option("--planos", "-p", help="Quantos planos mostrar")] = 3,
):
    """Compara a lista de compras entre as lojas e sugere onde comprar."""
    cfg, conn = _abrir()
    itens = db.lista_itens(conn)
    if not itens:
        raise ErroCompras("Lista vazia. Use: compras lista add <item> [quantidade]")
    ofertas = comparador.ofertas_da_lista(conn, cfg)
    lojas_com_preco = [l for l in cfg.lojas.values() if any(l.id in o for o in ofertas.values())]
    if not lojas_com_preco:
        raise ErroCompras("Nenhum preço registrado para os itens da lista. Use: compras preco add ...")

    t = Table("Item", "Precisa", *[l.nome for l in lojas_com_preco], title="Preços por loja", show_lines=True)
    for item in itens:
        por_loja = ofertas[item["id"]]
        mais_barata = min(por_loja.values(), key=lambda o: o.custo).loja.id if por_loja else None
        qtd = unidades.formatar(item["necessidade"], item["unidade"]) if item["necessidade"] else "1 emb."
        celulas = []
        for loja in lojas_com_preco:
            oferta = por_loja.get(loja.id)
            celulas.append(_celula_item(oferta, loja.id == mais_barata, item["unidade"]))
        t.add_row(item["nome"], qtd, *celulas)
    console.print(t)

    resultado = comparador.planejar(itens, ofertas, cfg, max_lojas)
    referencia = next((p for p in resultado if len(p.lojas) == 1 and not p.faltando), None)
    console.print()
    for i, plano in enumerate(resultado[:planos], 1):
        cab = f"[bold]{i}. {plano.nome}: {brl(plano.total)}[/bold]"
        if referencia and plano is not referencia and not plano.faltando:
            dif = referencia.total - plano.total
            if dif > 0:
                cab += f" [green](economiza {brl(dif)} vs só {referencia.nome})[/green]"
        console.print(cab)
        for loja in plano.lojas:
            itens_loja = [o for o in plano.alocacao.values() if o.loja.id == loja.id]
            nomes = ", ".join(_nome_item(itens, o) for o in itens_loja)
            fixo = plano.custos_fixos[loja.id]
            fixo_txt = f" + {'frete' if loja.tipo == 'online' else 'ida'} {brl(fixo)}" if fixo else ""
            console.print(f"   {loja.nome}: {brl(plano.subtotais[loja.id])}{fixo_txt} — {nomes}")
        if plano.faltando:
            console.print(f"   [red]sem preço: {', '.join(i['nome'] for i in plano.faltando)}[/red]")
    console.print("\n[dim]verde = mais barato · ciano = desconto da loja aplicado · promo = marcado como promoção · % vs média = comparado ao histórico (120 dias)[/dim]")


def _celula_item(oferta, melhor: bool, unidade: str) -> str:
    if oferta is None:
        return "[dim]—[/dim]"
    texto = brl(oferta.custo)
    if oferta.pacotes > 1:
        texto += f" ({oferta.pacotes}x)"
    if melhor:
        texto = f"[bold green]{texto}[/bold green]"
    texto += f"\n[dim]{oferta.produto['descricao']}\n{brl(oferta.preco_unitario)}/{unidade}[/dim]"
    marcas = []
    if oferta.ajustes:
        marcas.append(f"[cyan]{', '.join(oferta.ajustes)}[/cyan]")
    if oferta.promocao:
        marcas.append("[yellow]promo[/yellow]")
    if oferta.variacao is not None and abs(oferta.variacao) >= 0.05:
        cor = "green" if oferta.variacao < 0 else "red"
        marcas.append(f"[{cor}]{_pct(oferta.variacao)} vs média[/{cor}]")
    if oferta.idade_dias > 30:
        marcas.append(f"[dim]visto há {oferta.idade_dias}d[/dim]")
    if marcas:
        texto += "\n" + " ".join(marcas)
    return texto


def _nome_item(itens, oferta) -> str:
    return next(i["nome"] for i in itens if i["id"] == oferta.produto["item_id"])


def main():
    try:
        app()
    except ErroCompras as e:
        console.print(f"[red]{e}[/red]")
        raise SystemExit(1)
