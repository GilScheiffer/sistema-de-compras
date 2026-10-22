from datetime import date

from compras.coletores import guanabara


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
