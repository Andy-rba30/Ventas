import sqlite3

import pytest

from agro.db.transacciones import FIADO_PAGADO, NO_EXISTE, OK
from agro.servicios.operaciones import ErrorOperacion
from tests.conftest import carrito


# --- ventas ---------------------------------------------------------------

def test_venta_descuenta_stock_de_todas_las_lineas(con_datos, ops):
    c = carrito(("UREA", 120, 2), ("FOSFATO", 90, 0.5), ("UREA", 120, 1))
    assert ops.registrar_venta(c, "2026-09-05", "Administradora", "PÚBLICO GENERAL") == "VENTA"
    assert con_datos.productos.obtener("UREA").stock == 7
    assert con_datos.productos.obtener("FOSFATO").stock == 4.5
    filas = con_datos.cursor.execute(
        "SELECT tipo, producto, cantidad, total_dinero, estado, cliente, stock_resultante FROM transacciones ORDER BY id").fetchall()
    assert filas == [
        ("VENTA", "UREA", 2, 240, "PAGADO", "PÚBLICO GENERAL", 8),
        ("VENTA", "FOSFATO", 0.5, 45, "PAGADO", "PÚBLICO GENERAL", 4.5),
        ("VENTA", "UREA", 1, 120, "PAGADO", "PÚBLICO GENERAL", 7),
    ]
    # las tres líneas comparten hora: forman una sola boleta en el reporte
    assert con_datos.cursor.execute("SELECT count(DISTINCT hora) FROM transacciones").fetchone()[0] == 1


def test_venta_con_subtotal_editado_registra_el_subtotal(con_datos, ops):
    c = carrito(("UREA", 120, 2)); c.editar(0, "subtotal", "200")
    ops.registrar_venta(c, "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    assert con_datos.cursor.execute("SELECT total_dinero FROM transacciones").fetchone()[0] == 200


def test_venta_carrito_vacio_rechazada(con_datos, ops):
    with pytest.raises(ErrorOperacion, match="vacío"):
        ops.registrar_venta(carrito(), "2026-09-05", "Administradora", "PÚBLICO GENERAL")


def test_fiado_a_publico_general_rechazado(con_datos, ops):
    with pytest.raises(ErrorOperacion, match="cliente"):
        ops.registrar_venta(carrito(("UREA", 120, 1)), "2026-09-05", "Administradora", "PÚBLICO GENERAL", fiado=True)
    assert con_datos.productos.obtener("UREA").stock == 10


def test_venta_sobre_stock_deja_stock_negativo(con_datos, ops):
    """Comportamiento heredado: la UI advierte, pero el servicio permite vender sin stock."""
    ops.registrar_venta(carrito(("FOSFATO", 90, 8)), "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    assert con_datos.productos.obtener("FOSFATO").stock == -3


def test_linea_de_producto_inexistente_se_omite(con_datos, ops):
    """Comportamiento heredado: si el producto ya no existe, esa línea no se registra."""
    ops.registrar_venta(carrito(("UREA", 120, 1), ("FANTASMA", 5, 1)), "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    assert con_datos.cursor.execute("SELECT count(*) FROM transacciones").fetchone()[0] == 1


def test_venta_es_atomica_si_falla_una_linea(con_datos, ops, monkeypatch):
    original = con_datos.transacciones.registrar
    llamadas = {"n": 0}

    def registrar_fallando(*a, **k):
        llamadas["n"] += 1
        if llamadas["n"] == 2:
            raise sqlite3.OperationalError("disco lleno (simulado)")
        return original(*a, **k)

    monkeypatch.setattr(con_datos.transacciones, "registrar", registrar_fallando)
    with pytest.raises(sqlite3.OperationalError):
        ops.registrar_venta(carrito(("UREA", 120, 2), ("FOSFATO", 90, 1)), "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    assert con_datos.productos.obtener("UREA").stock == 10  # la primera línea se revirtió
    assert con_datos.cursor.execute("SELECT count(*) FROM transacciones").fetchone()[0] == 0
    assert not con_datos.conn.in_transaction


# --- compras ----------------------------------------------------------------

def test_compra_suma_stock_y_actualiza_costo(con_datos, ops):
    ops.registrar_compra(carrito(("UREA", 95, 20)), "2026-09-04", "Administradora", "AGROSUR")
    p = con_datos.productos.obtener("UREA")
    assert p.stock == 30 and p.precio_compra == 95
    fila = con_datos.cursor.execute("SELECT tipo, proveedor, estado, total_dinero FROM transacciones").fetchone()
    assert fila == ("ENTRADA", "AGROSUR", "PAGADO", 1900)


@pytest.mark.parametrize("proveedor", ["", None])
def test_compra_sin_proveedor_rechazada(con_datos, ops, proveedor):
    with pytest.raises(ErrorOperacion, match="proveedor"):
        ops.registrar_compra(carrito(("UREA", 95, 1)), "2026-09-04", "Administradora", proveedor)


def test_compra_carrito_vacio_rechazada(con_datos, ops):
    with pytest.raises(ErrorOperacion):
        ops.registrar_compra(carrito(), "2026-09-04", "Administradora", "AGROSUR")


# --- fiados y cobros --------------------------------------------------------

@pytest.fixture
def fiado(con_datos, ops):
    ops.registrar_venta(carrito(("UREA", 120, 3)), "2026-09-03", "Administradora", "JUAN", fiado=True)
    deudas = con_datos.transacciones.deudas_pendientes()
    assert len(deudas) == 1 and deudas[0][2:] == ("JUAN", "UREA", 3, 360)
    return deudas[0][0]


def test_fiado_queda_pendiente(con_datos, fiado):
    assert con_datos.productos.obtener("UREA").stock == 7
    assert con_datos.transacciones.fiados_pendientes_de("JUAN") == [("2026-09-03", "UREA", 3, 360)]
    assert con_datos.transacciones.fiados_pendientes_de("OTRO") == []


def test_cobrar_fiado_registra_cobro_enlazado(con_datos, ops, fiado):
    assert ops.cobrar_fiado(fiado, "Rosa", "2026-09-10")
    assert con_datos.transacciones.deudas_pendientes() == []
    cobro = con_datos.cursor.execute(
        "SELECT encargada, cantidad, ref_id, fecha, total_dinero, estado, cliente FROM transacciones WHERE tipo='COBRO_DEUDA'").fetchone()
    assert cobro == ("Rosa", 0, fiado, "2026-09-10", 360, "COMPLETADO", "JUAN")
    assert con_datos.productos.obtener("UREA").stock == 7  # cobrar no mueve stock


def test_cobrar_fiado_usa_fecha_de_hoy_por_defecto(con_datos, ops, fiado):
    from agro.servicios.formato import hoy
    assert ops.cobrar_fiado(fiado, "Rosa")
    assert con_datos.cursor.execute("SELECT fecha FROM transacciones WHERE tipo='COBRO_DEUDA'").fetchone()[0] == hoy()


def test_no_se_cobra_dos_veces(con_datos, ops, fiado):
    assert ops.cobrar_fiado(fiado, "Rosa")
    assert ops.cobrar_fiado(fiado, "Rosa") is False
    assert con_datos.cursor.execute("SELECT count(*) FROM transacciones WHERE tipo='COBRO_DEUDA'").fetchone()[0] == 1


def test_cobrar_id_inexistente_o_no_fiado(con_datos, ops):
    ops.registrar_venta(carrito(("UREA", 120, 1)), "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    id_venta = con_datos.cursor.execute("SELECT id FROM transacciones").fetchone()[0]
    assert ops.cobrar_fiado(id_venta, "Rosa") is False
    assert ops.cobrar_fiado(9999, "Rosa") is False


def test_no_se_borra_fiado_pagado_pero_borrar_cobro_lo_reabre(con_datos, ops, fiado):
    ops.cobrar_fiado(fiado, "Rosa")
    id_cobro = con_datos.cursor.execute("SELECT id FROM transacciones WHERE tipo='COBRO_DEUDA'").fetchone()[0]

    assert ops.eliminar_operaciones([fiado]) == ([fiado], [])
    assert con_datos.cursor.execute("SELECT count(*) FROM transacciones").fetchone()[0] == 2

    assert ops.eliminar_operaciones([id_cobro]) == ([], [])
    assert len(con_datos.transacciones.deudas_pendientes()) == 1

    antes = con_datos.productos.obtener("UREA").stock
    assert ops.eliminar_operaciones([fiado]) == ([], [])
    assert con_datos.productos.obtener("UREA").stock == antes + 3
    assert con_datos.cursor.execute("SELECT count(*) FROM transacciones").fetchone()[0] == 0


def test_eliminar_venta_y_entrada_revierten_stock(con_datos, ops):
    ops.registrar_venta(carrito(("UREA", 120, 2)), "2026-09-05", "Administradora", "PÚBLICO GENERAL")
    ops.registrar_compra(carrito(("FOSFATO", 70, 4)), "2026-09-05", "Administradora", "AGROSUR")
    ids = [r[0] for r in con_datos.cursor.execute("SELECT id FROM transacciones")]
    assert ops.eliminar_operaciones(ids) == ([], [])
    assert con_datos.productos.obtener("UREA").stock == 10
    assert con_datos.productos.obtener("FOSFATO").stock == 5


def test_codigos_de_eliminar_y_reversar(con_datos, ops, fiado):
    assert con_datos.transacciones.eliminar_y_reversar(9999) == NO_EXISTE
    ops.cobrar_fiado(fiado, "Rosa")
    assert con_datos.transacciones.eliminar_y_reversar(fiado) == FIADO_PAGADO
    id_cobro = con_datos.cursor.execute("SELECT id FROM transacciones WHERE tipo='COBRO_DEUDA'").fetchone()[0]
    assert con_datos.transacciones.eliminar_y_reversar(id_cobro) == OK


def test_cobro_antiguo_sin_ref_id_se_borra_sin_reabrir(con_datos, fiado):
    """Registros previos a la columna ref_id: el cobro se elimina y queda un aviso en el log."""
    con_datos.cursor.execute("UPDATE transacciones SET estado='PAGADO' WHERE id=?", (fiado,))
    id_cobro = con_datos.transacciones.registrar("2026-09-10", "COBRO_DEUDA", "UREA", 0, 360, "Admin", 7, cliente="JUAN", estado="COMPLETADO")
    assert con_datos.transacciones.eliminar_y_reversar(id_cobro) == OK
    assert con_datos.transacciones.deudas_pendientes() == []
