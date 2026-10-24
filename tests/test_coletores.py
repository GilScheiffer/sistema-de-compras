from datetime import date

from compras.coletores import guanabara, mercado_livre


def test_guanabara_descricao_e_promocao():
    p = guanabara.converter(
        {"nome": "Arroz Branco Tipo 1 Tio João", "marca": "Tio João", "quantidade": 5, "unidade": "kg",
         "preco": 27.95, "por": "embalagem", "leve": None, "pague": None, "obs": ""},
        date(2026, 10, 23),
    )
    assert p.descricao == "Arroz Branco Tipo 1 Tio João 5kg"
    assert p.promocao == {"origem": "encarte", "fim": "2026-10-23"}
    assert p.sku == "arroz branco tipo 1 tio joao 5kg"


def test_guanabara_preco_por_kg_vira_1kg():
    p = guanabara.converter({"nome": "Presunto Cozido Sadia", "preco": 29.98, "por": "kg"}, None)
    assert p.descricao == "Presunto Cozido Sadia 1kg"


def test_guanabara_ignora_sem_preco():
    assert guanabara.converter({"nome": "Arte", "preco": None}, None) is None


def test_mercado_livre_converter():
    produto = {
        "id": "MLB123",
        "name": " Detergente Líquido Ypê Neutro 500ml ",
        "attributes": [{"id": "BRAND", "value_name": "Ypê"}],
        "pictures": [{"url": "https://http2.mlstatic.com/foto.jpg"}],
    }
    p = mercado_livre.converter(produto, {"price": 2.99, "original_price": 3.49})
    assert (p.sku, p.descricao, p.marca, p.preco, p.preco_regular) == (
        "MLB123", "Detergente Líquido Ypê Neutro 500ml", "Ypê", 2.99, 3.49)
    assert p.url == "https://www.mercadolivre.com.br/p/MLB123"
    assert p.imagem == "https://http2.mlstatic.com/foto.jpg"


def test_mercado_livre_ignora_preco_de_menor():
    p = mercado_livre.converter({"id": "MLB1", "name": "Arroz 1kg"}, {"price": 5.0, "original_price": 5.0})
    assert p.preco_regular is None and p.marca is None and p.imagem is None
