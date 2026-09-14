"""Historial de precios por producto: cada costo de compra pagado y cada cambio de precio de venta."""
import datetime
from dataclasses import dataclass


@dataclass
class PrecioHistorico:
    fecha: str
    hora: str
    tipo: str      # 'compra' | 'venta'
    precio: float


class RepositorioPrecios:
    def __init__(self, cx):
        self.cx = cx

    def registrar(self, producto_id, tipo, precio, fecha=None, hora=None):
        if tipo not in ("compra", "venta"):
            raise ValueError(f"Tipo de precio desconocido: {tipo}")
        fecha = fecha or datetime.date.today().isoformat()
        hora = hora or datetime.datetime.now().strftime("%H:%M:%S")
        self.cx.cursor.execute("INSERT INTO precios_historial (producto_id, fecha, hora, tipo, precio) VALUES (?, ?, ?, ?, ?)",
                               (producto_id, fecha, hora, tipo, float(precio)))
        return self.cx.cursor.lastrowid

    def historial(self, producto_id, limite=20, tipo=None):
        """Del más reciente al más antiguo."""
        sql = "SELECT fecha, hora, tipo, precio FROM precios_historial WHERE producto_id=?"
        params = [producto_id]
        if tipo:
            sql += " AND tipo=?"
            params.append(tipo)
        sql += " ORDER BY fecha DESC, hora DESC, id DESC LIMIT ?"
        params.append(limite)
        return [PrecioHistorico(*r) for r in self.cx.cursor.execute(sql, params)]

    def ultimo(self, producto_id, tipo):
        h = self.historial(producto_id, limite=1, tipo=tipo)
        return h[0] if h else None
