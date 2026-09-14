import os
import sqlite3

import pytest


def test_pragmas_y_log_en_archivo(db_archivo):
    from agro.registro import log
    assert db_archivo.cursor.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert db_archivo.cursor.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    # el logger se configura una sola vez por proceso: basta con que escriba a un app.log
    assert any(getattr(h, "baseFilename", "").endswith("app.log") for h in log.handlers)


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


def test_introspeccion(db):
    assert db.version_esquema() == 1
    assert db.tabla_existe("boletas") and not db.tabla_existe("transacciones")
    assert {"id", "nombre", "unidad", "precio_venta", "stock_minimo", "activo"} <= db.columnas_de("productos")


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
