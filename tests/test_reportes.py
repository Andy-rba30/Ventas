import pytest

from agro.servicios.reportes import BoletaReporte, Reporte
from tests.conftest import carrito


@pytest.fixture
def con_movimientos(con_datos, ops):
    """Septiembre 2026: venta contado (día 2), compra (día 4), fiado a JUAN (día 6), y una venta en agosto."""
    ops.registrar_venta(carrito(("UREA", 120, 2), ("FOSFATO", 90, 1)), "2026-09-02", "Administradora", "PÚBLICO GENERAL")
    ops.registrar_compra(carrito(("UREA", 95, 20)), "2026-09-04", "Rosa", "AGROSUR")
    ops.registrar_venta(carrito(("UREA", 120, 1)), "2026-09-06", "Administradora", "JUAN", fiado=True)
    ops.registrar_venta(carrito(("UREA", 120, 1)), "2026-08-20", "Administradora", "PÚBLICO GENERAL")
    return con_datos


def test_reporte_vacio_sin_datos(reportes, db):
    rep = reportes.generar(2026, "Septiembre")
    assert rep.vacio and rep.ingresos == 0 and rep.boletas == [] and rep.movimientos == []
    assert rep.balance == 0 and rep.por_cobrar_total == 0


def test_reporte_vacio_en_periodo_sin_movimientos(con_movimientos, reportes):
    rep = reportes.generar(2025, 1)
    assert rep.vacio
    assert rep.stock_total == con_movimientos.productos.stock_total()
    assert rep.por_cobrar_total == 120  # el total por cobrar no depende del periodo


def test_tarjetas_del_mes(con_movimientos, reportes):
    rep = reportes.generar(2026, "Septiembre")
    assert not rep.vacio
    assert rep.ingresos == 330          # 240 + 90; el fiado pendiente no es caja
    assert rep.gastos == 1900
    assert rep.por_cobrar == 120
    assert rep.balance == 330 - 1900
    assert rep.stock_total == 10 - 2 + 20 - 1 - 1 + 5 - 1


def test_mes_por_nombre_o_numero(con_movimientos, reportes):
    assert reportes.generar(2026, "Septiembre").ingresos == reportes.generar(2026, 9).ingresos == 330
    assert reportes.generar(2026, "Agosto").ingresos == 120


def test_boletas_agrupadas_y_ordenadas_desc(con_movimientos, reportes):
    rep = reportes.generar(2026, "Septiembre")
    assert [b.fecha for b in rep.boletas] == ["2026-09-06", "2026-09-04", "2026-09-02"]
    fiado, compra, venta = rep.boletas
    assert isinstance(venta, BoletaReporte)
    assert venta.clave == "B:1" and venta.tipo == "VENTA" and venta.total == 330 and venta.estado == "PAGADO"
    assert venta.persona == "PÚBLICO GENERAL" and venta.encargada == "Administradora"
    assert [(l.clave, l.producto, l.cantidad, l.total) for l in venta.lineas] == [("L:1", "UREA", 2, 240), ("L:2", "FOSFATO", 1, 90)]
    assert compra.tipo == "ENTRADA" and compra.persona == "AGROSUR" and compra.encargada == "Rosa" and len(compra.lineas) == 1
    assert fiado.tipo == "FIADO" and fiado.estado == "PENDIENTE" and fiado.persona == "JUAN"


def test_pago_de_fiado_cuenta_como_ingreso_y_aparece_como_cobro(con_movimientos, ops, reportes):
    id_fiado = con_movimientos.boletas.deudas_pendientes()[0].id
    pago_id = ops.cobrar_fiado(id_fiado, "Rosa", monto=50, fecha="2026-09-15")
    rep = reportes.generar(2026, 9)
    assert rep.ingresos == 380 and rep.por_cobrar == 70 and rep.por_cobrar_total == 70
    cobro = rep.boletas[0]
    assert cobro.clave == f"P:{pago_id}" and cobro.tipo == "COBRO_DEUDA" and cobro.total == 50 and cobro.persona == "JUAN"
    assert cobro.lineas[0].cantidad == 0 and cobro.lineas[0].clave == cobro.clave
    assert [b.tipo for b in rep.boletas if b.tipo == "FIADO"][0] and rep.boletas[1].estado == "PARCIAL"


def test_pago_en_otro_mes_cuenta_en_su_mes(con_movimientos, ops, reportes):
    id_fiado = con_movimientos.boletas.deudas_pendientes()[0].id
    ops.cobrar_fiado(id_fiado, "Rosa", fecha="2026-10-01")
    assert reportes.generar(2026, 9).ingresos == 330
    octubre = reportes.generar(2026, 10)
    assert octubre.ingresos == 120 and not octubre.vacio and octubre.boletas[0].tipo == "COBRO_DEUDA"
    assert reportes.generar(2026, 9).por_cobrar == 0  # el fiado de septiembre ya no tiene saldo


def test_movimientos_por_producto(con_movimientos, reportes):
    rep = reportes.generar(2026, 9)
    mov = {m.producto: m for m in rep.movimientos}
    assert mov["UREA"].salidas == 3 and mov["UREA"].entradas == 20 and mov["UREA"].cierre == 27
    assert mov["FOSFATO"].salidas == 1 and mov["FOSFATO"].entradas == 0 and mov["FOSFATO"].cierre == 4


def test_filtro_por_dia(con_movimientos, reportes):
    rep = reportes.generar(2026, 9, dia=4)
    assert rep.gastos == 1900 and rep.ingresos == 0 and len(rep.boletas) == 1
    assert reportes.generar(2026, 9, dia=30).vacio


def test_filtro_por_cliente_y_proveedor(con_movimientos, ops, reportes):
    ops.cobrar_fiado(con_movimientos.boletas.deudas_pendientes()[0].id, "Rosa", monto=20, fecha="2026-09-20")
    rep_juan = reportes.generar(2026, 9, cliente="JUAN")
    assert rep_juan.por_cobrar == 100 and rep_juan.ingresos == 20 and len(rep_juan.boletas) == 2
    rep_prov = reportes.generar(2026, 9, proveedor="AGROSUR")
    assert rep_prov.gastos == 1900 and rep_prov.ingresos == 0 and len(rep_prov.boletas) == 1
    assert reportes.generar(2026, 9, cliente="NADIE").vacio


def test_exportar_excel_tres_hojas(con_movimientos, reportes, tmp_path):
    import pandas as pd
    ruta = tmp_path / "salida.xlsx"
    assert reportes.exportar_excel(str(ruta)) and ruta.exists()
    hojas = pd.read_excel(ruta, sheet_name=None)
    assert set(hojas) == {"Boletas", "Lineas", "Pagos"} and len(hojas["Boletas"]) == 4 and len(hojas["Lineas"]) == 5


def test_exportar_excel_sin_datos_devuelve_false(reportes, tmp_path):
    ruta = tmp_path / "vacio.xlsx"
    assert reportes.exportar_excel(str(ruta)) is False and not ruta.exists()


def test_reporte_es_dataclass_con_balance():
    rep = Reporte(ingresos=10, gastos=4)
    assert rep.balance == 6 and rep.vacio
