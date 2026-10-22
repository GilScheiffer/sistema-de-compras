import pytest

from compras import ErroCompras
from compras.unidades import Quantidade, extrair, formatar, ler


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Arroz Tio João Tipo 1 5kg", Quantidade(5, "kg")),
        ("Café Pilão 500g", Quantidade(0.5, "kg")),
        ("Óleo de Soja Liza 900 ml", Quantidade(0.9, "L")),
        ("Leite Integral 1L", Quantidade(1, "L")),
        ("Amaciante 1,5L", Quantidade(1.5, "L")),
        ("Papel Higiênico Neve 12 rolos", Quantidade(12, "un")),
        ("Cerveja 6x350ml", Quantidade(2.1, "L")),
        ("Cerveja Lata 350ml c/12", Quantidade(4.2, "L")),
        ("Detergente Ypê 500ml", Quantidade(0.5, "L")),
    ],
)
def test_extrair(texto, esperado):
    assert extrair(texto) == esperado


def test_extrair_sem_quantidade():
    assert extrair("Banana prata") is None


def test_ler_numero_puro_usa_unidade_do_item():
    assert ler("2", "kg") == Quantidade(2, "kg")


def test_ler_invalido():
    with pytest.raises(ErroCompras):
        ler("muito")


def test_formatar():
    assert formatar(Quantidade(0.5, "kg")) == "500 g"
    assert formatar(Quantidade(1.5, "L")) == "1,5 L"
    assert formatar(12, "un") == "12 un"
