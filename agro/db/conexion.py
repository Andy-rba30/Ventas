"""Conexión SQLite: apertura, PRAGMAs, transacciones, respaldo y arranque de migraciones."""
import sqlite3
from contextlib import contextmanager

from agro.db import migraciones
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
        migraciones.aplicar(self)
        log.info("BD abierta: %s (esquema v%d)", ruta, self.version_esquema())

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
            # La copia hereda el modo WAL; se pasa a DELETE para que sea un único archivo portable.
            destino.execute("PRAGMA journal_mode=DELETE")
        finally:
            destino.close()
        log.info("Respaldo creado en %s", ruta_destino)

    # --- introspección ---
    def version_esquema(self):
        return self.cursor.execute("PRAGMA user_version").fetchone()[0]

    def tabla_existe(self, nombre):
        return self.cursor.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nombre,)).fetchone() is not None

    def columnas_de(self, tabla):
        return {row[1] for row in self.cursor.execute(f"PRAGMA table_info({tabla})")}
