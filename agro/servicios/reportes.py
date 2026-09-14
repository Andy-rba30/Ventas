"""Reporte por periodo (tarjetas, movimiento por producto, boletas con líneas), exportación
filtrada a Excel y resumen para la pantalla Inicio.

Por ahora filtra con pandas sobre las extracciones de RepositorioBoletas (comportamiento
heredado); la Fase 5 lo reemplaza por consultas SQL agregadas.
"""
import datetime
from dataclasses import dataclass, field

import pandas as pd

from agro.servicios.formato import MES_A_NUMERO
from agro.servicios.operaciones import clave_boleta, clave_linea, clave_pago

TIPOS = ["VENTA", "FIADO", "ENTRADA", "COBRO_DEUDA"]
DIAS_FIADO_ANTIGUO = 30


@dataclass
class LineaReporte:
    clave: str          # "L:<id>" o "P:<id>"
    producto: str
    cantidad: float
    precio_unit: float
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
    unidad: str
    salidas: float
    entradas: float
    stock_actual: float
    cierre: float | None  # stock_resultante de la última línea del periodo


@dataclass
class Reporte:
    ingresos: float = 0.0          # caja: ventas al contado + pagos de fiados del periodo
    gastos: float = 0.0            # entradas de mercadería
    ventas: float = 0.0            # todo lo vendido (contado + fiado), sin importar si se cobró
    costo_vendido: float = 0.0     # cantidad vendida x precio_compra actual del producto
    por_cobrar: float = 0.0        # saldo de los fiados emitidos en el periodo
    por_cobrar_total: float = 0.0  # saldo de todos los fiados, sin filtro
    stock_total: float = 0.0
    movimientos: list = field(default_factory=list)
    boletas: list = field(default_factory=list)
    vacio: bool = True

    @property
    def balance(self):
        return self.ingresos - self.gastos

    @property
    def margen_bruto(self):
        return round(self.ventas - self.costo_vendido, 2)


@dataclass
class ResumenInicio:
    ventas_hoy: float
    boletas_hoy: int
    por_cobrar_total: float
    bajo_minimo: list          # Producto
    fiados_antiguos: list      # Deudor con más de DIAS_FIADO_ANTIGUO días


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

    # ------------------------------------------------------------------ reporte del periodo
    def generar(self, anio, mes, dia=None, cliente=None, proveedor=None, tipo=None):
        """anio: int; mes: nombre ('Enero'...) o número 1-12; dia: int o None;
        cliente/proveedor/tipo: valor exacto o None para todos."""
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
        if tipo:
            bol = bol[bol['tipo'] == tipo] if (tipo != "COBRO_DEUDA" and not bol.empty) else bol.iloc[0:0]
            if tipo != "COBRO_DEUDA":
                pag = pag.iloc[0:0]
        if bol.empty and pag.empty:
            return rep

        rep.vacio = False
        lin = self.db.boletas.lineas_dataframe()
        lin = lin[lin['boleta_id'].isin(bol['id'])] if not bol.empty else lin.iloc[0:0]

        rep.ingresos = float(bol.loc[bol['tipo'] == 'VENTA', 'total'].sum()) + float(pag['monto'].sum() if not pag.empty else 0)
        rep.gastos = float(bol.loc[bol['tipo'] == 'ENTRADA', 'total'].sum())
        rep.ventas = float(bol.loc[bol['tipo'].isin(['VENTA', 'FIADO']), 'total'].sum())
        vendidas = lin[lin['tipo'].isin(['VENTA', 'FIADO'])]
        rep.costo_vendido = round(float((vendidas['cantidad'] * vendidas['costo_unit_actual']).sum()), 2) if not vendidas.empty else 0.0
        fiados = bol[bol['tipo'] == 'FIADO']
        rep.por_cobrar = round(float((fiados['total'] - fiados['pagado']).sum()), 2) if not fiados.empty else 0.0

        # Movimiento por producto
        for prod, df_prod in lin.groupby('producto', sort=True):
            salidas = float(df_prod.loc[df_prod['tipo'].isin(['VENTA', 'FIADO']), 'cantidad'].sum())
            entradas = float(df_prod.loc[df_prod['tipo'] == 'ENTRADA', 'cantidad'].sum())
            ultima = df_prod.sort_values(by=["fecha", "hora", "id"], ascending=False).iloc[0]
            cierre = None if pd.isna(ultima['stock_resultante']) else float(ultima['stock_resultante'])
            rep.movimientos.append(MovimientoProducto(prod, ultima['unidad'], salidas, entradas, float(ultima['stock_actual']), cierre))

        # Boletas (con sus líneas) y pagos (como boleta COBRO_DEUDA de una línea), de más reciente a más antigua
        boletas = []
        for _, b in bol.iterrows():
            lineas = [LineaReporte(clave_linea(int(l['id'])), l['producto'], float(l['cantidad']), float(l['precio_unit']), float(l['subtotal']))
                      for _, l in lin[lin['boleta_id'] == b['id']].sort_values('id').iterrows()]
            boletas.append(BoletaReporte(clave_boleta(int(b['id'])), b['fecha'], b['hora'], b['tipo'], float(b['total']),
                                         b['cliente'] or b['proveedor'], b['encargada'], b['estado'], lineas))
        for _, p in pag.iterrows():
            clave = clave_pago(int(p['id']))
            boletas.append(BoletaReporte(clave, p['fecha'], p['hora'], "COBRO_DEUDA", float(p['monto']), p['cliente'], p['encargada'],
                                         "COMPLETADO", [LineaReporte(clave, f"Pago de fiado #{int(p['boleta_id'])}", 0.0, 0.0, float(p['monto']))]))
        boletas.sort(key=lambda b: (b.fecha, b.hora, b.clave), reverse=True)
        rep.boletas = boletas
        return rep

    # ------------------------------------------------------------------ exportación
    def exportar_excel(self, ruta, anio=None, mes=None, dia=None, cliente=None, proveedor=None, tipo=None):
        """Exporta las boletas del filtro (o todas si no se da periodo) en dos hojas: Boletas y Líneas.
        Devuelve False si no hay datos."""
        if anio is None or mes is None:
            # Sin periodo: todos los meses con datos (boletas o pagos).
            boletas = []
            fechas = pd.concat([self.db.boletas.boletas_dataframe()['fecha'], self.db.boletas.pagos_dataframe()['fecha']])
            for (a, m) in sorted({(f.year, f.month) for f in pd.to_datetime(fechas)}):
                boletas.extend(self.generar(a, m, cliente=cliente, proveedor=proveedor, tipo=tipo).boletas)
            boletas.sort(key=lambda b: (b.fecha, b.hora, b.clave), reverse=True)
        else:
            boletas = self.generar(anio, mes, dia, cliente, proveedor, tipo).boletas
        if not boletas:
            return False

        filas_boletas = [{"Fecha": b.fecha, "Hora": b.hora, "Tipo": b.tipo, "Cliente/Proveedor": b.persona, "Encargada": b.encargada,
                          "Total (S/.)": b.total, "Estado": b.estado, "Ref": b.clave} for b in boletas]
        filas_lineas = [{"Fecha": b.fecha, "Tipo": b.tipo, "Cliente/Proveedor": b.persona, "Producto": l.producto,
                         "Cantidad": l.cantidad, "P. Unit (S/.)": l.precio_unit, "Subtotal (S/.)": l.total, "Ref boleta": b.clave}
                        for b in boletas for l in b.lineas]
        with pd.ExcelWriter(ruta, engine="openpyxl") as xw:
            for nombre, filas in (("Boletas", filas_boletas), ("Lineas", filas_lineas)):
                df = pd.DataFrame(filas)
                df.to_excel(xw, sheet_name=nombre, index=False)
                _ajustar_hoja(xw.sheets[nombre], df)
        return True

    # ------------------------------------------------------------------ inicio
    def resumen_inicio(self, hoy=None):
        hoy = hoy or datetime.date.today()
        bol = self.db.boletas.boletas_dataframe()
        ventas_hoy, n = 0.0, 0
        if not bol.empty:
            de_hoy = bol[(bol['fecha'] == hoy.isoformat()) & (bol['tipo'].isin(['VENTA', 'FIADO']))]
            ventas_hoy, n = float(de_hoy['total'].sum()), int(len(de_hoy))
        deudores = self.db.boletas.resumen_deudores(hoy)
        return ResumenInicio(
            ventas_hoy=round(ventas_hoy, 2),
            boletas_hoy=n,
            por_cobrar_total=self.db.boletas.total_por_cobrar(),
            bajo_minimo=self.db.productos.bajo_minimo(),
            fiados_antiguos=[d for d in deudores if d.dias > DIAS_FIADO_ANTIGUO],
        )


def _ajustar_hoja(ws, df):
    """Cabeceras en negrita y ancho de columna según el contenido."""
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter
    for i, col in enumerate(df.columns, start=1):
        ws.cell(row=1, column=i).font = Font(bold=True)
        ancho = max([len(str(col))] + [len(str(v)) for v in df[col].tolist()[:500]]) + 2
        ws.column_dimensions[get_column_letter(i)].width = min(max(ancho, 8), 45)
