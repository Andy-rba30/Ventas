"""Repositorio de boletas y pagos, y reglas de contactos con historial."""
import pytest

from agro.db.boletas import NO_EXISTE, OK, TIENE_PAGOS


def _ids(db):
    return {
        "urea": db.productos.obtener("UREA").id,
        "fosfato": db.productos.obtener("FOSFATO").id,
        "juan": db.contactos.id_de("cliente", "JUAN"),
        "agrosur": db.contactos.id_de("proveedor", "AGROSUR"),
        "admin": db.contactos.id_encargada("Administradora"),
    }


def test_crear_boleta_calcula_total_y_estado(con_datos):
    ids = _ids(con_datos)
    bid = con_datos.boletas.crear("2026-09-01", "VENTA", ids["admin"], [(ids["urea"], 2, 120, 240, 8), (ids["fosfato"], 1, 90, 90, 4)],
                                  cliente_id=ids["juan"], hora="10:00:00")
    b = con_datos.boletas.obtener(bid)
    assert (b.total, b.estado, b.hora, b.cliente, b.proveedor, b.persona, b.pagado, b.saldo) == (330, "PAGADO", "10:00:00", "JUAN", "", "JUAN", 0, 330)
    assert [l.producto for l in b.lineas] == ["UREA", "FOSFATO"]
    fid = con_datos.boletas.crear("2026-09-01", "FIADO", ids["admin"], [(ids["urea"], 1, 120, 120, 7)], cliente_id=ids["juan"])
    assert con_datos.boletas.obtener(fid).estado == "PENDIENTE"
    assert con_datos.boletas.obtener(9999) is None


def test_crear_sin_lineas_falla(con_datos):
    with pytest.raises(ValueError):
        con_datos.boletas.crear("2026-09-01", "VENTA", _ids(con_datos)["admin"], [])


def test_tipo_invalido_rechazado_por_la_bd(con_datos):
    import sqlite3
    with pytest.raises(sqlite3.IntegrityError):
        con_datos.boletas.crear("2026-09-01", "REGALO", _ids(con_datos)["admin"], [(_ids(con_datos)["urea"], 1, 1, 1, 1)])


@pytest.fixture
def fiado(con_datos):
    ids = _ids(con_datos)
    return con_datos.boletas.crear("2026-09-03", "FIADO", ids["admin"], [(ids["urea"], 3, 120, 360, 7)], cliente_id=ids["juan"])


def test_registrar_pago_parcial_y_total(con_datos, fiado):
    admin = _ids(con_datos)["admin"]
    p1 = con_datos.boletas.registrar_pago(fiado, 100, admin, fecha="2026-09-10", hora="09:00:00", notas="adelanto")
    b = con_datos.boletas.obtener(fiado)
    assert (b.estado, b.pagado, b.saldo) == ("PARCIAL", 100, 260)
    con_datos.boletas.registrar_pago(fiado, 260, admin)
    b = con_datos.boletas.obtener(fiado)
    assert (b.estado, b.pagado, b.saldo) == ("PAGADO", 360, 0)
    pagos = con_datos.boletas.pagos_de(fiado)
    assert pagos[0].id == p1 and pagos[0].notas == "adelanto" and pagos[0].encargada == "Administradora"
    assert con_datos.boletas.deudas_pendientes() == [] and con_datos.boletas.total_por_cobrar() == 0


@pytest.mark.parametrize("monto", [0, -1, 360.01])
def test_pago_invalido(con_datos, fiado, monto):
    with pytest.raises(ValueError):
        con_datos.boletas.registrar_pago(fiado, monto, _ids(con_datos)["admin"])


def test_pago_sobre_venta_contado_rechazado(con_datos):
    ids = _ids(con_datos)
    bid = con_datos.boletas.crear("2026-09-01", "VENTA", ids["admin"], [(ids["urea"], 1, 120, 120, 9)], cliente_id=ids["juan"])
    with pytest.raises(ValueError):
        con_datos.boletas.registrar_pago(bid, 10, ids["admin"])


def test_deudas_pendientes_ordenadas_y_por_cliente(con_datos, fiado):
    ids = _ids(con_datos)
    con_datos.contactos.agregar("cliente", "ANA", "", "")
    ana = con_datos.contactos.id_de("cliente", "ANA")
    f2 = con_datos.boletas.crear("2026-09-01", "FIADO", ids["admin"], [(ids["fosfato"], 1, 90, 90, 4)], cliente_id=ana)
    assert [b.id for b in con_datos.boletas.deudas_pendientes()] == [f2, fiado]  # más antigua primero
    assert [b.cliente for b in con_datos.boletas.deudas_pendientes("ANA")] == ["ANA"]
    assert con_datos.boletas.total_por_cobrar() == 450


def test_eliminar_pago_reabre_el_fiado(con_datos, fiado):
    admin = _ids(con_datos)["admin"]
    p1 = con_datos.boletas.registrar_pago(fiado, 360, admin)
    assert con_datos.boletas.obtener(fiado).estado == "PAGADO"
    assert con_datos.boletas.eliminar_pago(p1) == OK
    assert con_datos.boletas.obtener(fiado).estado == "PENDIENTE"
    assert con_datos.boletas.eliminar_pago(p1) == NO_EXISTE


def test_eliminar_boleta_con_pagos_bloqueada(con_datos, fiado):
    con_datos.boletas.registrar_pago(fiado, 10, _ids(con_datos)["admin"])
    assert con_datos.boletas.eliminar_boleta(fiado) == TIENE_PAGOS
    assert con_datos.boletas.eliminar_linea(con_datos.boletas.obtener(fiado).lineas[0].id) == TIENE_PAGOS
    assert con_datos.boletas.eliminar_boleta(9999) == NO_EXISTE
    assert con_datos.boletas.eliminar_linea(9999) == NO_EXISTE


def test_eliminar_boleta_revierte_stock_por_id_aunque_el_producto_este_inactivo(con_datos, fiado):
    con_datos.productos.desactivar("UREA")
    assert con_datos.boletas.eliminar_boleta(fiado) == OK
    assert con_datos.productos.obtener("UREA", incluir_inactivos=True).stock == 13
    assert con_datos.cursor.execute("SELECT count(*) FROM boleta_lineas").fetchone()[0] == 0


def test_eliminar_entrada_resta_stock(con_datos):
    ids = _ids(con_datos)
    bid = con_datos.boletas.crear("2026-09-01", "ENTRADA", ids["admin"], [(ids["urea"], 5, 90, 450, 15)], proveedor_id=ids["agrosur"])
    assert con_datos.boletas.obtener(bid).persona == "AGROSUR"
    assert con_datos.boletas.eliminar_boleta(bid) == OK
    assert con_datos.productos.obtener("UREA").stock == 5


def test_dataframes(con_datos, fiado):
    con_datos.boletas.registrar_pago(fiado, 60, _ids(con_datos)["admin"], fecha="2026-09-10")
    bol, lin, pag = con_datos.boletas.boletas_dataframe(), con_datos.boletas.lineas_dataframe(), con_datos.boletas.pagos_dataframe()
    assert bol.iloc[0][["tipo", "cliente", "total", "pagado", "estado"]].tolist() == ["FIADO", "JUAN", 360, 60, "PARCIAL"]
    assert lin.iloc[0][["producto", "cantidad", "subtotal", "cliente"]].tolist() == ["UREA", 3, 360, "JUAN"]
    assert pag.iloc[0][["monto", "cliente", "encargada"]].tolist() == [60, "JUAN", "Administradora"]


# --- contactos con historial ------------------------------------------------

def test_cliente_con_boletas_se_desactiva_en_vez_de_borrarse(con_datos, fiado):
    assert con_datos.contactos.eliminar("cliente", "JUAN")
    assert "JUAN" not in con_datos.contactos.nombres("cliente")
    assert con_datos.contactos.id_de("cliente", "JUAN") is not None
    assert con_datos.boletas.obtener(fiado).cliente == "JUAN"  # el historial sigue mostrando el nombre
    # volver a agregarlo lo reactiva
    assert con_datos.contactos.agregar("cliente", "JUAN", "999", "111")
    assert ("JUAN", "999", "111") in [r[1:4] for r in con_datos.contactos.listar("cliente")]


def test_cliente_sin_boletas_se_borra(con_datos):
    con_datos.contactos.agregar("cliente", "PEPE", "1", "2")
    assert con_datos.contactos.eliminar("cliente", "PEPE")
    assert con_datos.contactos.id_de("cliente", "PEPE") is None
    assert con_datos.contactos.eliminar("cliente", "PEPE") is False
    assert con_datos.contactos.eliminar("cliente", "PÚBLICO GENERAL") is False


def test_encargada_con_historial_se_desactiva(con_datos):
    ids = _ids(con_datos)
    con_datos.contactos.agregar_encargada("Rosa")
    rosa = con_datos.contactos.id_encargada("Rosa")
    con_datos.boletas.crear("2026-09-01", "VENTA", rosa, [(ids["urea"], 1, 120, 120, 9)], cliente_id=ids["juan"])
    assert con_datos.contactos.eliminar_encargada("Rosa")
    assert con_datos.contactos.encargadas() == ["Administradora"]
    assert con_datos.contactos.encargadas(incluir_inactivas=True) == ["Administradora", "Rosa"]
    assert con_datos.contactos.eliminar_encargada("Administradora") is False
    assert con_datos.contactos.agregar_encargada("Rosa")  # reactiva
    assert con_datos.contactos.encargadas() == ["Administradora", "Rosa"]
    assert con_datos.contactos.agregar_encargada("Rosa") is False


def test_id_encargada_crear(con_datos):
    assert con_datos.contactos.id_encargada("Nadie") is None
    id_ = con_datos.contactos.id_encargada("Nadie", crear=True)
    assert id_ and con_datos.contactos.id_encargada("Nadie") == id_
    assert "Nadie" not in con_datos.contactos.encargadas()


# --- deudores, pagos parciales e historial ----------------------------------

def test_varios_pagos_parciales_nunca_superan_el_total(con_datos, fiado):
    admin = _ids(con_datos)["admin"]
    for monto in (100, 200, 59.99):
        con_datos.boletas.registrar_pago(fiado, monto, admin)
    b = con_datos.boletas.obtener(fiado)
    assert b.estado == "PARCIAL" and b.pagado == 359.99 and b.saldo == 0.01
    with pytest.raises(ValueError):
        con_datos.boletas.registrar_pago(fiado, 0.02, admin)      # supera el saldo
    con_datos.boletas.registrar_pago(fiado, 0.01, admin)
    b = con_datos.boletas.obtener(fiado)
    assert b.estado == "PAGADO" and b.saldo == 0 and len(con_datos.boletas.pagos_de(fiado)) == 4
    with pytest.raises(ValueError):
        con_datos.boletas.registrar_pago(fiado, 1, admin)         # ya no hay saldo


def test_resumen_deudores(con_datos, fiado):
    import datetime
    ids = _ids(con_datos)
    con_datos.contactos.agregar("cliente", "ANA", "", "")
    ana = con_datos.contactos.id_de("cliente", "ANA")
    con_datos.boletas.crear("2026-08-01", "FIADO", ids["admin"], [(ids["fosfato"], 1, 90, 90, 4)], cliente_id=ana)
    con_datos.boletas.crear("2026-09-05", "FIADO", ids["admin"], [(ids["fosfato"], 2, 90, 180, 2)], cliente_id=ana)
    con_datos.boletas.registrar_pago(fiado, 60, ids["admin"])
    deudores = con_datos.boletas.resumen_deudores(hoy=datetime.date(2026, 9, 14))
    assert [(d.cliente, d.n_boletas, d.deuda, d.fecha_mas_antigua, d.dias) for d in deudores] == [
        ("ANA", 2, 270, "2026-08-01", 44),      # la deuda más antigua primero
        ("JUAN", 1, 300, "2026-09-03", 11),
    ]
    # al pagar todo, el cliente desaparece del resumen
    con_datos.boletas.registrar_pago(fiado, 300, ids["admin"])
    assert [d.cliente for d in con_datos.boletas.resumen_deudores()] == ["ANA"]
    assert con_datos.boletas.resumen_deudores.__doc__  # documentado


def test_resumen_deudores_vacio(db):
    assert db.boletas.resumen_deudores() == []


def test_pagos_de_cliente_mas_reciente_primero(con_datos, fiado):
    ids = _ids(con_datos)
    f2 = con_datos.boletas.crear("2026-09-04", "FIADO", ids["admin"], [(ids["fosfato"], 1, 90, 90, 4)], cliente_id=ids["juan"])
    con_datos.boletas.registrar_pago(fiado, 50, ids["admin"], fecha="2026-09-10", hora="10:00:00", notas="adelanto")
    con_datos.boletas.registrar_pago(f2, 90, ids["admin"], fecha="2026-09-12", hora="09:00:00")
    con_datos.boletas.registrar_pago(fiado, 10, ids["admin"], fecha="2026-09-12", hora="11:00:00")
    pagos = con_datos.boletas.pagos_de_cliente("JUAN")
    assert [(p.boleta_id, p.monto, p.fecha, p.notas) for p in pagos] == [
        (fiado, 10, "2026-09-12", ""), (f2, 90, "2026-09-12", ""), (fiado, 50, "2026-09-10", "adelanto")]
    assert con_datos.boletas.pagos_de_cliente("NADIE") == []
