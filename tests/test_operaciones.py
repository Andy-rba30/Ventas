import sqlite3

import pytest

from agro.servicios.operaciones import ErrorOperacion, clave_boleta, clave_linea, clave_pago
from tests.conftest import carrito


def _boletas(db):
    return db.cursor.execute("SELECT id, tipo, total, estado FROM boletas ORDER BY id").fetchall()


# --- ventas ---------------------------------------------------------------

def test_venta_crea_una_boleta_con_todas_las_lineas(con_datos, ops):
    c = carrito(("UREA", 120, 2), ("FOSFATO", 90, 0.5), ("UREA", 120, 1))
    assert ops.registrar_venta(c, "2026-09-05", "Administradora", "PÚBLICO GENERAL") == "VENTA"
    assert con_datos.productos.obtener("UREA").stock == 7
    assert con_datos.productos.obtener("FOSFATO").stock == 4.5
    assert _boletas(con_datos) == [(1, "VENTA", 405, "PAGADO")]
    b = con_datos.boletas.obtener(1)
    assert b.cliente == "PÚBLICO GENERAL" and b.encargada == "Administradora" and b.fecha == "2026-09-05"
    assert [(l.producto, l.cantidad, l.precio_unit, l.subtotal, l.stock_resultante) for l in b.lineas] == [
        ("UREA", 2, 120, 240, 8), ("FOSFATO", 0.5, 90, 45, 4.5), ("UREA", 1, 120, 120, 7)]


def test_venta_con_subtotal_editado_registra_el_subtotal(con_datos, ops):
    c = carrito(("UREA", 120, 2)); c.editar(0, "subtotal", "200")
    ops.registrar_venta(c, "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    b = con_datos.boletas.obtener(1)
    assert b.total == 200 and b.lineas[0].precio_unit == 120


def test_venta_carrito_vacio_rechazada(con_datos, ops):
    with pytest.raises(ErrorOperacion, match="vacío"):
        ops.registrar_venta(carrito(), "2026-09-05", "Administradora", "PÚBLICO GENERAL")


def test_fiado_a_publico_general_rechazado(con_datos, ops):
    with pytest.raises(ErrorOperacion, match="cliente"):
        ops.registrar_venta(carrito(("UREA", 120, 1)), "2026-09-05", "Administradora", "PÚBLICO GENERAL", fiado=True)
    assert con_datos.productos.obtener("UREA").stock == 10


def test_venta_a_cliente_inexistente_rechazada(con_datos, ops):
    with pytest.raises(ErrorOperacion, match="no existe"):
        ops.registrar_venta(carrito(("UREA", 120, 1)), "2026-09-05", "Administradora", "NADIE")


def test_venta_sobre_stock_deja_stock_negativo(con_datos, ops):
    """Comportamiento heredado: la UI advierte, pero el servicio permite vender sin stock."""
    ops.registrar_venta(carrito(("FOSFATO", 90, 8)), "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    assert con_datos.productos.obtener("FOSFATO").stock == -3


def test_linea_de_producto_inexistente_se_omite(con_datos, ops):
    """Comportamiento heredado: si el producto ya no existe, esa línea no se registra."""
    ops.registrar_venta(carrito(("UREA", 120, 1), ("FANTASMA", 5, 1)), "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    assert len(con_datos.boletas.obtener(1).lineas) == 1


def test_carrito_solo_con_productos_inexistentes_rechazado(con_datos, ops):
    with pytest.raises(ErrorOperacion, match="Ninguno"):
        ops.registrar_venta(carrito(("FANTASMA", 5, 1)), "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    assert _boletas(con_datos) == []


def test_encargada_desconocida_se_crea_inactiva(con_datos, ops):
    ops.registrar_venta(carrito(("UREA", 120, 1)), "2026-09-05", "Temporal", "PÚBLICO GENERAL")
    assert con_datos.boletas.obtener(1).encargada == "Temporal"
    assert "Temporal" not in con_datos.contactos.encargadas()
    assert "Temporal" in con_datos.contactos.encargadas(incluir_inactivas=True)


def test_venta_es_atomica_si_falla_la_boleta(con_datos, ops, monkeypatch):
    def crear_fallando(*a, **k):
        raise sqlite3.OperationalError("disco lleno (simulado)")
    monkeypatch.setattr(con_datos.boletas, "crear", crear_fallando)
    with pytest.raises(sqlite3.OperationalError):
        ops.registrar_venta(carrito(("UREA", 120, 2), ("FOSFATO", 90, 1)), "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    assert con_datos.productos.obtener("UREA").stock == 10  # el descuento de stock se revirtió
    assert con_datos.productos.obtener("FOSFATO").stock == 5
    assert _boletas(con_datos) == [] and not con_datos.conn.in_transaction


# --- compras ----------------------------------------------------------------

def test_compra_suma_stock_y_actualiza_costo(con_datos, ops):
    boleta_id = ops.registrar_compra(carrito(("UREA", 95, 20)), "2026-09-04", "Administradora", "AGROSUR")
    p = con_datos.productos.obtener("UREA")
    assert p.stock == 30 and p.precio_compra == 95
    b = con_datos.boletas.obtener(boleta_id)
    assert (b.tipo, b.proveedor, b.estado, b.total, b.cliente) == ("ENTRADA", "AGROSUR", "PAGADO", 1900, "")


@pytest.mark.parametrize("proveedor", ["", None])
def test_compra_sin_proveedor_rechazada(con_datos, ops, proveedor):
    with pytest.raises(ErrorOperacion, match="proveedor"):
        ops.registrar_compra(carrito(("UREA", 95, 1)), "2026-09-04", "Administradora", proveedor)


def test_compra_proveedor_inexistente_rechazada(con_datos, ops):
    with pytest.raises(ErrorOperacion, match="no existe"):
        ops.registrar_compra(carrito(("UREA", 95, 1)), "2026-09-04", "Administradora", "NADIE")


def test_compra_carrito_vacio_rechazada(con_datos, ops):
    with pytest.raises(ErrorOperacion):
        ops.registrar_compra(carrito(), "2026-09-04", "Administradora", "AGROSUR")


# --- fiados y pagos ---------------------------------------------------------

@pytest.fixture
def fiado(con_datos, ops):
    ops.registrar_venta(carrito(("UREA", 120, 3), ("FOSFATO", 90, 1)), "2026-09-03", "Administradora", "JUAN", fiado=True)
    deudas = con_datos.boletas.deudas_pendientes()
    assert len(deudas) == 1 and deudas[0].cliente == "JUAN" and deudas[0].total == 450 and deudas[0].saldo == 450
    return deudas[0].id


def test_fiado_queda_pendiente(con_datos, fiado):
    assert con_datos.productos.obtener("UREA").stock == 7
    assert con_datos.boletas.obtener(fiado).estado == "PENDIENTE"
    assert con_datos.boletas.fiados_pendientes_de("JUAN") == [("2026-09-03", "UREA", 3, 360), ("2026-09-03", "FOSFATO", 1, 90)]
    assert con_datos.boletas.fiados_pendientes_de("OTRO") == []
    assert con_datos.boletas.total_por_cobrar() == 450


def test_cobrar_saldo_completo(con_datos, ops, fiado):
    pago_id = ops.cobrar_fiado(fiado, "Rosa", fecha="2026-09-10")
    b = con_datos.boletas.obtener(fiado)
    assert b.estado == "PAGADO" and b.pagado == 450 and b.saldo == 0
    assert con_datos.boletas.deudas_pendientes() == []
    pago = con_datos.boletas.obtener_pago(pago_id)
    assert (pago.monto, pago.encargada, pago.fecha) == (450, "Rosa", "2026-09-10")
    assert con_datos.productos.obtener("UREA").stock == 7  # cobrar no mueve stock


def test_pago_parcial_y_luego_total(con_datos, ops, fiado):
    ops.cobrar_fiado(fiado, "Rosa", monto=100, fecha="2026-09-10")
    b = con_datos.boletas.obtener(fiado)
    assert b.estado == "PARCIAL" and b.pagado == 100 and b.saldo == 350
    assert len(con_datos.boletas.deudas_pendientes()) == 1
    ops.cobrar_fiado(fiado, "Rosa")  # sin monto: paga el saldo
    assert con_datos.boletas.obtener(fiado).estado == "PAGADO"
    assert [p.monto for p in con_datos.boletas.pagos_de(fiado)] == [100, 350]


def test_cobrar_fiado_usa_fecha_de_hoy_por_defecto(con_datos, ops, fiado):
    from agro.servicios.formato import hoy
    pago_id = ops.cobrar_fiado(fiado, "Rosa")
    assert con_datos.boletas.obtener_pago(pago_id).fecha == hoy()


@pytest.mark.parametrize("monto", [0, -5, 450.01, 1000])
def test_pago_invalido_rechazado(con_datos, ops, fiado, monto):
    with pytest.raises(ErrorOperacion):
        ops.cobrar_fiado(fiado, "Rosa", monto=monto)
    assert con_datos.boletas.obtener(fiado).pagado == 0


def test_no_se_cobra_un_fiado_ya_pagado(con_datos, ops, fiado):
    ops.cobrar_fiado(fiado, "Rosa")
    with pytest.raises(ErrorOperacion, match="ya está pagado"):
        ops.cobrar_fiado(fiado, "Rosa")
    assert len(con_datos.boletas.pagos_de(fiado)) == 1


def test_cobrar_algo_que_no_es_fiado(con_datos, ops):
    ops.registrar_venta(carrito(("UREA", 120, 1)), "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    with pytest.raises(ErrorOperacion):
        ops.cobrar_fiado(1, "Rosa")
    with pytest.raises(ErrorOperacion):
        ops.cobrar_fiado(9999, "Rosa")


# --- eliminación ------------------------------------------------------------

def test_fiado_con_pagos_no_se_borra_pero_borrar_el_pago_lo_reabre(con_datos, ops, fiado):
    pago_id = ops.cobrar_fiado(fiado, "Rosa")
    assert ops.eliminar_operaciones([clave_boleta(fiado)]) == ([clave_boleta(fiado)], [])
    clave_l = clave_linea(con_datos.boletas.obtener(fiado).lineas[0].id)
    assert ops.eliminar_operaciones([clave_l]) == ([clave_l], [])  # tampoco una línea suelta
    assert len(con_datos.boletas.obtener(fiado).lineas) == 2

    assert ops.eliminar_operaciones([clave_pago(pago_id)]) == ([], [])
    assert con_datos.boletas.obtener(fiado).estado == "PENDIENTE"
    assert len(con_datos.boletas.deudas_pendientes()) == 1

    antes = con_datos.productos.obtener("UREA").stock
    assert ops.eliminar_operaciones([clave_boleta(fiado)]) == ([], [])
    assert con_datos.productos.obtener("UREA").stock == antes + 3
    assert con_datos.boletas.obtener(fiado) is None and _boletas(con_datos) == []


def test_eliminar_venta_y_entrada_revierten_stock(con_datos, ops):
    ops.registrar_venta(carrito(("UREA", 120, 2)), "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    ops.registrar_compra(carrito(("FOSFATO", 70, 4)), "2026-09-05", "Administradora", "AGROSUR")
    claves = [clave_boleta(r[0]) for r in _boletas(con_datos)]
    assert ops.eliminar_operaciones(claves) == ([], [])
    assert con_datos.productos.obtener("UREA").stock == 10
    assert con_datos.productos.obtener("FOSFATO").stock == 5
    assert con_datos.cursor.execute("SELECT count(*) FROM boleta_lineas").fetchone()[0] == 0


def test_eliminar_una_linea_recalcula_total(con_datos, ops):
    ops.registrar_venta(carrito(("UREA", 120, 2), ("FOSFATO", 90, 1)), "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    b = con_datos.boletas.obtener(1)
    assert ops.eliminar_operaciones([clave_linea(b.lineas[1].id)]) == ([], [])
    b = con_datos.boletas.obtener(1)
    assert b.total == 240 and len(b.lineas) == 1
    assert con_datos.productos.obtener("FOSFATO").stock == 5
    # al borrar la última línea desaparece la boleta
    assert ops.eliminar_operaciones([clave_linea(b.lineas[0].id)]) == ([], [])
    assert con_datos.boletas.obtener(1) is None and con_datos.productos.obtener("UREA").stock == 10


def test_claves_invalidas_e_inexistentes(con_datos, ops):
    assert ops.eliminar_operaciones(["B:9999", "L:9999", "P:9999"]) == ([], [])  # no existen: nada que hacer
    assert ops.eliminar_operaciones(["X:1"]) == ([], ["X:1"])
    ops.registrar_venta(carrito(("UREA", 120, 1)), "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    assert ops.eliminar_operaciones([1]) == ([], [])  # entero suelto = boleta
    assert _boletas(con_datos) == []
