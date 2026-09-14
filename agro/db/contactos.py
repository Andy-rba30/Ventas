"""Repositorio de clientes, proveedores y encargadas.

Un contacto con historial (boletas o pagos) no se borra: se desactiva."""
import sqlite3

from agro.config import CLIENTE_GENERAL, ENCARGADA_DEFAULT
from agro.registro import log


def _tabla(tipo):
    return "clientes" if tipo == "cliente" else "proveedores"


def _columna_boleta(tipo):
    return "cliente_id" if tipo == "cliente" else "proveedor_id"


class RepositorioContactos:
    def __init__(self, cx):
        self.cx = cx

    # --- Clientes y proveedores (tipo: 'cliente' | 'proveedor') ---
    def agregar(self, tipo, nombre, doc_o_contacto, telefono):
        """Crea el contacto. Si ya existe activo devuelve False; si existe inactivo lo reactiva."""
        col2 = "documento" if tipo == "cliente" else "contacto"
        tabla = _tabla(tipo)
        row = self.cx.cursor.execute(f"SELECT id, activo FROM {tabla} WHERE nombre=?", (nombre,)).fetchone()
        if row is not None:
            if row[1]:
                return False
            self.cx.cursor.execute(f"UPDATE {tabla} SET {col2}=?, telefono=?, activo=1 WHERE id=?", (doc_o_contacto, telefono, row[0]))
            return True
        self.cx.cursor.execute(f"INSERT INTO {tabla} (nombre, {col2}, telefono) VALUES (?, ?, ?)", (nombre, doc_o_contacto, telefono))
        return True

    def eliminar(self, tipo, nombre):
        """Borra el contacto; si tiene boletas asociadas solo lo desactiva. PÚBLICO GENERAL no se toca."""
        if nombre == CLIENTE_GENERAL:
            return False
        tabla = _tabla(tipo)
        id_ = self.id_de(tipo, nombre)
        if id_ is None:
            return False
        try:
            con_historial = self.cx.cursor.execute(
                f"SELECT 1 FROM boletas WHERE {_columna_boleta(tipo)}=? LIMIT 1", (id_,)).fetchone()
            if con_historial:
                self.cx.cursor.execute(f"UPDATE {tabla} SET activo=0 WHERE id=?", (id_,))
            else:
                self.cx.cursor.execute(f"DELETE FROM {tabla} WHERE id=?", (id_,))
            return True
        except sqlite3.Error as e:
            log.error("Error al eliminar %s '%s': %s", tipo, nombre, e)
            return False

    def listar(self, tipo, incluir_inactivos=False):
        """Filas (id, nombre, documento|contacto, telefono) ordenadas por nombre."""
        col2 = "documento" if tipo == "cliente" else "contacto"
        filtro = "" if incluir_inactivos else " WHERE activo=1"
        return self.cx.cursor.execute(f"SELECT id, nombre, {col2}, telefono FROM {_tabla(tipo)}{filtro} ORDER BY nombre").fetchall()

    def nombres(self, tipo, incluir_inactivos=False):
        return [r[1] for r in self.listar(tipo, incluir_inactivos)]

    def id_de(self, tipo, nombre):
        """Id del contacto (activo o no) o None."""
        if not nombre:
            return None
        row = self.cx.cursor.execute(f"SELECT id FROM {_tabla(tipo)} WHERE nombre=?", (nombre,)).fetchone()
        return row[0] if row else None

    def nombre_de(self, tipo, id_):
        if id_ is None:
            return ""
        row = self.cx.cursor.execute(f"SELECT nombre FROM {_tabla(tipo)} WHERE id=?", (id_,)).fetchone()
        return row[0] if row else ""

    # --- Encargadas ---
    def agregar_encargada(self, nombre):
        row = self.cx.cursor.execute("SELECT id, activo FROM encargadas WHERE nombre=?", (nombre,)).fetchone()
        if row is not None:
            if row[1]:
                return False
            self.cx.cursor.execute("UPDATE encargadas SET activo=1 WHERE id=?", (row[0],))
            return True
        self.cx.cursor.execute("INSERT INTO encargadas (nombre) VALUES (?)", (nombre,))
        return True

    def eliminar_encargada(self, nombre):
        if nombre == ENCARGADA_DEFAULT:
            return False
        id_ = self.id_encargada(nombre)
        if id_ is None:
            return False
        try:
            con_historial = self.cx.cursor.execute(
                "SELECT 1 FROM boletas WHERE encargada_id=? UNION SELECT 1 FROM pagos WHERE encargada_id=? LIMIT 1", (id_, id_)).fetchone()
            if con_historial:
                self.cx.cursor.execute("UPDATE encargadas SET activo=0 WHERE id=?", (id_,))
            else:
                self.cx.cursor.execute("DELETE FROM encargadas WHERE id=?", (id_,))
            return True
        except sqlite3.Error as e:
            log.error("Error al eliminar encargada '%s': %s", nombre, e)
            return False

    def encargadas(self, incluir_inactivas=False):
        filtro = "" if incluir_inactivas else " WHERE activo=1"
        return [r[0] for r in self.cx.cursor.execute(f"SELECT nombre FROM encargadas{filtro} ORDER BY id")]

    def id_encargada(self, nombre, crear=False):
        """Id de la encargada. Con crear=True la inserta (inactiva) si no existe,
        para no perder una operación por un nombre desconocido."""
        row = self.cx.cursor.execute("SELECT id FROM encargadas WHERE nombre=?", (nombre,)).fetchone()
        if row:
            return row[0]
        if not crear or not nombre:
            return None
        self.cx.cursor.execute("INSERT INTO encargadas (nombre, activo) VALUES (?, 0)", (nombre,))
        log.warning("Encargada '%s' no existía; creada inactiva", nombre)
        return self.cx.cursor.lastrowid
