"""Conexión SQLite: apertura, PRAGMAs, esquema, migraciones, transacciones y respaldo."""
import sqlite3
from contextlib import contextmanager

from agro.config import CLIENTE_GENERAL, ENCARGADA_DEFAULT
from agro.registro import configurar_logging, log


class Conexion:
    def __init__(self, ruta):
        self.db_name = ruta
        configurar_logging(ruta)
        # isolation_level=None: autocommit por sentencia; las operaciones de varias
        # sentencias se agrupan explícitamente con `with self.transaccion():`.
        self.conn = sqlite3.connect(ruta, isolation_level=None)
        self.cursor = self.conn.cursor()
        self._nivel_transaccion = 0
        self.cursor.execute("PRAGMA foreign_keys=ON")
        if ruta != ":memory:":
            self.cursor.execute("PRAGMA journal_mode=WAL")
        self.crear_tablas()
        self.migrar_tablas()
        log.info("BD abierta: %s", ruta)

    @contextmanager
    def transaccion(self):
        """Agrupa varias sentencias: se guardan todas o ninguna. Admite anidamiento
        (el bloque interno se une al externo)."""
        if self._nivel_transaccion == 0:
            self.cursor.execute("BEGIN")
        self._nivel_transaccion += 1
        try:
            yield
        except BaseException:
            self._nivel_transaccion -= 1
            if self._nivel_transaccion == 0 and self.conn.in_transaction:
                self.conn.rollback()
            raise
        else:
            self._nivel_transaccion -= 1
            if self._nivel_transaccion == 0:
                self.conn.commit()

    def cerrar(self):
        try:
            self.conn.close()
        except sqlite3.Error as e:
            log.warning("Error al cerrar la BD: %s", e)

    def respaldar_a(self, ruta_destino):
        """Copia consistente de la BD (segura con WAL) usando la API de respaldo de SQLite."""
        destino = sqlite3.connect(ruta_destino)
        try:
            self.conn.backup(destino)
        finally:
            destino.close()
        log.info("Respaldo creado en %s", ruta_destino)

    # --- Esquema ---
    def crear_tablas(self):
        # Se usa REAL en stock y cantidad para soportar dosis (1/2, 0.5, etc.)
        with self.transaccion():
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS productos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE,
                    precio REAL,
                    precio_compra REAL DEFAULT 0.0,
                    stock REAL
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS transacciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT,
                    hora TEXT,
                    tipo TEXT,
                    producto TEXT,
                    cantidad REAL,
                    total_dinero REAL,
                    encargada TEXT,
                    stock_resultante REAL,
                    cliente TEXT,
                    proveedor TEXT,
                    estado TEXT,
                    ref_id INTEGER
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS encargadas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS clientes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE,
                    documento TEXT,
                    telefono TEXT
                )
            """)
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS proveedores (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT UNIQUE,
                    contacto TEXT,
                    telefono TEXT
                )
            """)
            # Registros por defecto
            if self.cursor.execute("SELECT count(*) FROM encargadas").fetchone()[0] == 0:
                self.cursor.execute("INSERT INTO encargadas (nombre) VALUES (?)", (ENCARGADA_DEFAULT,))
            if self.cursor.execute("SELECT count(*) FROM clientes").fetchone()[0] == 0:
                self.cursor.execute("INSERT INTO clientes (nombre, documento, telefono) VALUES (?, '-', '-')", (CLIENTE_GENERAL,))

    def columnas_de(self, tabla):
        return {row[1] for row in self.cursor.execute(f"PRAGMA table_info({tabla})")}

    def migrar_tablas(self):
        """Añade columnas que falten en BDs creadas por versiones anteriores."""
        columnas = [
            ("transacciones", "cliente", "TEXT"),
            ("transacciones", "estado", "TEXT"),
            ("transacciones", "proveedor", "TEXT"),
            ("transacciones", "ref_id", "INTEGER"),
            ("productos", "precio_compra", "REAL DEFAULT 0.0"),
        ]
        with self.transaccion():
            for tabla, col, tipo in columnas:
                if col not in self.columnas_de(tabla):
                    self.cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}")
                    log.info("Migración: columna %s.%s añadida", tabla, col)
