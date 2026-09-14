"""Consultas agregadas para reportes: totales por tipo, costo de lo vendido, movimiento por
producto, boletas y pagos de un periodo. Solo SQL; sin pandas."""
import calendar
from dataclasses import dataclass

from agro.db.boletas import Boleta, LineaBoleta, Pago, _boleta

TIPOS_BOLETA = ("VENTA", "FIADO", "ENTRADA")


@dataclass
class Filtro:
    """Periodo y filtros de un reporte. dia=None es el mes completo."""
    anio: int
    mes: int
    dia: int | None = None
    cliente: str | None = None
    proveedor: str | None = None
    tipo: str | None = None

    @property
    def desde(self):
        return f"{self.anio:04d}-{self.mes:02d}-{self.dia:02d}" if self.dia else f"{self.anio:04d}-{self.mes:02d}-01"

    @property
    def hasta(self):
        ultimo = self.dia or calendar.monthrange(self.anio, self.mes)[1]
        return f"{self.anio:04d}-{self.mes:02d}-{ultimo:02d}"

    def incluye_boletas(self):
        return self.tipo is None or self.tipo in TIPOS_BOLETA

    def incluye_pagos(self):
        return self.proveedor is None and self.tipo in (None, "COBRO_DEUDA")


class RepositorioReportes:
    def __init__(self, cx):
        self.cx = cx

    # ------------------------------------------------------------------ condiciones
    def _where_boletas(self, f):
        """Condiciones sobre el alias b (boletas), c (clientes) y pr (proveedores)."""
        cond, params = ["b.fecha BETWEEN ? AND ?"], [f.desde, f.hasta]
        if f.cliente:
            cond.append("c.nombre = ?"); params.append(f.cliente)
        if f.proveedor:
            cond.append("pr.nombre = ?"); params.append(f.proveedor)
        if f.tipo in TIPOS_BOLETA:
            cond.append("b.tipo = ?"); params.append(f.tipo)
        return " AND ".join(cond), params

    def _where_pagos(self, f):
        cond, params = ["g.fecha BETWEEN ? AND ?"], [f.desde, f.hasta]
        if f.cliente:
            cond.append("c.nombre = ?"); params.append(f.cliente)
        return " AND ".join(cond), params

    _FROM_BOLETAS = """
        FROM boletas b
        LEFT JOIN clientes c ON c.id = b.cliente_id
        LEFT JOIN proveedores pr ON pr.id = b.proveedor_id
        JOIN encargadas e ON e.id = b.encargada_id
    """

    # ------------------------------------------------------------------ agregados
    def totales_por_tipo(self, f):
        """{tipo: (suma_total, saldo_pendiente)} de las boletas del filtro."""
        if not f.incluye_boletas():
            return {}
        where, params = self._where_boletas(f)
        filas = self.cx.cursor.execute(f"""
            SELECT b.tipo, SUM(b.total),
                   SUM(b.total - COALESCE((SELECT SUM(monto) FROM pagos WHERE boleta_id = b.id), 0))
            {self._FROM_BOLETAS} WHERE {where} GROUP BY b.tipo
        """, params).fetchall()
        return {t: (round(float(tot), 2), round(float(saldo), 2)) for t, tot, saldo in filas}

    def total_pagos(self, f):
        if not f.incluye_pagos():
            return 0.0
        where, params = self._where_pagos(f)
        row = self.cx.cursor.execute(f"""
            SELECT COALESCE(SUM(g.monto), 0) FROM pagos g
            JOIN boletas b ON b.id = g.boleta_id LEFT JOIN clientes c ON c.id = b.cliente_id
            WHERE {where}
        """, params).fetchone()
        return round(float(row[0]), 2)

    def costo_vendido(self, f):
        """Cantidad vendida (VENTA y FIADO) x precio_compra actual del producto."""
        if not f.incluye_boletas() or f.tipo == "ENTRADA":
            return 0.0
        where, params = self._where_boletas(f)
        row = self.cx.cursor.execute(f"""
            SELECT COALESCE(SUM(l.cantidad * p.precio_compra), 0)
            FROM boleta_lineas l JOIN productos p ON p.id = l.producto_id
            JOIN boletas b ON b.id = l.boleta_id
            LEFT JOIN clientes c ON c.id = b.cliente_id
            LEFT JOIN proveedores pr ON pr.id = b.proveedor_id
            WHERE {where} AND b.tipo IN ('VENTA', 'FIADO')
        """, params).fetchone()
        return round(float(row[0]), 2)

    def movimiento_por_producto(self, f):
        """(producto, unidad, salidas, entradas, stock_actual, cierre) por producto con líneas en el filtro."""
        if not f.incluye_boletas():
            return []
        where, params = self._where_boletas(f)
        return self.cx.cursor.execute(f"""
            SELECT p.nombre, p.unidad,
                   SUM(CASE WHEN b.tipo IN ('VENTA', 'FIADO') THEN l.cantidad ELSE 0 END),
                   SUM(CASE WHEN b.tipo = 'ENTRADA' THEN l.cantidad ELSE 0 END),
                   p.stock,
                   (SELECT l2.stock_resultante FROM boleta_lineas l2 JOIN boletas b2 ON b2.id = l2.boleta_id
                    LEFT JOIN clientes c ON c.id = b2.cliente_id LEFT JOIN proveedores pr ON pr.id = b2.proveedor_id
                    WHERE l2.producto_id = p.id AND {where.replace('b.', 'b2.')}
                    ORDER BY b2.fecha DESC, b2.hora DESC, l2.id DESC LIMIT 1)
            FROM boleta_lineas l JOIN productos p ON p.id = l.producto_id
            JOIN boletas b ON b.id = l.boleta_id
            LEFT JOIN clientes c ON c.id = b.cliente_id
            LEFT JOIN proveedores pr ON pr.id = b.proveedor_id
            WHERE {where}
            GROUP BY p.id ORDER BY p.nombre
        """, params + params).fetchall()

    # ------------------------------------------------------------------ detalle
    def boletas_periodo(self, f):
        """Boletas del filtro con sus líneas, de la más reciente a la más antigua."""
        if not f.incluye_boletas():
            return []
        where, params = self._where_boletas(f)
        boletas = [_boleta(r) for r in self.cx.cursor.execute(f"""
            SELECT b.id, b.fecha, b.hora, b.tipo, c.nombre, pr.nombre, e.nombre, b.total, b.estado, b.notas,
                   COALESCE((SELECT SUM(monto) FROM pagos WHERE boleta_id = b.id), 0)
            {self._FROM_BOLETAS} WHERE {where}
            ORDER BY b.fecha DESC, b.hora DESC, b.id DESC
        """, params).fetchall()]
        if boletas:
            por_id = {b.id: b for b in boletas}
            marcas = ",".join("?" * len(por_id))
            for r in self.cx.cursor.execute(f"""
                SELECT l.id, l.boleta_id, l.producto_id, p.nombre, l.cantidad, l.precio_unit, l.subtotal, l.stock_resultante
                FROM boleta_lineas l JOIN productos p ON p.id = l.producto_id
                WHERE l.boleta_id IN ({marcas}) ORDER BY l.id
            """, list(por_id)):
                por_id[r[1]].lineas.append(LineaBoleta(*r))
        return boletas

    def pagos_periodo(self, f):
        """Pagos del filtro (con el nombre del cliente), del más reciente al más antiguo."""
        if not f.incluye_pagos():
            return []
        where, params = self._where_pagos(f)
        return [Pago(*r) for r in self.cx.cursor.execute(f"""
            SELECT g.id, g.boleta_id, g.fecha, g.hora, g.monto, e.nombre, g.notas, COALESCE(c.nombre, '')
            FROM pagos g JOIN boletas b ON b.id = g.boleta_id
            LEFT JOIN clientes c ON c.id = b.cliente_id
            JOIN encargadas e ON e.id = g.encargada_id
            WHERE {where} ORDER BY g.fecha DESC, g.hora DESC, g.id DESC
        """, params)]

    def meses_con_datos(self):
        """[(anio, mes)] con boletas o pagos, ordenados."""
        filas = self.cx.cursor.execute("""
            SELECT DISTINCT substr(fecha, 1, 7) FROM boletas
            UNION SELECT DISTINCT substr(fecha, 1, 7) FROM pagos ORDER BY 1
        """).fetchall()
        return [(int(m[:4]), int(m[5:7])) for (m,) in filas]

    def ventas_del_dia(self, fecha):
        """(total, número de boletas) de VENTA y FIADO emitidas en la fecha."""
        row = self.cx.cursor.execute(
            "SELECT COALESCE(SUM(total), 0), COUNT(*) FROM boletas WHERE fecha = ? AND tipo IN ('VENTA', 'FIADO')", (fecha,)).fetchone()
        return round(float(row[0]), 2), int(row[1])
