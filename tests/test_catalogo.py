"""Reconhecimento de produtos com nomes reais vistos no Pão de Açúcar."""

import pytest

from compras import catalogo

ITENS = {i.id: i for i in catalogo.carregar()}


@pytest.mark.parametrize(
    "item, descricao, esperado",
    [
        # aceitos
        ("arroz-branco", "Arroz Agulhinha Tipo 1 TIO JOÃO Pacote 5kg", 5),
        ("arroz-branco", "Arroz Branco Tipo 1 Qualitá Pacote 2kg", 2),
        ("cafe-po", "Café Torrado e Moído Tradicional Pilão Pacote 500g", 0.5),
        ("detergente", "Detergente Líquido Neutro Limpol Squeeze 500ml", 0.5),
        ("detergente", "Lava-Louças Líquido Concentrado Erva-Doce Cif Squeeze 420ml", 0.42),
        ("sabao-po", "Lava-Roupas Pó Omo Lavagem Perfeita Caixa 800g", 0.8),
        ("ovos", "Ovos Vermelho Extra Bandeija C/20", 20),
        ("ovos", "Qualitá Ovo Vermelho Grande Caipira Com 20 Unidades", 20),
        ("ketchup", "Qualitá Ketchup Tradicional 380G", 0.38),
        ("papel-higienico", "Papel Higiênico Neve Leve 12 Pague 11 rolos", 12),
        ("papel-toalha", "Toalha de Papel Folha Dupla Qualitá Pacote 2 Unidades", 2),
        ("saco-lixo", "Saco de Lixo Reforçado Oceano Pacote com 50 Embalixo 50L", 50),
        ("escova-dente", "Escova Dental Ultramacia Colgate Sensitive", 1),
        ("esponja", "Esponja Multiuso Esfrebom Leve 4 Pague 3 Unidades", 4),
        ("leite-desnatado", "Leite UHT Semidesnatado Gloria 1L", 1),
        ("cerveja", "Cerveja Lata 350ml c/12", 4.2),
        # rejeitados
        ("arroz-branco", "Alimento para Cães Adultos Carne com Arroz Purina Dog Chow 1kg", None),
        ("arroz-branco", "Macarrão de Arroz e Milho Spaghetti Barilla Pacote 500g", None),
        ("arroz-branco", "Arroz Integral Tipo 1 TIO JOÃO Pacote 1kg", None),
        ("sal", "Manteiga Extra com Sal Aviação 200g", None),
        ("cafe-po", "Café em Cápsula Torrado e Moído Espresso Intenso 10 Unidades", None),
        ("detergente", "Detergente Sanitário Gel Adesivo Citrus Pato 38g Refil", None),
        ("detergente", "Detergente Tablete para Máquina de Lavar Louças Finish 30 Unidades", None),
        ("leite-integral", "Leite em Pó Ninho Integral Sachê 575g", None),
        ("leite-integral", "Leite Fermentado Integral Morango Activia Bandeja 480g", None),
        ("requeijao", "Pizza Lombo com Requeijão e Mussarela Sadia 460g", None),
        ("ketchup", "Kit Ketchup Tradicional 397g + Maionese 215g + Mostarda", None),
        ("refrigerante-cola", "Refrigerante sem Açúcar Coca-Cola Lata 350ml", None),
        ("pipoca-microondas", "Combo Refrigerante Guaraná ANTARCTICA 2 Litros + Pipoca", None),
        ("saco-lixo", "Saco De Lixo Embalixo Alca Bloqueadora De Odores 30 Litros", None),
    ],
)
def test_reconhece(item, descricao, esperado):
    q = ITENS[item].reconhece(descricao)
    if esperado is None:
        assert q is None
    else:
        assert q is not None and q.valor == pytest.approx(esperado)


def test_catalogo_valido():
    for item in ITENS.values():
        assert item.unidade in ("kg", "L", "un"), item.id
        assert item.comeca, f"{item.id} sem 'comeca'"


MARCAS = catalogo.Marcas(["TIO JOÃO", "Tio", "3 CORAÇÕES", "QUALITÁ", "Personal"])


@pytest.mark.parametrize(
    "item, descricao, esperado",
    [
        ("arroz-parboilizado", "Tio João Arroz Parboilizado - 5Kg", 5),
        ("cafe-po", "3 Corações Café Torrado E Moído Tradicional Pacote 500G", 0.5),
        ("papel-higienico", "Personal Papel Higiênico Vip Folha Tripla Com 12 Rolos De 20M", 12),
        ("refrigerante-cola", "Refrigerante Pepsi 2.25L", 2.25),
        ("sabao-liquido", "Lava-Roupas Suprema 5L", 5),
        ("papel-higienico", "Papel Higienico Rolão Institucional Com 08 Rolos 300 Metros", None),
    ],
)
def test_reconhece_com_marca_no_inicio(item, descricao, esperado):
    q = ITENS[item].reconhece(descricao, marcas=MARCAS)
    assert (q.valor if q else None) == (pytest.approx(esperado) if esperado else None)


def test_encontra_marca_mais_longa():
    assert MARCAS.encontrar("Tio João Arroz Parboilizado 5kg") == "TIO JOÃO"
    assert MARCAS.encontrar("Café Torrado 3 Corações 500g") == "3 CORAÇÕES"
    assert MARCAS.encontrar("Arroz Branco Urbano 1kg") is None
