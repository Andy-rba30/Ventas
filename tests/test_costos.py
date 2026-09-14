"""Costo promedio ponderado (función pura) e historial de precios (servicio + repositorio)."""
import datetime

import pytest

from agro.servicios.costos import costo_promedio
from agro.servicios.reportes import ServicioReportes
from tests.conftest import carrito

HOY = datetime.date.today()


# --- función pura -------------------------------------------------------------

@pytest.mark.parametrize("stock, costo, cant, nuevo, esperado", [
    (10, 100, 10, 120, 110.0),          # mitad y mitad
    (7, 100, 10, 110, 105.8824),        # ponderado, redondeo a 4 decimales
    (0, 100, 5, 130, 130.0),            # sin stock previo: manda el nuevo costo
    (-3, 100, 5, 130, 130.0),           # stock negativo por ventas sin stock
    (10, 0, 5, 130, 130.0),             # sin costo previo conocido
    (10, 100, 0, 130, 100.0),           # sin cantidad nueva: no cambia
    (10, 100, 0.5, 100, 100.0),         # mismo costo: no cambia
    (None, None, 2, 50, 50.0),          # tolera None
])
def test_costo_promedio(stock, costo, cant, nuevo, esperado):
    assert costo_promedio(stock, costo, cant, nuevo) == esperado


def test_costo_promedio_fraccionario():
    # 2.5 sacos a 80 + 0.5 saco a 100 = 200 + 50 = 250 / 3
    assert costo_promedio(2.5, 80, 0.5, 100) == round(250 / 3, 4)


# --- integración con el servicio ---------------------------------------------

def test_compra_actualiza_promedio_y_anota_historial(ops, con_datos):
    ops.registrar_compra(carrito(("UREA", 130, 10)), HOY, "Administradora", "AGROSUR")
    p = con_datos.productos.obtener("UREA")
    assert p.stock == 20 and p.precio_compra == 115.0
    hist = con_datos.precios.historial(p.id, tipo="compra")
    # el alta anotó 100 y la compra anotó 130 (el costo pagado, no el promedio)
    assert [h.precio for h in hist] == [130.0, 100.0]
    assert con_datos.precios.ultimo(p.id, "compra").precio == 130.0


def test_mismo_producto_repetido_en_la_compra_promedia_en_cadena(ops, con_datos):
    ops.registrar_compra(carrito(("UREA", 130, 10), ("UREA", 160, 10)), HOY, "Administradora", "AGROSUR")
    p = con_datos.productos.obtener("UREA")
    # 10@100 + 10@130 = 115; luego 20@115 + 10@160 = 130
    assert p.stock == 30 and p.precio_compra == 130.0


def test_venta_guarda_el_costo_vigente_en_la_linea(ops, con_datos):
    ops.registrar_compra(carrito(("UREA", 140, 10)), HOY, "Administradora", "AGROSUR")   # promedio 120
    boleta_id = ops.registrar_venta(carrito(("UREA", 150, 4)), HOY, "Administradora", "PÚBLICO GENERAL")
    linea = con_datos.boletas.lineas_de(boleta_id)[0]
    assert linea.costo_unit == 120.0
    # una compra posterior no altera el costo ya guardado en la venta
    ops.registrar_compra(carrito(("UREA", 200, 10)), HOY, "Administradora", "AGROSUR")
    assert con_datos.boletas.lineas_de(boleta_id)[0].costo_unit == 120.0


def test_margen_usa_el_costo_de_cada_linea(ops, con_datos):
    ops.registrar_venta(carrito(("UREA", 150, 4)), HOY, "Administradora", "PÚBLICO GENERAL")  # costo 100
    ops.registrar_compra(carrito(("UREA", 200, 10)), HOY, "Administradora", "AGROSUR")        # promedio sube
    r = ServicioReportes(con_datos).generar(HOY.year, HOY.month)
    assert r.costo_vendido == 400.0 and r.margen_bruto == 200.0


def test_alta_y_cambio_de_precio_de_venta_quedan_en_el_historial(con_datos):
    p = con_datos.productos.obtener("UREA")
    assert [h.precio for h in con_datos.precios.historial(p.id, tipo="venta")] == [120.0]
    assert con_datos.productos.modificar("UREA", "UREA", 125.0, 100.0)
    assert con_datos.productos.modificar("UREA", "UREA", 125.0, 100.0, stock_minimo=12)  # sin cambio de precio
    assert [h.precio for h in con_datos.precios.historial(p.id, tipo="venta")] == [125.0, 120.0]
    assert con_datos.precios.ultimo(p.id, "venta").precio == 125.0
    assert con_datos.precios.ultimo(p.id, "compra").precio == 100.0


def test_historial_respeta_limite_y_orden(con_datos):
    p = con_datos.productos.obtener("UREA")
    for i, dia in enumerate(("2024-01-01", "2024-01-03", "2024-01-02")):
        con_datos.precios.registrar(p.id, "compra", 100 + i, fecha=dia, hora="10:00:00")
    hist = con_datos.precios.historial(p.id, limite=2, tipo="compra")
    assert [(h.fecha, h.precio) for h in hist] == [(HOY.isoformat(), 100.0), ("2024-01-03", 101.0)]


def test_tipo_de_precio_invalido(con_datos):
    with pytest.raises(ValueError):
        con_datos.precios.registrar(1, "regalo", 1)
