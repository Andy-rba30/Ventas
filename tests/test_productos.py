from agro.db.productos import Producto


def test_agregar_y_obtener(db):
    assert db.productos.agregar("UREA", 120, 100, 10)
    assert db.productos.obtener("UREA") == Producto("UREA", 120.0, 100.0, 10.0)
    assert db.productos.obtener("NO EXISTE") is None


def test_nombre_duplicado_devuelve_false(con_datos):
    assert con_datos.productos.agregar("UREA", 1, 1, 1) is False
    assert con_datos.productos.obtener("UREA").precio == 120


def test_listar_y_nombres_ordenados(con_datos):
    assert con_datos.productos.nombres() == ["FOSFATO", "UREA"]
    assert [p.nombre for p in con_datos.productos.listar()] == ["FOSFATO", "UREA"]
    assert con_datos.productos.stock_total() == 15


def test_stock_total_sin_productos(db):
    assert db.productos.stock_total() == 0.0


def test_renombrar_actualiza_historial(con_datos):
    db = con_datos
    db.transacciones.registrar("2026-09-01", "VENTA", "UREA", 1, 120, "Administradora", 9, estado="PAGADO")
    assert db.productos.modificar("UREA", "UREA GRANULADA", 130, 100)
    assert db.productos.obtener("UREA") is None
    assert db.productos.obtener("UREA GRANULADA").precio == 130
    assert db.cursor.execute("SELECT producto FROM transacciones").fetchone()[0] == "UREA GRANULADA"


def test_renombrar_a_nombre_existente_no_deja_cambios_parciales(con_datos):
    db = con_datos
    db.transacciones.registrar("2026-09-01", "VENTA", "UREA", 1, 120, "Administradora", 9, estado="PAGADO")
    assert db.productos.modificar("UREA", "FOSFATO", 1, 1) is False
    # ni el producto ni el historial cambiaron, y no quedó una transacción abierta
    assert db.productos.obtener("UREA").precio == 120
    assert db.cursor.execute("SELECT count(*) FROM transacciones WHERE producto='UREA'").fetchone()[0] == 1
    assert not db.conn.in_transaction


def test_modificar_sin_stock_conserva_stock(con_datos):
    assert con_datos.productos.modificar("UREA", "UREA", 125, 90, None)
    p = con_datos.productos.obtener("UREA")
    assert (p.precio, p.precio_compra, p.stock) == (125, 90, 10)


def test_modificar_con_stock(con_datos):
    assert con_datos.productos.modificar("UREA", "UREA", 120, 100, 2.5)
    assert con_datos.productos.obtener("UREA").stock == 2.5


def test_eliminar(con_datos):
    assert con_datos.productos.eliminar("UREA")
    assert con_datos.productos.obtener("UREA") is None
    assert con_datos.productos.eliminar("UREA")  # borrar algo inexistente no falla


def test_ajustar_stock(con_datos):
    p = con_datos.productos
    assert p.ajustar_stock("UREA", 3, "restar") == 7
    assert p.ajustar_stock("UREA", 0.5, "sumar") == 7.5
    assert p.ajustar_stock("UREA", 0, "neutro") == 7.5
    assert p.ajustar_stock("NADA", 1, "restar") is None
    assert p.ajustar_stock("NADA", 0, "neutro") == 0


def test_actualizar_precio_compra(con_datos):
    con_datos.productos.actualizar_precio_compra("UREA", 95)
    assert con_datos.productos.obtener("UREA").precio_compra == 95
