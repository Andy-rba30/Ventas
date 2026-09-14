import os
import sqlite3

import pytest

from agro.db import BaseDatos


def test_pragmas_y_log_en_archivo(db_archivo, tmp_path):
    assert db_archivo.cursor.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert db_archivo.cursor.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert (tmp_path / "app.log").exists()


def test_registros_por_defecto(db):
    assert db.contactos.encargadas() == ["Administradora"]
    assert db.contactos.nombres("cliente") == ["PÚBLICO GENERAL"]


def test_transaccion_confirma_al_salir(db):
    with db.transaccion():
        db.contactos.agregar_encargada("Rosa")
        assert db.conn.in_transaction
    assert not db.conn.in_transaction
    assert "Rosa" in db.contactos.encargadas()


def test_transaccion_revierte_ante_excepcion(db):
    with pytest.raises(sqlite3.OperationalError):
        with db.transaccion():
            db.contactos.agregar_encargada("Rosa")
            raise sqlite3.OperationalError("fallo simulado")
    assert not db.conn.in_transaction
    assert "Rosa" not in db.contactos.encargadas()


def test_transaccion_anidada_se_une_a_la_externa(db):
    with db.transaccion():
        with db.transaccion():
            db.contactos.agregar_encargada("Rosa")
        assert db.conn.in_transaction  # la interna no confirmó por su cuenta
    assert not db.conn.in_transaction and "Rosa" in db.contactos.encargadas()


def test_excepcion_en_anidada_revierte_todo(db):
    with pytest.raises(ValueError):
        with db.transaccion():
            db.contactos.agregar_encargada("Rosa")
            with db.transaccion():
                db.contactos.agregar_encargada("Ana")
                raise ValueError("fallo en la interna")
    assert db.contactos.encargadas() == ["Administradora"]


def _crear_bd_esquema_viejo(ruta):
    c = sqlite3.connect(ruta)
    c.execute("CREATE TABLE productos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, precio REAL, stock REAL)")
    c.execute("CREATE TABLE transacciones (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, hora TEXT, tipo TEXT, "
              "producto TEXT, cantidad REAL, total_dinero REAL, encargada TEXT, stock_resultante REAL)")
    c.execute("INSERT INTO productos (nombre, precio, stock) VALUES ('CAL', 10, 4)")
    c.execute("INSERT INTO transacciones (fecha, hora, tipo, producto, cantidad, total_dinero, encargada, stock_resultante) "
              "VALUES ('2025-01-05', '10:00:00', 'VENTA', 'CAL', 1, 10, 'Administradora', 4)")
    c.commit(); c.close()


def test_migracion_desde_esquema_viejo(tmp_path):
    ruta = str(tmp_path / "vieja.db")
    _crear_bd_esquema_viejo(ruta)
    db = BaseDatos(ruta)
    try:
        assert {"cliente", "estado", "proveedor", "ref_id"} <= db.columnas_de("transacciones")
        assert "precio_compra" in db.columnas_de("productos")
        assert db.productos.obtener("CAL").precio_compra == 0.0
        assert db.cursor.execute("SELECT cliente, estado, ref_id FROM transacciones").fetchone() == (None, None, None)
        assert "Administradora" in db.contactos.encargadas() and "PÚBLICO GENERAL" in db.contactos.nombres("cliente")
    finally:
        db.cerrar()
    # segunda apertura: la migración es idempotente
    BaseDatos(ruta).cerrar()


def test_respaldo_consistente_con_wal(db_archivo, tmp_path):
    db_archivo.productos.agregar("UREA", 1, 1, 1)
    destino = tmp_path / "copia.db"
    db_archivo.respaldar_a(str(destino))
    copia = sqlite3.connect(str(destino))
    try:
        assert copia.execute("SELECT nombre FROM productos").fetchall() == [("UREA",)]
        # la copia es un archivo autocontenido (sin -wal pendiente)
        assert not os.path.exists(str(destino) + "-wal")
    finally:
        copia.close()
