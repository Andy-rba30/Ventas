"""Fixtures compartidas. Todas las pruebas usan SQLite en memoria (o un archivo en tmp_path
cuando hace falta WAL/respaldo). Nunca tocan la BD real ni escriben en el repo."""
import pytest

from agro.db import BaseDatos
from agro.servicios.carrito import Carrito
from agro.servicios.operaciones import ServicioOperaciones
from agro.servicios.reportes import ServicioReportes


@pytest.fixture(autouse=True)
def _cwd_temporal(tmp_path, monkeypatch):
    # app.log se crea junto a la BD; con ':memory:' cae en el cwd, así que lo movemos a tmp.
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def db():
    bd = BaseDatos(":memory:")
    yield bd
    bd.cerrar()


@pytest.fixture
def db_archivo(tmp_path):
    """BD en archivo: necesaria para WAL, respaldo y migración."""
    bd = BaseDatos(str(tmp_path / "prueba.db"))
    yield bd
    bd.cerrar()


@pytest.fixture
def ops(db):
    return ServicioOperaciones(db)


@pytest.fixture
def reportes(db):
    return ServicioReportes(db)


@pytest.fixture
def con_datos(db):
    """Dos productos, un cliente y un proveedor."""
    assert db.productos.agregar("UREA", 120.0, 100.0, 10)
    assert db.productos.agregar("FOSFATO", 90.0, 70.0, 5)
    assert db.contactos.agregar("cliente", "JUAN", "12345678", "999")
    assert db.contactos.agregar("proveedor", "AGROSUR", "Pedro", "888")
    return db


def carrito(*lineas):
    """carrito(("UREA", 120, 2), ("FOSFATO", 90, 0.5)) -> Carrito"""
    c = Carrito()
    for producto, precio, cant in lineas:
        c.agregar(producto, precio, cant)
    return c
