"""Repositorio de productos (inventario)."""
import sqlite3
from dataclasses import dataclass

from agro.registro import log


@dataclass
class Producto:
    nombre: str
    precio: float
    precio_compra: float
    stock: float


def _fila_a_producto(row):
    return Producto(row[0], float(row[1] or 0.0), float(row[2] or 0.0), float(row[3] or 0.0))


class RepositorioProductos:
    def __init__(self, cx):
        self.cx = cx

    def agregar(self, nombre, precio, precio_compra, stock):
        try:
            self.cx.cursor.execute("INSERT INTO productos (nombre, precio, precio_compra, stock) VALUES (?, ?, ?, ?)", (nombre, precio, precio_compra, stock))
            return True
        except sqlite3.IntegrityError:
            return False

    def modificar(self, nombre_actual, nuevo_nombre, nuevo_precio, nuevo_precio_compra, nuevo_stock=None):
        """Renombra/actualiza el producto y su historial en una sola transacción.
        Si el nuevo nombre ya existe no queda ningún cambio parcial."""
        try:
            with self.cx.transaccion():
                if nombre_actual != nuevo_nombre:
                    self.cx.cursor.execute("UPDATE transacciones SET producto=? WHERE producto=?", (nuevo_nombre, nombre_actual))
                if nuevo_stock is not None:
                    self.cx.cursor.execute("UPDATE productos SET nombre=?, precio=?, precio_compra=?, stock=? WHERE nombre=?", (nuevo_nombre, nuevo_precio, nuevo_precio_compra, nuevo_stock, nombre_actual))
                else:
                    self.cx.cursor.execute("UPDATE productos SET nombre=?, precio=?, precio_compra=? WHERE nombre=?", (nuevo_nombre, nuevo_precio, nuevo_precio_compra, nombre_actual))
            return True
        except sqlite3.IntegrityError:
            log.warning("No se pudo renombrar '%s' a '%s': el nombre ya existe", nombre_actual, nuevo_nombre)
            return False
        except sqlite3.Error as e:
            log.error("Error al modificar producto '%s': %s", nombre_actual, e)
            return False

    def eliminar(self, nombre):
        try:
            self.cx.cursor.execute("DELETE FROM productos WHERE nombre=?", (nombre,))
            return True
        except sqlite3.Error as e:
            log.error("Error al eliminar producto '%s': %s", nombre, e)
            return False

    def actualizar_precio_compra(self, nombre, precio_compra):
        self.cx.cursor.execute("UPDATE productos SET precio_compra=? WHERE nombre=?", (precio_compra, nombre))

    def ajustar_stock(self, nombre, cantidad, operacion):
        """operacion: 'sumar', 'restar' o 'neutro' (solo consulta).
        Devuelve el stock resultante, o None si el producto no existe."""
        res = self.cx.cursor.execute("SELECT stock FROM productos WHERE nombre=?", (nombre,)).fetchone()
        if not res:
            return 0 if operacion == "neutro" else None
        stock_actual = float(res[0])
        if operacion == "neutro":
            return stock_actual
        nuevo_stock = stock_actual + cantidad if operacion == "sumar" else stock_actual - cantidad
        self.cx.cursor.execute("UPDATE productos SET stock=? WHERE nombre=?", (nuevo_stock, nombre))
        return nuevo_stock

    def obtener(self, nombre):
        row = self.cx.cursor.execute("SELECT nombre, precio, precio_compra, stock FROM productos WHERE nombre=?", (nombre,)).fetchone()
        return _fila_a_producto(row) if row else None

    def listar(self):
        return [_fila_a_producto(r) for r in self.cx.cursor.execute("SELECT nombre, precio, precio_compra, stock FROM productos ORDER BY nombre")]

    def nombres(self):
        return [row[0] for row in self.cx.cursor.execute("SELECT nombre FROM productos ORDER BY nombre")]

    def stock_total(self):
        res = self.cx.cursor.execute("SELECT SUM(stock) FROM productos").fetchone()
        return float(res[0] or 0.0)
