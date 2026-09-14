"""Esquema v1: productos, contactos, boletas con líneas y pagos.

Versionado con PRAGMA user_version. La versión 0 es el esquema heredado (tabla
`transacciones` plana); `migraciones.py` lo convierte a esta versión.
"""
from agro.config import CLIENTE_GENERAL, ENCARGADA_DEFAULT, UMBRAL_BAJO_STOCK

VERSION_ESQUEMA = 1

TABLAS = [
    f"""
    CREATE TABLE IF NOT EXISTS productos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        unidad TEXT NOT NULL DEFAULT 'unid',
        precio_venta REAL NOT NULL DEFAULT 0,
        precio_compra REAL NOT NULL DEFAULT 0,
        stock REAL NOT NULL DEFAULT 0,
        stock_minimo REAL NOT NULL DEFAULT {UMBRAL_BAJO_STOCK},
        activo INTEGER NOT NULL DEFAULT 1
    )""",
    """
    CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        documento TEXT,
        telefono TEXT,
        activo INTEGER NOT NULL DEFAULT 1
    )""",
    """
    CREATE TABLE IF NOT EXISTS proveedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        contacto TEXT,
        telefono TEXT,
        activo INTEGER NOT NULL DEFAULT 1
    )""",
    """
    CREATE TABLE IF NOT EXISTS encargadas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL UNIQUE,
        activo INTEGER NOT NULL DEFAULT 1
    )""",
    """
    CREATE TABLE IF NOT EXISTS boletas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT NOT NULL,
        hora TEXT NOT NULL,
        tipo TEXT NOT NULL CHECK (tipo IN ('VENTA', 'FIADO', 'ENTRADA')),
        cliente_id INTEGER REFERENCES clientes(id),
        proveedor_id INTEGER REFERENCES proveedores(id),
        encargada_id INTEGER NOT NULL REFERENCES encargadas(id),
        total REAL NOT NULL DEFAULT 0,
        estado TEXT NOT NULL CHECK (estado IN ('PAGADO', 'PENDIENTE', 'PARCIAL')),
        notas TEXT NOT NULL DEFAULT ''
    )""",
    """
    CREATE TABLE IF NOT EXISTS boleta_lineas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        boleta_id INTEGER NOT NULL REFERENCES boletas(id) ON DELETE CASCADE,
        producto_id INTEGER NOT NULL REFERENCES productos(id),
        cantidad REAL NOT NULL,
        precio_unit REAL NOT NULL,
        subtotal REAL NOT NULL,
        stock_resultante REAL
    )""",
    """
    CREATE TABLE IF NOT EXISTS pagos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        boleta_id INTEGER NOT NULL REFERENCES boletas(id) ON DELETE CASCADE,
        fecha TEXT NOT NULL,
        hora TEXT NOT NULL,
        monto REAL NOT NULL,
        encargada_id INTEGER NOT NULL REFERENCES encargadas(id),
        notas TEXT NOT NULL DEFAULT ''
    )""",
]

INDICES = [
    "CREATE INDEX IF NOT EXISTS idx_boletas_fecha ON boletas(fecha)",
    "CREATE INDEX IF NOT EXISTS idx_boletas_tipo_estado ON boletas(tipo, estado)",
    "CREATE INDEX IF NOT EXISTS idx_boletas_cliente ON boletas(cliente_id)",
    "CREATE INDEX IF NOT EXISTS idx_lineas_boleta ON boleta_lineas(boleta_id)",
    "CREATE INDEX IF NOT EXISTS idx_lineas_producto ON boleta_lineas(producto_id)",
    "CREATE INDEX IF NOT EXISTS idx_pagos_boleta ON pagos(boleta_id)",
]


def crear_esquema(cursor):
    """Crea tablas e índices que falten e inserta los registros por defecto."""
    for sentencia in TABLAS + INDICES:
        cursor.execute(sentencia)
    if cursor.execute("SELECT count(*) FROM encargadas").fetchone()[0] == 0:
        cursor.execute("INSERT INTO encargadas (nombre) VALUES (?)", (ENCARGADA_DEFAULT,))
    if cursor.execute("SELECT count(*) FROM clientes").fetchone()[0] == 0:
        cursor.execute("INSERT INTO clientes (nombre, documento, telefono) VALUES (?, '-', '-')", (CLIENTE_GENERAL,))
