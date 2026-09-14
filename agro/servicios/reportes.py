"""Reporte por periodo (tarjetas, movimiento por producto, boletas con líneas), exportación
filtrada a Excel y resumen para la pantalla Inicio. Todo sobre consultas SQL agregadas de
RepositorioReportes; sin pandas."""
import datetime
from dataclasses import dataclass, field

from agro.db.reportes import Filtro
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


# Nombres alternativos usados en la documentación del plan.
ResumenPeriodo = Reporte
BoletaResumen = BoletaReporte


@dataclass
class ResumenInicio:
    ventas_hoy: float
    boletas_hoy: int
    por_cobrar_total: float
    bajo_minimo: list          # Producto
    fiados_antiguos: list      # Deudor con más de DIAS_FIADO_ANTIGUO días


def _filtro(anio, mes, dia, cliente, proveedor, tipo):
    mes_num = MES_A_NUMERO[mes] if isinstance(mes, str) else int(mes)
    return Filtro(int(anio), mes_num, int(dia) if dia else None, cliente or None, proveedor or None, tipo or None)


class ServicioReportes:
    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------ reporte del periodo
    def generar(self, anio, mes, dia=None, cliente=None, proveedor=None, tipo=None):
        """anio: int; mes: nombre ('Enero'...) o número 1-12; dia: int o None;
        cliente/proveedor/tipo: valor exacto o None para todos."""
        f = _filtro(anio, mes, dia, cliente, proveedor, tipo)
        r = self.db.reportes
        rep = Reporte(stock_total=self.db.productos.stock_total(), por_cobrar_total=self.db.boletas.total_por_cobrar())

        boletas = r.boletas_periodo(f)
        pagos = r.pagos_periodo(f)
        if not boletas and not pagos:
            return rep
        rep.vacio = False

        totales = r.totales_por_tipo(f)
        suma = lambda t: totales.get(t, (0.0, 0.0))[0]  # noqa: E731
        rep.ingresos = round(suma("VENTA") + sum(p.monto for p in pagos), 2)
        rep.gastos = suma("ENTRADA")
        rep.ventas = round(suma("VENTA") + suma("FIADO"), 2)
        rep.por_cobrar = totales.get("FIADO", (0.0, 0.0))[1]
        rep.costo_vendido = r.costo_vendido(f)

        rep.movimientos = [
            MovimientoProducto(nombre, unidad, float(salidas), float(entradas), float(stock), None if cierre is None else float(cierre))
            for nombre, unidad, salidas, entradas, stock, cierre in r.movimiento_por_producto(f)]

        lista = [
            BoletaReporte(clave_boleta(b.id), b.fecha, b.hora, b.tipo, b.total, b.persona, b.encargada, b.estado,
                          [LineaReporte(clave_linea(l.id), l.producto, l.cantidad, l.precio_unit, l.subtotal) for l in b.lineas])
            for b in boletas]
        for p in pagos:
            clave = clave_pago(p.id)
            lista.append(BoletaReporte(clave, p.fecha, p.hora, "COBRO_DEUDA", p.monto, p.cliente, p.encargada, "COMPLETADO",
                                       [LineaReporte(clave, f"Pago de fiado #{p.boleta_id}", 0.0, 0.0, p.monto)]))
        lista.sort(key=lambda b: (b.fecha, b.hora, b.clave), reverse=True)
        rep.boletas = lista
        return rep

    # ------------------------------------------------------------------ exportación
    def exportar_excel(self, ruta, anio=None, mes=None, dia=None, cliente=None, proveedor=None, tipo=None):
        """Exporta las boletas del filtro (o todas si no se da periodo) en dos hojas: Boletas y Líneas.
        Devuelve False si no hay datos."""
        from agro.servicios import exportar
        if anio is None or mes is None:
            boletas = []
            for a, m in self.db.reportes.meses_con_datos():
                boletas.extend(self.generar(a, m, cliente=cliente, proveedor=proveedor, tipo=tipo).boletas)
            boletas.sort(key=lambda b: (b.fecha, b.hora, b.clave), reverse=True)
        else:
            boletas = self.generar(anio, mes, dia, cliente, proveedor, tipo).boletas
        if not boletas:
            return False
        exportar.boletas_a_excel(ruta, boletas)
        return True

    # ------------------------------------------------------------------ inicio
    def resumen_inicio(self, hoy=None):
        hoy = hoy or datetime.date.today()
        ventas_hoy, n = self.db.reportes.ventas_del_dia(hoy.isoformat())
        deudores = self.db.boletas.resumen_deudores(hoy)
        return ResumenInicio(
            ventas_hoy=ventas_hoy,
            boletas_hoy=n,
            por_cobrar_total=self.db.boletas.total_por_cobrar(),
            bajo_minimo=self.db.productos.bajo_minimo(),
            fiados_antiguos=[d for d in deudores if d.dias > DIAS_FIADO_ANTIGUO],
        )
