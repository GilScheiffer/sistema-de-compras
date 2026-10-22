from datetime import date, timedelta
from pathlib import Path

import pytest

from compras import comparador, db, regras
from compras.config import Config, Loja


@pytest.fixture
def cfg():
    lojas = {
        "guanabara": Loja("guanabara", "Guanabara", "fisica"),
        "pao": Loja(
            "pao",
            "Pão de Açúcar",
            "fisica",
            regras=[{"tipo": "desconto_marca", "marca": "Qualitá", "percentual": 20, "condicao": "cartao"}],
        ),
        "ml": Loja("ml", "Mercado Livre", "online", frete=20.0, frete_gratis_acima=79.0),
    }
    return Config(lojas=lojas, perfil={"cartao": True}, banco=Path(":memory:"))


@pytest.fixture
def conn():
    return db.conectar(":memory:")


def _preco(conn, item_id, loja, descricao, qtd, preco, marca=None, dias_atras=0):
    pid = db.salvar_produto(conn, item_id, loja, descricao, qtd, marca)
    db.registrar_preco(conn, pid, preco, date.today() - timedelta(days=dias_atras))


def test_desconto_qualita_so_com_cartao():
    r = [{"tipo": "desconto_marca", "marca": "Qualitá", "percentual": 20, "condicao": "cartao"}]
    assert regras.aplicar(10.0, None, "Arroz QUALITA 5kg", r, {"cartao": True}) == (8.0, ["-20% Qualitá"])
    assert regras.aplicar(10.0, None, "Arroz QUALITA 5kg", r, {"cartao": False}) == (10.0, [])
    assert regras.aplicar(10.0, None, "Arroz Qualitativo 5kg", r, {"cartao": True}) == (10.0, [])


def test_escolhe_combinacao_de_pacotes_mais_barata(cfg, conn):
    arroz = db.criar_item(conn, "Arroz", "kg")
    _preco(conn, arroz, "guanabara", "Arroz 1kg", 1, 6.00)
    _preco(conn, arroz, "guanabara", "Arroz 5kg", 5, 27.00)
    item = db.buscar_item(conn, "arroz")
    oferta = comparador.melhor_oferta(conn, item, 5, cfg.lojas["guanabara"], cfg.perfil)
    assert oferta.produto["descricao"] == "Arroz 5kg"
    assert oferta.custo == 27.00


def test_plano_divide_entre_lojas_e_considera_frete(cfg, conn):
    arroz = db.criar_item(conn, "Arroz", "kg")
    sabao = db.criar_item(conn, "Sabão em pó", "kg")
    _preco(conn, arroz, "guanabara", "Arroz Tio João 5kg", 5, 28.00)
    _preco(conn, arroz, "pao", "Arroz Qualitá 5kg", 5, 30.00)  # 24,00 com cartão
    _preco(conn, sabao, "guanabara", "Omo 1,6kg", 1.6, 35.00)
    _preco(conn, sabao, "pao", "Omo 1,6kg", 1.6, 38.00)
    _preco(conn, sabao, "ml", "Omo 1,6kg", 1.6, 25.00)  # mais barato, mas paga frete de 20
    db.lista_definir(conn, arroz, 5)
    db.lista_definir(conn, sabao, 1.6)

    itens = db.lista_itens(conn)
    planos = comparador.planejar(itens, comparador.ofertas_da_lista(conn, cfg), cfg, max_lojas=2)

    melhor = planos[0]
    assert melhor.nome == "Guanabara + Pão de Açúcar"
    assert melhor.total == pytest.approx(24.00 + 35.00)
    ml = next(p for p in planos if p.nome == "Pão de Açúcar + Mercado Livre")
    assert ml.total == pytest.approx(24.00 + 25.00 + 20.00)


def test_variacao_contra_historico(cfg, conn):
    cafe = db.criar_item(conn, "Café", "kg")
    for dias, preco in [(60, 20.0), (30, 20.0), (0, 15.0)]:
        _preco(conn, cafe, "guanabara", "Café Pilão 500g", 0.5, preco, dias_atras=dias)
    oferta = comparador.melhor_oferta(conn, db.buscar_item(conn, "café"), None, cfg.lojas["guanabara"], cfg.perfil)
    assert oferta.variacao == pytest.approx(-0.25)
