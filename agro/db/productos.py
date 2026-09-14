"""Repositorio de productos (inventario). Los productos no se borran: se desactivan
para conservar el historial de boletas."""
import sqlite3
from dataclasses import dataclass

from agro.config import UMBRAL_BAJO_STOCK
from agro.registro import log

_COLUMNAS = "id, nombre, unidad, precio_venta, precio_compra, stock, stock_minimo, activo"


@dataclass
class Producto:
    id: int
    nombre: str
    unidad: str
    precio_venta: float
    precio_compra: float
    stock: float
    stock_minimo: float
    activo: bool

    @property
    def bajo_stock(self):
        return self.stock <= self.stock_minimo

    @property
    def margen_pct(self):
        """Margen bruto sobre el precio de venta, o None si no hay costo."""
        if not self.precio_compra or not self.precio_venta:
            return None
        return (self.precio_venta - self.precio_compra) / self.precio_venta * 100


def _fila(row):
    return Producto(row[0], row[1], row[2], float(row[3]), float(row[4]), float(row[5]), float(row[6]), bool(row[7]))


class RepositorioProductos:
    def __init__(self, cx):
        self.cx = cx

    def agregar(self, nombre, precio_venta, precio_compra, stock, unidad="unid", stock_minimo=UMBRAL_BAJO_STOCK):
        """Crea el producto. Si ya existe activo devuelve False; si existe inactivo lo reactiva
        con los nuevos datos y devuelve True."""
        existente = self.obtener(nombre, incluir_inactivos=True)
        if existente is not None:
            if existente.activo:
                return False
            self.cx.cursor.execute(
                "UPDATE productos SET unidad=?, precio_venta=?, precio_compra=?, stock=?, stock_minimo=?, activo=1 WHERE id=?",
                (unidad, precio_venta, precio_compra, stock, stock_minimo, existente.id))
            log.info("Producto '%s' reactivado", nombre)
            return True
        self.cx.cursor.execute(
            "INSERT INTO productos (nombre, unidad, precio_venta, precio_compra, stock, stock_minimo) VALUES (?, ?, ?, ?, ?, ?)",
            (nombre, unidad, precio_venta, precio_compra, stock, stock_minimo))
        return True

    def modificar(self, nombre_actual, nuevo_nombre, precio_venta, precio_compra, stock=None, unidad=None, stock_minimo=None):
        """Actualiza datos (y nombre) del producto. El historial no cambia porque referencia el id.
        Devuelve False si el nuevo nombre ya pertenece a otro producto."""
        try:
            campos = ["nombre=?", "precio_venta=?", "precio_compra=?"]
            valores = [nuevo_nombre, precio_venta, precio_compra]
            if stock is not None: campos.append("stock=?"); valores.append(stock)
            if unidad is not None: campos.append("unidad=?"); valores.append(unidad)
            if stock_minimo is not None: campos.append("stock_minimo=?"); valores.append(stock_minimo)
            valores.append(nombre_actual)
            self.cx.cursor.execute(f"UPDATE productos SET {', '.join(campos)} WHERE nombre=?", valores)
            return self.cx.cursor.rowcount > 0
        except sqlite3.IntegrityError:
            log.warning("No se pudo renombrar '%s' a '%s': el nombre ya existe", nombre_actual, nuevo_nombre)
            return False
        except sqlite3.Error as e:
            log.error("Error al modificar producto '%s': %s", nombre_actual, e)
            return False

    def desactivar(self, nombre):
        self.cx.cursor.execute("UPDATE productos SET activo=0 WHERE nombre=?", (nombre,))
        return self.cx.cursor.rowcount > 0

    # Alias heredado: "eliminar" un producto conserva su historial.
    eliminar = desactivar

    def reactivar(self, nombre):
        self.cx.cursor.execute("UPDATE productos SET activo=1 WHERE nombre=?", (nombre,))
        return self.cx.cursor.rowcount > 0

    def actualizar_precio_compra(self, nombre, precio_compra):
        self.cx.cursor.execute("UPDATE productos SET precio_compra=? WHERE nombre=?", (precio_compra, nombre))

    def ajustar_stock(self, nombre, cantidad, operacion):
        """operacion: 'sumar', 'restar' o 'neutro' (solo consulta).
        Devuelve el stock resultante, o None si el producto no existe o está inactivo."""
        p = self.obtener(nombre)
        if p is None:
            return 0 if operacion == "neutro" else None
        if operacion == "neutro":
            return p.stock
        nuevo = p.stock + cantidad if operacion == "sumar" else p.stock - cantidad
        self.cx.cursor.execute("UPDATE productos SET stock=? WHERE id=?", (nuevo, p.id))
        return nuevo

    def obtener(self, nombre, incluir_inactivos=False):
        filtro = "" if incluir_inactivos else " AND activo=1"
        row = self.cx.cursor.execute(f"SELECT {_COLUMNAS} FROM productos WHERE nombre=?{filtro}", (nombre,)).fetchone()
        return _fila(row) if row else None

    def obtener_por_id(self, producto_id):
        row = self.cx.cursor.execute(f"SELECT {_COLUMNAS} FROM productos WHERE id=?", (producto_id,)).fetchone()
        return _fila(row) if row else None

    def listar(self, incluir_inactivos=False):
        filtro = "" if incluir_inactivos else " WHERE activo=1"
        return [_fila(r) for r in self.cx.cursor.execute(f"SELECT {_COLUMNAS} FROM productos{filtro} ORDER BY nombre")]

    def nombres(self, incluir_inactivos=False):
        return [p.nombre for p in self.listar(incluir_inactivos)]

    def bajo_minimo(self):
        return [p for p in self.listar() if p.bajo_stock]

    def stock_total(self):
        res = self.cx.cursor.execute("SELECT SUM(stock) FROM productos WHERE activo=1").fetchone()
        return float(res[0] or 0.0)
