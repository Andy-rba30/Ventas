import pytest

from agro.servicios.formato import MES_A_NUMERO, MESES, cantidad, moneda, parse_cantidad, parse_dinero


@pytest.mark.parametrize("texto, esperado", [
    ("1/2", 0.5), ("0,5", 0.5), ("0.25", 0.25), (" 3 ", 3.0), ("3/4", 0.75), (2, 2.0),
])
def test_parse_cantidad_valores_validos(texto, esperado):
    assert parse_cantidad(texto) == esperado


@pytest.mark.parametrize("texto", ["1/0", "abc", "", "1/2/3", "/"])
def test_parse_cantidad_invalida_lanza_valueerror(texto):
    with pytest.raises(ValueError):
        parse_cantidad(texto)


def test_parse_dinero_acepta_prefijo():
    assert parse_dinero("S/. 12.50") == 12.5
    assert parse_dinero("7") == 7.0
    with pytest.raises(ValueError):
        parse_dinero("S/. x")


def test_formato_moneda_y_cantidad():
    assert moneda(12.5) == "S/. 12.50"
    assert moneda(0) == "S/. 0.00"
    assert cantidad(1.50) == "1.5"
    assert cantidad(3.0) == "3"
    assert cantidad(0.25) == "0.25"


def test_meses():
    assert len(MESES) == 12 and MES_A_NUMERO["Enero"] == 1 and MES_A_NUMERO["Diciembre"] == 12
