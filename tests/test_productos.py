from agro.db.productos import Producto


def test_agregar_y_obtener(db):
    assert db.productos.agregar("UREA", 120, 100, 10)
    p = db.productos.obtener("UREA")
    assert isinstance(p, Producto)
    assert (p.nombre, p.precio_venta, p.precio_compra, p.stock, p.unidad, p.stock_minimo, p.activo) == ("UREA", 120, 100, 10, "unid", 5, True)
    assert db.productos.obtener("NO EXISTE") is None
    assert db.productos.obtener_por_id(p.id) == p


def test_agregar_con_unidad_y_minimo(db):
    assert db.productos.agregar("ABONO FOLIAR", 35, 20, 12, unidad="L", stock_minimo=2)
    p = db.productos.obtener("ABONO FOLIAR")
    assert p.unidad == "L" and p.stock_minimo == 2 and not p.bajo_stock


def test_nombre_duplicado_devuelve_false(con_datos):
    assert con_datos.productos.agregar("UREA", 1, 1, 1) is False
    assert con_datos.productos.obtener("UREA").precio_venta == 120


def test_listar_y_nombres_ordenados(con_datos):
    assert con_datos.productos.nombres() == ["FOSFATO", "UREA"]
    assert [p.nombre for p in con_datos.productos.listar()] == ["FOSFATO", "UREA"]
    assert con_datos.productos.stock_total() == 15


def test_stock_total_sin_productos(db):
    assert db.productos.stock_total() == 0.0


def test_renombrar_conserva_id_e_historial(con_datos, ops):
    from tests.conftest import carrito
    db = con_datos
    id_urea = db.productos.obtener("UREA").id
    ops.registrar_venta(carrito(("UREA", 120, 1)), "2026-09-01", "Administradora", "PÚBLICO GENERAL")
    assert db.productos.modificar("UREA", "UREA GRANULADA", 130, 100)
    assert db.productos.obtener("UREA") is None
    p = db.productos.obtener("UREA GRANULADA")
    assert p.id == id_urea and p.precio_venta == 130
    assert [l.producto for l in db.boletas.obtener(1).lineas] == ["UREA GRANULADA"]


def test_renombrar_a_nombre_existente_falla_sin_cambios(con_datos):
    assert con_datos.productos.modificar("UREA", "FOSFATO", 1, 1) is False
    assert con_datos.productos.obtener("UREA").precio_venta == 120
    assert not con_datos.conn.in_transaction


def test_modificar_inexistente_devuelve_false(con_datos):
    assert con_datos.productos.modificar("NADA", "NADA", 1, 1) is False


def test_modificar_sin_stock_conserva_stock(con_datos):
    assert con_datos.productos.modificar("UREA", "UREA", 125, 90, None)
    p = con_datos.productos.obtener("UREA")
    assert (p.precio_venta, p.precio_compra, p.stock) == (125, 90, 10)


def test_modificar_con_stock_unidad_y_minimo(con_datos):
    assert con_datos.productos.modificar("UREA", "UREA", 120, 100, 2.5, unidad="saco", stock_minimo=3)
    p = con_datos.productos.obtener("UREA")
    assert (p.stock, p.unidad, p.stock_minimo, p.bajo_stock) == (2.5, "saco", 3, True)


def test_desactivar_conserva_historial_y_reactiva_al_crear(con_datos):
    p = con_datos.productos
    assert p.desactivar("UREA")
    assert p.obtener("UREA") is None
    assert p.obtener("UREA", incluir_inactivos=True).activo is False
    assert p.nombres() == ["FOSFATO"] and p.nombres(incluir_inactivos=True) == ["FOSFATO", "UREA"]
    assert p.stock_total() == 5  # los inactivos no cuentan
    assert p.eliminar("NADA") is False
    # volver a crearlo con el mismo nombre lo reactiva con los datos nuevos
    assert p.agregar("UREA", 150, 110, 3)
    q = p.obtener("UREA")
    assert q.activo and q.precio_venta == 150 and q.stock == 3


def test_reactivar(con_datos):
    con_datos.productos.desactivar("UREA")
    assert con_datos.productos.reactivar("UREA")
    assert con_datos.productos.obtener("UREA").activo


def test_ajustar_stock(con_datos):
    p = con_datos.productos
    assert p.ajustar_stock("UREA", 3, "restar") == 7
    assert p.ajustar_stock("UREA", 0.5, "sumar") == 7.5
    assert p.ajustar_stock("UREA", 0, "neutro") == 7.5
    assert p.ajustar_stock("NADA", 1, "restar") is None
    assert p.ajustar_stock("NADA", 0, "neutro") == 0
    p.desactivar("UREA")
    assert p.ajustar_stock("UREA", 1, "restar") is None  # inactivo: no se vende


def test_actualizar_precio_compra_y_margen(con_datos):
    con_datos.productos.actualizar_precio_compra("UREA", 90)
    p = con_datos.productos.obtener("UREA")
    assert p.precio_compra == 90 and p.margen_pct == 25
    assert Producto(1, "X", "unid", 10, 0, 1, 5, True).margen_pct is None


def test_bajo_minimo(con_datos):
    con_datos.productos.modificar("FOSFATO", "FOSFATO", 90, 70, 5, stock_minimo=5)
    assert [p.nombre for p in con_datos.productos.bajo_minimo()] == ["FOSFATO"]
