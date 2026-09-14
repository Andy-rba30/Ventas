"""Reporte por periodo: tarjetas, movimiento por producto y boletas agrupadas.

Por ahora usa pandas sobre toda la tabla de transacciones (comportamiento heredado);
la Fase 5 lo reemplaza por consultas SQL agregadas.
"""
from dataclasses import dataclass, field

import pandas as pd

from agro.servicios.formato import MES_A_NUMERO


@dataclass
class LineaBoleta:
    id: int
    producto: str
    cantidad: float
    total: float


@dataclass
class BoletaReporte:
    fecha: str
    tipo: str
    total: float
    persona: str
    encargada: str
    lineas: list


@dataclass
class MovimientoProducto:
    producto: str
    salidas: float
    entradas: float
    cierre: float | None  # None cuando no hubo movimiento de stock en el periodo


@dataclass
class Reporte:
    ingresos: float = 0.0
    gastos: float = 0.0
    por_cobrar: float = 0.0
    stock_total: float = 0.0
    movimientos: list = field(default_factory=list)
    boletas: list = field(default_factory=list)
    vacio: bool = True

    @property
    def balance(self):
        return self.ingresos - self.gastos


class ServicioReportes:
    def __init__(self, db):
        self.db = db

    def generar(self, anio, mes, dia=None, cliente=None, proveedor=None):
        """anio: int; mes: nombre ('Enero'...) o número 1-12; dia: int o None;
        cliente/proveedor: nombre exacto o None para todos."""
        mes_num = MES_A_NUMERO[mes] if isinstance(mes, str) else int(mes)
        rep = Reporte(stock_total=self.db.productos.stock_total())

        df = self.db.transacciones.como_dataframe()
        if df.empty:
            return rep

        df['fecha'] = pd.to_datetime(df['fecha'])
        df = df[(df['fecha'].dt.year == int(anio)) & (df['fecha'].dt.month == mes_num)].copy()
        if dia:
            df = df[df['fecha'].dt.day == int(dia)]
        if cliente:
            df = df[df['cliente'] == cliente]
        if proveedor:
            df = df[df['proveedor'] == proveedor]
        if df.empty:
            return rep

        rep.vacio = False
        rep.ingresos = float(df[df['tipo'].isin(['VENTA', 'COBRO_DEUDA'])]['total_dinero'].sum())
        rep.gastos = float(df[df['tipo'] == 'ENTRADA']['total_dinero'].sum())
        rep.por_cobrar = float(df[(df['tipo'] == 'FIADO') & (df['estado'] == 'PENDIENTE')]['total_dinero'].sum())

        for prod in df['producto'].unique():
            if not prod:
                continue
            df_prod = df[df['producto'] == prod]
            salidas = float(df_prod[df_prod['tipo'].isin(['VENTA', 'FIADO'])]['cantidad'].sum())
            entradas = float(df_prod[df_prod['tipo'] == 'ENTRADA']['cantidad'].sum())
            mov_stock = df_prod[df_prod['tipo'] != 'COBRO_DEUDA']
            cierre = None
            if not mov_stock.empty:
                cierre = float(mov_stock.sort_values(by=["fecha", "hora"], ascending=False).iloc[0]['stock_resultante'])
            rep.movimientos.append(MovimientoProducto(prod, salidas, entradas, cierre))

        # Agrupación heredada: una boleta = misma fecha + hora + tipo (la Fase 3 añade una tabla real).
        df['grupo_boleta'] = df['fecha'].dt.strftime("%Y-%m-%d") + " " + df['hora'].astype(str) + " | " + df['tipo']
        df_ordenado = df.sort_values(by=["fecha", "hora"], ascending=False)
        for _, group in df_ordenado.groupby('grupo_boleta', sort=False):
            cab = group.iloc[0]
            persona = cab['cliente'] if pd.notna(cab['cliente']) and cab['cliente'] != "" else cab['proveedor']
            if pd.isna(persona):
                persona = ""
            lineas = [LineaBoleta(int(r['id']), r['producto'], float(r['cantidad']), float(r['total_dinero'])) for _, r in group.iterrows()]
            rep.boletas.append(BoletaReporte(cab['fecha'].strftime("%Y-%m-%d"), cab['tipo'], float(group['total_dinero'].sum()),
                                             persona, cab['encargada'] if pd.notna(cab['encargada']) else "", lineas))
        return rep

    def exportar_excel(self, ruta):
        """Exporta toda la tabla de transacciones. Devuelve False si no hay datos."""
        df = self.db.transacciones.como_dataframe()
        if df.empty:
            return False
        df.to_excel(ruta, index=False)
        return True
