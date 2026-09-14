"""Reporte por periodo: tarjetas, movimiento por producto y boletas con sus líneas.

Por ahora filtra con pandas sobre las extracciones de RepositorioBoletas (comportamiento
heredado); la Fase 5 lo reemplaza por consultas SQL agregadas.
"""
from dataclasses import dataclass, field

import pandas as pd

from agro.servicios.formato import MES_A_NUMERO
from agro.servicios.operaciones import clave_boleta, clave_linea, clave_pago


@dataclass
class LineaReporte:
    clave: str          # "L:<id>" o "P:<id>"
    producto: str
    cantidad: float
    total: float


@dataclass
class BoletaReporte:
    clave: str          # "B:<id>" o "P:<id>" (un pago se muestra como boleta COBRO_DEUDA)
    fecha: str
    hora: str
    tipo: str           # VENTA | FIADO | ENTRADA | COBRO_DEUDA
    total: float
    persona: str
    encargada: str
    estado: str
    lineas: list


@dataclass
class MovimientoProducto:
    producto: str
    salidas: float
    entradas: float
    cierre: float | None  # None cuando no hubo movimiento de stock en el periodo


@dataclass
class Reporte:
    ingresos: float = 0.0        # ventas al contado + pagos de fiados del periodo
    gastos: float = 0.0          # entradas de mercadería
    por_cobrar: float = 0.0      # saldo de los fiados emitidos en el periodo
    por_cobrar_total: float = 0.0  # saldo de todos los fiados, sin filtro
    stock_total: float = 0.0
    movimientos: list = field(default_factory=list)
    boletas: list = field(default_factory=list)
    vacio: bool = True

    @property
    def balance(self):
        return self.ingresos - self.gastos


def _filtrar_periodo(df, anio, mes_num, dia):
    if df.empty:
        return df
    f = pd.to_datetime(df['fecha'])
    mask = (f.dt.year == int(anio)) & (f.dt.month == mes_num)
    if dia:
        mask &= f.dt.day == int(dia)
    return df[mask].copy()


class ServicioReportes:
    def __init__(self, db):
        self.db = db

    def generar(self, anio, mes, dia=None, cliente=None, proveedor=None):
        """anio: int; mes: nombre ('Enero'...) o número 1-12; dia: int o None;
        cliente/proveedor: nombre exacto o None para todos."""
        mes_num = MES_A_NUMERO[mes] if isinstance(mes, str) else int(mes)
        rep = Reporte(stock_total=self.db.productos.stock_total(), por_cobrar_total=self.db.boletas.total_por_cobrar())

        bol = _filtrar_periodo(self.db.boletas.boletas_dataframe(), anio, mes_num, dia)
        pag = _filtrar_periodo(self.db.boletas.pagos_dataframe(), anio, mes_num, dia)
        if cliente:
            bol = bol[bol['cliente'] == cliente] if not bol.empty else bol
            pag = pag[pag['cliente'] == cliente] if not pag.empty else pag
        if proveedor:
            bol = bol[bol['proveedor'] == proveedor] if not bol.empty else bol
            pag = pag.iloc[0:0]  # los pagos no tienen proveedor
        if bol.empty and pag.empty:
            return rep

        rep.vacio = False
        lin = self.db.boletas.lineas_dataframe()
        lin = lin[lin['boleta_id'].isin(bol['id'])] if not bol.empty else lin.iloc[0:0]

        rep.ingresos = float(bol.loc[bol['tipo'] == 'VENTA', 'total'].sum()) + float(pag['monto'].sum() if not pag.empty else 0)
        rep.gastos = float(bol.loc[bol['tipo'] == 'ENTRADA', 'total'].sum())
        fiados = bol[bol['tipo'] == 'FIADO']
        rep.por_cobrar = round(float((fiados['total'] - fiados['pagado']).sum()), 2) if not fiados.empty else 0.0

        # Movimiento por producto
        for prod, df_prod in lin.groupby('producto', sort=True):
            salidas = float(df_prod.loc[df_prod['tipo'].isin(['VENTA', 'FIADO']), 'cantidad'].sum())
            entradas = float(df_prod.loc[df_prod['tipo'] == 'ENTRADA', 'cantidad'].sum())
            ultima = df_prod.sort_values(by=["fecha", "hora", "id"], ascending=False).iloc[0]['stock_resultante']
            cierre = None if pd.isna(ultima) else float(ultima)
            rep.movimientos.append(MovimientoProducto(prod, salidas, entradas, cierre))

        # Boletas (con sus líneas) y pagos (como boleta COBRO_DEUDA de una línea), de más reciente a más antigua
        boletas = []
        for _, b in bol.iterrows():
            lineas = [LineaReporte(clave_linea(int(l['id'])), l['producto'], float(l['cantidad']), float(l['subtotal']))
                      for _, l in lin[lin['boleta_id'] == b['id']].sort_values('id').iterrows()]
            boletas.append(BoletaReporte(clave_boleta(int(b['id'])), b['fecha'], b['hora'], b['tipo'], float(b['total']),
                                         b['cliente'] or b['proveedor'], b['encargada'], b['estado'], lineas))
        for _, p in pag.iterrows():
            clave = clave_pago(int(p['id']))
            boletas.append(BoletaReporte(clave, p['fecha'], p['hora'], "COBRO_DEUDA", float(p['monto']), p['cliente'], p['encargada'],
                                         "COMPLETADO", [LineaReporte(clave, f"Pago de fiado #{int(p['boleta_id'])}", 0.0, float(p['monto']))]))
        boletas.sort(key=lambda b: (b.fecha, b.hora, b.clave), reverse=True)
        rep.boletas = boletas
        return rep

    def exportar_excel(self, ruta):
        """Exporta todas las boletas, líneas y pagos en tres hojas. Devuelve False si no hay datos."""
        bol = self.db.boletas.boletas_dataframe()
        if bol.empty:
            return False
        with pd.ExcelWriter(ruta) as xw:
            bol.to_excel(xw, sheet_name="Boletas", index=False)
            self.db.boletas.lineas_dataframe().to_excel(xw, sheet_name="Lineas", index=False)
            self.db.boletas.pagos_dataframe().to_excel(xw, sheet_name="Pagos", index=False)
        return True
