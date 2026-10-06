"""Migración v0 (tabla plana `transacciones`) -> v1 (boletas, líneas, pagos)."""
import os
import sqlite3

import pytest

from agro.db import BaseDatos
from agro.db.esquema import VERSION_ESQUEMA


def _bd_legacy(ruta, con_columnas_nuevas=True):
    """Reproduce una BD creada por la versión anterior del programa, con datos típicos."""
    c = sqlite3.connect(ruta)
    c.execute("CREATE TABLE productos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, precio REAL, precio_compra REAL DEFAULT 0.0, stock REAL)")
    c.execute("CREATE TABLE encargadas (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE)")
    c.execute("CREATE TABLE clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, documento TEXT, telefono TEXT)")
    c.execute("CREATE TABLE proveedores (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, contacto TEXT, telefono TEXT)")
    cols = "fecha TEXT, hora TEXT, tipo TEXT, producto TEXT, cantidad REAL, total_dinero REAL, encargada TEXT, stock_resultante REAL"
    if con_columnas_nuevas:
        cols += ", cliente TEXT, proveedor TEXT, estado TEXT, ref_id INTEGER"
    c.execute(f"CREATE TABLE transacciones (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})")
    c.executemany("INSERT INTO productos (id, nombre, precio, precio_compra, stock) VALUES (?, ?, ?, ?, ?)",
                  [(1, "UREA", 120, 100, 27), (2, "FOSFATO", 90, 70, 4)])
    c.executemany("INSERT INTO encargadas (nombre) VALUES (?)", [("Administradora",), ("Rosa",)])
    c.executemany("INSERT INTO clientes (nombre, documento, telefono) VALUES (?, ?, ?)", [("PÚBLICO GENERAL", "-", "-"), ("JUAN", "1", "9")])
    c.execute("INSERT INTO proveedores (nombre, contacto, telefono) VALUES ('AGROSUR', 'Pedro', '8')")
    if con_columnas_nuevas:
        filas = [
            # id, fecha, hora, tipo, producto, cant, total, encargada, stock_res, cliente, proveedor, estado, ref_id
            (1, "2026-09-02", "10:00:00", "VENTA", "UREA", 2, 240, "Administradora", 8, "PÚBLICO GENERAL", "", "PAGADO", None),
            (2, "2026-09-02", "10:00:00", "VENTA", "FOSFATO", 1, 90, "Administradora", 4, "PÚBLICO GENERAL", "", "PAGADO", None),
            (3, "2026-09-04", "11:00:00", "ENTRADA", "UREA", 20, 1900, "Rosa", 28, "", "AGROSUR", "PAGADO", None),
            # fiado de 2 líneas: una pagada con cobro enlazado por ref_id, otra pagada con cobro antiguo sin ref_id
            (4, "2026-09-06", "12:00:00", "FIADO", "UREA", 1, 120, "Administradora", 27, "JUAN", "", "PAGADO", None),
            (5, "2026-09-06", "12:00:00", "FIADO", "FOSFATO", 1, 90, "Administradora", 3, "JUAN", "", "PAGADO", None),
            (6, "2026-09-10", "09:00:00", "COBRO_DEUDA", "UREA", 0, 120, "Rosa", 27, "JUAN", "", "COMPLETADO", 4),
            (7, "2026-09-11", "09:00:00", "COBRO_DEUDA", "FOSFATO", 1, 90, "Admin", 3, "JUAN", "", "COMPLETADO", None),
            # fiado pendiente de un producto que ya no existe
            (8, "2026-09-12", "13:00:00", "FIADO", "CAL AGRICOLA", 2, 30, "Administradora", 0, "JUAN", "", "PENDIENTE", None),
            # cobro huérfano: no hay fiado que coincida
            (9, "2026-09-13", "14:00:00", "COBRO_DEUDA", "UREA", 1, 999, "Admin", 27, "JUAN", "", "COMPLETADO", None),
            # cliente borrado que aún aparece en el historial
            (10, "2026-08-01", "08:00:00", "VENTA", "UREA", 1, 120, "Administradora", 30, "MARIA", "", "PAGADO", None),
        ]
        c.executemany("INSERT INTO transacciones VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", filas)
    else:
        c.execute("INSERT INTO transacciones VALUES (1, '2025-01-05', '10:00:00', 'VENTA', 'UREA', 1, 120, 'Administradora', 26)")
    c.commit(); c.close()


@pytest.fixture
def migrada(tmp_path):
    ruta = str(tmp_path / "negocio.db")
    _bd_legacy(ruta)
    db = BaseDatos(ruta)
    yield db, tmp_path
    db.cerrar()


def test_version_y_respaldo_previo(migrada):
    db, tmp_path = migrada
    assert db.version_esquema() == VERSION_ESQUEMA == 3
    copias = os.listdir(tmp_path / "backups")
    assert len(copias) == 1 and copias[0].startswith("negocio_pre_migracion_")
    vieja = sqlite3.connect(str(tmp_path / "backups" / copias[0]))
    assert vieja.execute("SELECT count(*) FROM transacciones").fetchone()[0] == 10  # la copia es la BD sin migrar
    vieja.close()


def test_tabla_vieja_se_conserva_renombrada(migrada):
    db, _ = migrada
    assert db.tabla_existe("_legacy_transacciones") and not db.tabla_existe("transacciones")
    assert db.cursor.execute("SELECT count(*) FROM _legacy_transacciones").fetchone()[0] == 10


def test_productos_conservan_id_y_faltante_se_crea_inactivo(migrada):
    db, _ = migrada
    urea = db.productos.obtener("UREA")
    assert (urea.id, urea.precio_venta, urea.precio_compra, urea.stock, urea.unidad, urea.stock_minimo) == (1, 120, 100, 27, "unid", 5)
    cal = db.productos.obtener("CAL AGRICOLA", incluir_inactivos=True)
    assert cal is not None and not cal.activo and db.productos.obtener("CAL AGRICOLA") is None


def test_boletas_agrupadas(migrada):
    db, _ = migrada
    bol = db.cursor.execute("SELECT id, fecha, tipo FROM boletas ORDER BY id").fetchall()  # se crean en orden cronológico
    assert [b[1] for b in bol] == ["2026-08-01", "2026-09-02", "2026-09-04", "2026-09-06", "2026-09-12"]
    assert [b[2] for b in bol] == ["VENTA", "VENTA", "ENTRADA", "FIADO", "FIADO"]
    venta = db.boletas.obtener(bol[1][0])
    assert venta.total == 330 and len(venta.lineas) == 2 and venta.cliente == "PÚBLICO GENERAL"
    assert [(l.producto, l.cantidad, l.precio_unit, l.stock_resultante) for l in venta.lineas] == [("UREA", 2, 120, 8), ("FOSFATO", 1, 90, 4)]
    entrada = db.boletas.obtener(bol[2][0])
    assert entrada.proveedor == "AGROSUR" and entrada.encargada == "Rosa" and entrada.total == 1900


def test_cobros_se_vinculan_por_ref_id_y_por_coincidencia(migrada):
    db, _ = migrada
    fiado = [b for b in (db.boletas.obtener(i) for i in range(1, 6)) if b and b.tipo == "FIADO" and b.total == 210][0]
    pagos = db.boletas.pagos_de(fiado.id)
    assert [(p.monto, p.fecha, p.encargada) for p in pagos] == [(120, "2026-09-10", "Rosa"), (90, "2026-09-11", "Admin")]
    assert fiado.estado == "PAGADO" and fiado.saldo == 0
    # el cobro huérfano (S/. 999) no se convirtió en pago
    assert db.cursor.execute("SELECT count(*) FROM pagos").fetchone()[0] == 2
    # la encargada legacy 'Admin' se creó inactiva
    assert "Admin" in db.contactos.encargadas(incluir_inactivas=True) and "Admin" not in db.contactos.encargadas()


def test_fiado_pendiente_sigue_pendiente(migrada):
    db, _ = migrada
    deudas = db.boletas.deudas_pendientes()
    assert len(deudas) == 1 and deudas[0].cliente == "JUAN" and deudas[0].total == 30 and deudas[0].estado == "PENDIENTE"
    assert deudas[0].lineas[0].producto == "CAL AGRICOLA"
    assert db.boletas.total_por_cobrar() == 30


def test_cliente_desconocido_se_crea_inactivo(migrada):
    db, _ = migrada
    assert "MARIA" not in db.contactos.nombres("cliente")
    assert db.contactos.id_de("cliente", "MARIA") is not None
    assert db.contactos.nombres("cliente") == ["JUAN", "PÚBLICO GENERAL"]


def test_reabrir_no_vuelve_a_migrar(migrada):
    db, tmp_path = migrada
    ruta = db.db_name
    db.cerrar()
    otra = BaseDatos(ruta)
    try:
        assert otra.version_esquema() == 3
        assert len(os.listdir(tmp_path / "backups")) == 1  # sin segunda copia
        assert otra.cursor.execute("SELECT count(*) FROM boletas").fetchone()[0] == 5
    finally:
        otra.cerrar()


def test_migracion_desde_esquema_muy_antiguo_sin_columnas_nuevas(tmp_path):
    ruta = str(tmp_path / "antigua.db")
    _bd_legacy(ruta, con_columnas_nuevas=False)
    db = BaseDatos(ruta)
    try:
        assert db.version_esquema() == 3
        b = db.boletas.obtener(1)
        assert b.tipo == "VENTA" and b.cliente == "" and b.total == 120 and b.estado == "PAGADO"
    finally:
        db.cerrar()


def test_bd_nueva_se_crea_directamente_en_v1(tmp_path):
    db = BaseDatos(str(tmp_path / "nueva.db"))
    try:
        assert db.version_esquema() == 3
        assert not db.tabla_existe("_legacy_transacciones") and not (tmp_path / "backups").exists()
        assert db.contactos.encargadas() == ["Administradora"] and db.contactos.nombres("cliente") == ["PÚBLICO GENERAL"]
        assert {"boletas", "boleta_lineas", "pagos"} <= {r[0] for r in db.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        indices = {r[0] for r in db.cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")}
        assert len(indices) == 7
    finally:
        db.cerrar()


def test_migracion_desde_v1_agrega_notas_y_costo(tmp_path):
    """Una BD que quedó en v1 (sin notas ni costo_unit) llega a la versión actual con una sola copia previa."""
    ruta = str(tmp_path / "v1.db")
    _bd_legacy(ruta)
    db = BaseDatos(ruta); db.cerrar()                 # v0 -> v2 (dos pasos, una copia)
    c = sqlite3.connect(ruta)
    c.execute("PRAGMA user_version=1")                # simular que quedó en v1
    c.execute("ALTER TABLE clientes DROP COLUMN notas"); c.execute("ALTER TABLE proveedores DROP COLUMN notas")
    c.commit(); c.close()
    db = BaseDatos(ruta)
    try:
        assert db.version_esquema() == 3
        assert "notas" in db.columnas_de("clientes") and "notas" in db.columnas_de("proveedores")
        assert "costo_unit" in db.columnas_de("boleta_lineas") and db.tabla_existe("precios_historial")
        assert db.contactos.obtener("cliente", "JUAN").notas == ""
        assert db.cursor.execute("SELECT count(*) FROM boletas").fetchone()[0] == 5  # los datos v1 siguen ahí
        assert len(os.listdir(tmp_path / "backups")) == 2  # copia del v0->v2 y copia del v1->v2
    finally:
        db.cerrar()


def test_bd_en_memoria_no_intenta_respaldar(db):
    assert db.version_esquema() == 3
