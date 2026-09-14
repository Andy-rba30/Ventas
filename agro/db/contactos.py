"""Repositorio de clientes, proveedores y encargadas."""
import sqlite3

from agro.config import CLIENTE_GENERAL, ENCARGADA_DEFAULT
from agro.registro import log


def _tabla(tipo):
    return "clientes" if tipo == "cliente" else "proveedores"


class RepositorioContactos:
    def __init__(self, cx):
        self.cx = cx

    # --- Clientes y proveedores (tipo: 'cliente' | 'proveedor') ---
    def agregar(self, tipo, nombre, doc_o_contacto, telefono):
        col2 = "documento" if tipo == "cliente" else "contacto"
        try:
            self.cx.cursor.execute(f"INSERT INTO {_tabla(tipo)} (nombre, {col2}, telefono) VALUES (?, ?, ?)", (nombre, doc_o_contacto, telefono))
            return True
        except sqlite3.IntegrityError:
            return False

    def eliminar(self, tipo, nombre):
        if nombre == CLIENTE_GENERAL:
            return False
        try:
            self.cx.cursor.execute(f"DELETE FROM {_tabla(tipo)} WHERE nombre=?", (nombre,))
            return True
        except sqlite3.Error as e:
            log.error("Error al eliminar %s '%s': %s", tipo, nombre, e)
            return False

    def listar(self, tipo):
        """Filas completas (id, nombre, documento|contacto, telefono) ordenadas por nombre."""
        return self.cx.cursor.execute(f"SELECT * FROM {_tabla(tipo)} ORDER BY nombre").fetchall()

    def nombres(self, tipo):
        return [row[0] for row in self.cx.cursor.execute(f"SELECT nombre FROM {_tabla(tipo)} ORDER BY nombre")]

    # --- Encargadas ---
    def agregar_encargada(self, nombre):
        try:
            self.cx.cursor.execute("INSERT INTO encargadas (nombre) VALUES (?)", (nombre,))
            return True
        except sqlite3.IntegrityError:
            return False

    def eliminar_encargada(self, nombre):
        if nombre == ENCARGADA_DEFAULT:
            return False
        try:
            self.cx.cursor.execute("DELETE FROM encargadas WHERE nombre=?", (nombre,))
            return True
        except sqlite3.Error as e:
            log.error("Error al eliminar encargada '%s': %s", nombre, e)
            return False

    def encargadas(self):
        return [row[0] for row in self.cx.cursor.execute("SELECT nombre FROM encargadas")]
