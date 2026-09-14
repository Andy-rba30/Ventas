import pytest

from agro.servicios.reportes import BoletaReporte, Reporte
from tests.conftest import carrito


@pytest.fixture
def con_movimientos(con_datos, ops):
    """Septiembre 2026: venta contado (día 2), compra (día 4), fiado a JUAN (día 6), y una venta en agosto."""
    db = con_datos
    ops.registrar_venta(carrito(("UREA", 120, 2), ("FOSFATO", 90, 1)), "2026-09-02", "Administradora", "PÚBLICO GENERAL")
    ops.registrar_compra(carrito(("UREA", 95, 20)), "2026-09-04", "Rosa", "AGROSUR")
    ops.registrar_venta(carrito(("UREA", 120, 1)), "2026-09-06", "Administradora", "JUAN", fiado=True)
    db.transacciones.registrar("2026-08-20", "VENTA", "UREA", 1, 120, "Administradora", 9, cliente="PÚBLICO GENERAL", estado="PAGADO")
    return db


def test_reporte_vacio_sin_datos(reportes, db):
    rep = reportes.generar(2026, "Septiembre")
    assert rep.vacio and rep.ingresos == 0 and rep.boletas == [] and rep.movimientos == []
    assert rep.balance == 0


def test_reporte_vacio_en_periodo_sin_movimientos(con_movimientos, reportes):
    rep = reportes.generar(2025, 1)
    assert rep.vacio and rep.stock_total == con_movimientos.productos.stock_total()


def test_tarjetas_del_mes(con_movimientos, reportes):
    rep = reportes.generar(2026, "Septiembre")
    assert not rep.vacio
    assert rep.ingresos == 330          # 240 + 90; el fiado pendiente no es caja
    assert rep.gastos == 1900
    assert rep.por_cobrar == 120
    assert rep.balance == 330 - 1900
    assert rep.stock_total == 10 - 2 + 20 - 1 + 5 - 1


def test_mes_por_nombre_o_numero(con_movimientos, reportes):
    assert reportes.generar(2026, "Septiembre").ingresos == reportes.generar(2026, 9).ingresos == 330
    assert reportes.generar(2026, "Agosto").ingresos == 120


def test_boletas_agrupadas_y_ordenadas_desc(con_movimientos, reportes):
    rep = reportes.generar(2026, "Septiembre")
    assert [b.fecha for b in rep.boletas] == ["2026-09-06", "2026-09-04", "2026-09-02"]
    venta = rep.boletas[2]
    assert isinstance(venta, BoletaReporte)
    assert venta.tipo == "VENTA" and venta.total == 330 and venta.persona == "PÚBLICO GENERAL" and venta.encargada == "Administradora"
    assert [(l.producto, l.cantidad, l.total) for l in venta.lineas] == [("UREA", 2, 240), ("FOSFATO", 1, 90)]
    compra = rep.boletas[1]
    assert compra.tipo == "ENTRADA" and compra.persona == "AGROSUR" and compra.encargada == "Rosa" and len(compra.lineas) == 1


def test_cobro_de_deuda_cuenta_como_ingreso(con_movimientos, ops, reportes):
    id_fiado = con_movimientos.transacciones.deudas_pendientes()[0][0]
    ops.cobrar_fiado(id_fiado, "Rosa", "2026-09-15")
    rep = reportes.generar(2026, 9)
    assert rep.ingresos == 450 and rep.por_cobrar == 0
    cobro = rep.boletas[0]
    assert cobro.tipo == "COBRO_DEUDA" and cobro.lineas[0].cantidad == 0 and cobro.total == 120


def test_movimientos_por_producto(con_movimientos, reportes):
    rep = reportes.generar(2026, 9)
    mov = {m.producto: m for m in rep.movimientos}
    assert mov["UREA"].salidas == 3 and mov["UREA"].entradas == 20 and mov["UREA"].cierre == 27
    assert mov["FOSFATO"].salidas == 1 and mov["FOSFATO"].entradas == 0 and mov["FOSFATO"].cierre == 4


def test_filtro_por_dia(con_movimientos, reportes):
    rep = reportes.generar(2026, 9, dia=4)
    assert rep.gastos == 1900 and rep.ingresos == 0 and len(rep.boletas) == 1
    assert reportes.generar(2026, 9, dia=30).vacio


def test_filtro_por_cliente_y_proveedor(con_movimientos, reportes):
    rep_juan = reportes.generar(2026, 9, cliente="JUAN")
    assert rep_juan.por_cobrar == 120 and rep_juan.ingresos == 0 and len(rep_juan.boletas) == 1
    rep_prov = reportes.generar(2026, 9, proveedor="AGROSUR")
    assert rep_prov.gastos == 1900 and rep_prov.ingresos == 0
    assert reportes.generar(2026, 9, cliente="NADIE").vacio


def test_exportar_excel(con_movimientos, reportes, tmp_path):
    ruta = tmp_path / "salida.xlsx"
    assert reportes.exportar_excel(str(ruta)) and ruta.exists()


def test_exportar_excel_sin_datos_devuelve_false(reportes, tmp_path):
    ruta = tmp_path / "vacio.xlsx"
    assert reportes.exportar_excel(str(ruta)) is False and not ruta.exists()


def test_reporte_es_dataclass_con_balance():
    rep = Reporte(ingresos=10, gastos=4)
    assert rep.balance == 6 and rep.vacio
