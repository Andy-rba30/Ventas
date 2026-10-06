import pytest

from agro.servicios.carrito import Carrito, LineaCarrito


def test_carrito_vacio():
    c = Carrito()
    assert c.vacio and len(c) == 0 and c.total == 0


def test_agregar_calcula_subtotal_y_total():
    c = Carrito()
    linea = c.agregar("UREA", 120, "0.5" and 0.5)
    c.agregar("UREA", 120, 2)
    assert isinstance(linea, LineaCarrito)
    assert linea.subtotal == 60 and c.total == 300 and len(c) == 2
    assert c.cantidad_de("UREA") == 2.5 and c.cantidad_de("OTRO") == 0
    assert [l.producto for l in c] == ["UREA", "UREA"] and c[1].cantidad == 2


def test_editar_cantidad_recalcula_subtotal():
    c = Carrito(); c.agregar("UREA", 120, 1)
    c.editar(0, "cantidad", "1/4")
    assert c[0].cantidad == 0.25 and c[0].subtotal == 30


def test_editar_precio_recalcula_subtotal():
    c = Carrito(); c.agregar("UREA", 120, 2)
    c.editar(0, "precio_unit", "S/. 100")
    assert c[0].precio_unit == 100 and c[0].subtotal == 200


def test_editar_subtotal_no_toca_precio_unitario():
    """Un descuento fijo se registra en el subtotal; el precio original queda como referencia."""
    c = Carrito(); c.agregar("UREA", 120, 2)
    c.editar(0, "subtotal", "200")
    assert c[0].subtotal == 200 and c[0].precio_unit == 120 and c[0].cantidad == 2


@pytest.mark.parametrize("campo, texto", [
    ("cantidad", "0"), ("cantidad", "-1"), ("cantidad", "abc"), ("cantidad", "1/0"),
    ("precio_unit", "-1"), ("precio_unit", "x"),
    ("subtotal", "-5"), ("subtotal", ""),
    ("producto", "UREA"),
])
def test_editar_invalido_lanza_valueerror_y_no_cambia(campo, texto):
    c = Carrito(); c.agregar("UREA", 120, 2)
    with pytest.raises(ValueError):
        c.editar(0, campo, texto)
    assert c[0] == LineaCarrito("UREA", 120, 2, 240)


def test_quitar_y_vaciar():
    c = Carrito(); c.agregar("A", 1, 1); c.agregar("B", 2, 1)
    c.quitar(0)
    assert [l.producto for l in c] == ["B"]
    c.quitar(5)  # índice fuera de rango: no hace nada
    assert len(c) == 1
    c.vaciar()
    assert c.vacio
