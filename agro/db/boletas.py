"""Repositorio de boletas (venta, fiado, entrada), sus líneas y los pagos de fiados."""
import datetime
import sqlite3
from dataclasses import dataclass, field

import pandas as pd

from agro.registro import log

# Códigos que devuelven eliminar_boleta / eliminar_linea / eliminar_pago
OK, NO_EXISTE, TIENE_PAGOS, ERROR = "OK", "NO_EXISTE", "TIENE_PAGOS", "ERROR"

_SQL_BOLETA = """
    SELECT b.id, b.fecha, b.hora, b.tipo, c.nombre, p.nombre, e.nombre, b.total, b.estado, b.notas,
           COALESCE((SELECT SUM(monto) FROM pagos WHERE boleta_id = b.id), 0)
    FROM boletas b
    LEFT JOIN clientes c ON c.id = b.cliente_id
    LEFT JOIN proveedores p ON p.id = b.proveedor_id
    JOIN encargadas e ON e.id = b.encargada_id
"""


@dataclass
class LineaBoleta:
    id: int
    boleta_id: int
    producto_id: int
    producto: str
    cantidad: float
    precio_unit: float
    subtotal: float
    stock_resultante: float | None


@dataclass
class Boleta:
    id: int
    fecha: str
    hora: str
    tipo: str
    cliente: str
    proveedor: str
    encargada: str
    total: float
    estado: str
    notas: str
    pagado: float
    lineas: list = field(default_factory=list)

    @property
    def saldo(self):
        return round(self.total - self.pagado, 2)

    @property
    def persona(self):
        return self.cliente or self.proveedor


@dataclass
class Pago:
    id: int
    boleta_id: int
    fecha: str
    hora: str
    monto: float
    encargada: str
    notas: str


def _boleta(row):
    return Boleta(row[0], row[1], row[2], row[3], row[4] or "", row[5] or "", row[6], float(row[7]), row[8], row[9] or "", float(row[10]))


class RepositorioBoletas:
    OK, NO_EXISTE, TIENE_PAGOS, ERROR = OK, NO_EXISTE, TIENE_PAGOS, ERROR

    def __init__(self, cx):
        self.cx = cx

    # --- creación -----------------------------------------------------------
    def crear(self, fecha, tipo, encargada_id, lineas, cliente_id=None, proveedor_id=None, hora=None, estado=None, notas=""):
        """Inserta la boleta y sus líneas. `lineas`: iterable de tuplas
        (producto_id, cantidad, precio_unit, subtotal, stock_resultante). Devuelve el id."""
        lineas = list(lineas)
        if not lineas:
            raise ValueError("Una boleta necesita al menos una línea")
        hora = hora or datetime.datetime.now().strftime("%H:%M:%S")
        estado = estado or ("PENDIENTE" if tipo == "FIADO" else "PAGADO")
        total = sum(float(l[3]) for l in lineas)
        with self.cx.transaccion():
            self.cx.cursor.execute("""
                INSERT INTO boletas (fecha, hora, tipo, cliente_id, proveedor_id, encargada_id, total, estado, notas)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (str(fecha), hora, tipo, cliente_id, proveedor_id, encargada_id, total, estado, notas))
            boleta_id = self.cx.cursor.lastrowid
            self.cx.cursor.executemany("""
                INSERT INTO boleta_lineas (boleta_id, producto_id, cantidad, precio_unit, subtotal, stock_resultante)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [(boleta_id, pid, float(cant), float(pu), float(sub), sr) for pid, cant, pu, sub, sr in lineas])
        return boleta_id

    # --- consulta -----------------------------------------------------------
    def obtener(self, boleta_id):
        row = self.cx.cursor.execute(_SQL_BOLETA + " WHERE b.id=?", (boleta_id,)).fetchone()
        if not row:
            return None
        b = _boleta(row)
        b.lineas = self.lineas_de(boleta_id)
        return b

    def lineas_de(self, boleta_id):
        return [LineaBoleta(*r) for r in self.cx.cursor.execute("""
            SELECT l.id, l.boleta_id, l.producto_id, p.nombre, l.cantidad, l.precio_unit, l.subtotal, l.stock_resultante
            FROM boleta_lineas l JOIN productos p ON p.id = l.producto_id
            WHERE l.boleta_id=? ORDER BY l.id
        """, (boleta_id,))]

    def deudas_pendientes(self, cliente=None):
        """Fiados con saldo (PENDIENTE o PARCIAL), con sus líneas, del más antiguo al más nuevo."""
        sql = _SQL_BOLETA + " WHERE b.tipo='FIADO' AND b.estado != 'PAGADO'"
        params = ()
        if cliente:
            sql += " AND c.nombre=?"
            params = (cliente,)
        sql += " ORDER BY b.fecha, b.hora, b.id"
        boletas = [_boleta(r) for r in self.cx.cursor.execute(sql, params).fetchall()]
        for b in boletas:
            b.lineas = self.lineas_de(b.id)
        return boletas

    def fiados_pendientes_de(self, cliente):
        """(fecha, producto, cantidad, subtotal) de cada línea fiada con saldo del cliente."""
        return [(b.fecha, l.producto, l.cantidad, l.subtotal) for b in self.deudas_pendientes(cliente) for l in b.lineas]

    def total_por_cobrar(self):
        row = self.cx.cursor.execute("""
            SELECT COALESCE(SUM(b.total - COALESCE((SELECT SUM(monto) FROM pagos WHERE boleta_id=b.id), 0)), 0)
            FROM boletas b WHERE b.tipo='FIADO' AND b.estado != 'PAGADO'
        """).fetchone()
        return round(float(row[0]), 2)

    # --- pagos --------------------------------------------------------------
    def registrar_pago(self, boleta_id, monto, encargada_id, fecha=None, hora=None, notas=""):
        """Registra un pago (total o parcial) de un fiado y actualiza su estado.
        Lanza ValueError si la boleta no es un fiado con saldo o el monto no es válido."""
        b = self.obtener(boleta_id)
        if b is None or b.tipo != "FIADO":
            raise ValueError("La boleta no es un fiado")
        monto = round(float(monto), 2)
        if monto <= 0:
            raise ValueError("El monto debe ser mayor a cero")
        if monto > b.saldo + 0.005:
            raise ValueError(f"El monto supera el saldo pendiente ({b.saldo:.2f})")
        fecha = fecha or datetime.date.today().strftime("%Y-%m-%d")
        hora = hora or datetime.datetime.now().strftime("%H:%M:%S")
        with self.cx.transaccion():
            self.cx.cursor.execute("INSERT INTO pagos (boleta_id, fecha, hora, monto, encargada_id, notas) VALUES (?, ?, ?, ?, ?, ?)",
                                   (boleta_id, fecha, hora, monto, encargada_id, notas))
            pago_id = self.cx.cursor.lastrowid
            self._recalcular_estado(boleta_id)
        log.info("Pago %s de S/. %.2f sobre fiado %s (%s)", pago_id, monto, boleta_id, b.cliente)
        return pago_id

    def pagos_de(self, boleta_id):
        return [Pago(*r) for r in self.cx.cursor.execute("""
            SELECT g.id, g.boleta_id, g.fecha, g.hora, g.monto, e.nombre, g.notas
            FROM pagos g JOIN encargadas e ON e.id = g.encargada_id WHERE g.boleta_id=? ORDER BY g.fecha, g.hora, g.id
        """, (boleta_id,))]

    def obtener_pago(self, pago_id):
        row = self.cx.cursor.execute("""
            SELECT g.id, g.boleta_id, g.fecha, g.hora, g.monto, e.nombre, g.notas
            FROM pagos g JOIN encargadas e ON e.id = g.encargada_id WHERE g.id=?
        """, (pago_id,)).fetchone()
        return Pago(*row) if row else None

    def _recalcular_estado(self, boleta_id):
        total, pagado = self.cx.cursor.execute("""
            SELECT total, COALESCE((SELECT SUM(monto) FROM pagos WHERE boleta_id=?), 0) FROM boletas WHERE id=?
        """, (boleta_id, boleta_id)).fetchone()
        estado = "PAGADO" if pagado >= total - 0.005 else ("PARCIAL" if pagado > 0 else "PENDIENTE")
        self.cx.cursor.execute("UPDATE boletas SET estado=? WHERE id=?", (estado, boleta_id))

    # --- eliminación con reversión ------------------------------------------
    def _revertir_stock(self, tipo, producto_id, cantidad):
        signo = "+" if tipo in ("VENTA", "FIADO") else "-"
        self.cx.cursor.execute(f"UPDATE productos SET stock = stock {signo} ? WHERE id=?", (cantidad, producto_id))

    def eliminar_boleta(self, boleta_id):
        """Borra la boleta y sus líneas devolviendo el stock. Un fiado con pagos no se borra."""
        b = self.obtener(boleta_id)
        if b is None:
            return NO_EXISTE
        if b.pagado > 0:
            return TIENE_PAGOS
        try:
            with self.cx.transaccion():
                for l in b.lineas:
                    self._revertir_stock(b.tipo, l.producto_id, l.cantidad)
                self.cx.cursor.execute("DELETE FROM boletas WHERE id=?", (boleta_id,))  # líneas en cascada
            log.info("Boleta %s (%s, %d líneas) eliminada", boleta_id, b.tipo, len(b.lineas))
            return OK
        except sqlite3.Error as e:
            log.error("Error al eliminar boleta %s: %s", boleta_id, e)
            return ERROR

    def eliminar_linea(self, linea_id):
        """Borra una línea devolviendo su stock y recalcula el total. Si la boleta queda vacía se borra."""
        row = self.cx.cursor.execute("""
            SELECT l.boleta_id, l.producto_id, l.cantidad, b.tipo FROM boleta_lineas l JOIN boletas b ON b.id = l.boleta_id WHERE l.id=?
        """, (linea_id,)).fetchone()
        if not row:
            return NO_EXISTE
        boleta_id, producto_id, cantidad, tipo = row
        if self.pagado_de(boleta_id) > 0:
            return TIENE_PAGOS
        try:
            with self.cx.transaccion():
                self._revertir_stock(tipo, producto_id, cantidad)
                self.cx.cursor.execute("DELETE FROM boleta_lineas WHERE id=?", (linea_id,))
                restantes = self.cx.cursor.execute("SELECT count(*) FROM boleta_lineas WHERE boleta_id=?", (boleta_id,)).fetchone()[0]
                if restantes == 0:
                    self.cx.cursor.execute("DELETE FROM boletas WHERE id=?", (boleta_id,))
                else:
                    self.cx.cursor.execute(
                        "UPDATE boletas SET total = (SELECT SUM(subtotal) FROM boleta_lineas WHERE boleta_id=?) WHERE id=?",
                        (boleta_id, boleta_id))
                    self._recalcular_estado(boleta_id)
            log.info("Línea %s de la boleta %s eliminada", linea_id, boleta_id)
            return OK
        except sqlite3.Error as e:
            log.error("Error al eliminar línea %s: %s", linea_id, e)
            return ERROR

    def eliminar_pago(self, pago_id):
        """Borra un pago; el fiado vuelve a PARCIAL o PENDIENTE."""
        pago = self.obtener_pago(pago_id)
        if pago is None:
            return NO_EXISTE
        try:
            with self.cx.transaccion():
                self.cx.cursor.execute("DELETE FROM pagos WHERE id=?", (pago_id,))
                self._recalcular_estado(pago.boleta_id)
            log.info("Pago %s (S/. %.2f) del fiado %s eliminado", pago_id, pago.monto, pago.boleta_id)
            return OK
        except sqlite3.Error as e:
            log.error("Error al eliminar pago %s: %s", pago_id, e)
            return ERROR

    def pagado_de(self, boleta_id):
        return float(self.cx.cursor.execute("SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE boleta_id=?", (boleta_id,)).fetchone()[0])

    # --- extracción para reportes (pandas; la Fase 5 lo pasa a SQL agregado) ---
    def boletas_dataframe(self):
        return pd.read_sql_query("""
            SELECT b.id, b.fecha, b.hora, b.tipo, b.total, b.estado, b.notas,
                   COALESCE(c.nombre, '') AS cliente, COALESCE(p.nombre, '') AS proveedor, e.nombre AS encargada,
                   COALESCE((SELECT SUM(monto) FROM pagos WHERE boleta_id = b.id), 0) AS pagado
            FROM boletas b
            LEFT JOIN clientes c ON c.id = b.cliente_id
            LEFT JOIN proveedores p ON p.id = b.proveedor_id
            JOIN encargadas e ON e.id = b.encargada_id
        """, self.cx.conn)

    def lineas_dataframe(self):
        return pd.read_sql_query("""
            SELECT l.id, l.boleta_id, b.fecha, b.hora, b.tipo, p.nombre AS producto, l.cantidad, l.precio_unit,
                   l.subtotal, l.stock_resultante, COALESCE(c.nombre, '') AS cliente, COALESCE(pr.nombre, '') AS proveedor,
                   e.nombre AS encargada, b.estado
            FROM boleta_lineas l
            JOIN boletas b ON b.id = l.boleta_id
            JOIN productos p ON p.id = l.producto_id
            LEFT JOIN clientes c ON c.id = b.cliente_id
            LEFT JOIN proveedores pr ON pr.id = b.proveedor_id
            JOIN encargadas e ON e.id = b.encargada_id
        """, self.cx.conn)

    def pagos_dataframe(self):
        return pd.read_sql_query("""
            SELECT g.id, g.boleta_id, g.fecha, g.hora, g.monto, g.notas, e.nombre AS encargada, COALESCE(c.nombre, '') AS cliente
            FROM pagos g
            JOIN boletas b ON b.id = g.boleta_id
            LEFT JOIN clientes c ON c.id = b.cliente_id
            JOIN encargadas e ON e.id = g.encargada_id
        """, self.cx.conn)
