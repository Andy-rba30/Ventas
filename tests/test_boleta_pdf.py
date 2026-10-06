"""Boleta imprimible: PDF de 80 mm por venta, fiado e ingreso."""
import datetime
import os

from agro.servicios import boleta_pdf
from tests.conftest import carrito

HOY = str(datetime.date.today())
NEGOCIO = {"nombre": "AGRO SAN JOSE", "ruc": "20123456789", "direccion": "Av. Los Alamos 123, Huancayo"}


def _pdf(db, boleta_id, ruta, negocio=NEGOCIO):
    b = db.boletas.obtener(boleta_id)
    assert boleta_pdf.generar(b, negocio, str(ruta)) == str(ruta)
    with open(ruta, "rb") as f:
        contenido = f.read()
    assert contenido.startswith(b"%PDF") and contenido.rstrip().endswith(b"%%EOF")
    return contenido


def test_venta_al_contado(ops, con_datos, tmp_path):
    bid = ops.registrar_venta(carrito(("UREA", 120, 2), ("FOSFATO", 90, 0.5)), HOY, "Administradora", "PÚBLICO GENERAL")
    pdf = _pdf(con_datos, bid, tmp_path / "sub" / "boleta.pdf")   # crea la carpeta
    for texto in (b"AGRO SAN JOSE", b"RUC 20123456789", b"Av. Los Alamos 123", b"BOLETA DE VENTA", b"N\\260 000001",
                  b"Cliente: P", b"UREA", b"FOSFATO", b"2 x S/. 120.00", b"0.5 x S/. 90.00", b"S/. 285.00", b"Gracias por su compra"):
        assert texto in pdf, texto
    assert b"Saldo pendiente" not in pdf


def test_fiado_con_pago_parcial_muestra_saldo(ops, con_datos, tmp_path):
    bid = ops.registrar_venta(carrito(("UREA", 120, 1)), HOY, "Administradora", "JUAN", fiado=True)
    ops.cobrar_fiado(bid, "Administradora", monto=20, notas="adelanto")
    pdf = _pdf(con_datos, bid, tmp_path / "fiado.pdf")
    for texto in (b"AL CR", b"Cliente: JUAN", b"Pagado", b"S/. 20.00", b"Saldo pendiente", b"S/. 100.00", b"Estado: PARCIAL"):
        assert texto in pdf, texto


def test_ingreso_de_mercaderia(ops, con_datos, tmp_path):
    bid = ops.registrar_compra(carrito(("UREA", 95, 10)), HOY, "Administradora", "AGROSUR")
    pdf = _pdf(con_datos, bid, tmp_path / "ingreso.pdf", negocio={"nombre": "", "ruc": "", "direccion": ""})
    for texto in (b"Sistema Agro-Negocio Familiar", b"INGRESO DE MERCADER", b"Proveedor: AGROSUR", b"10 x S/. 95.00", b"S/. 950.00",
                  b"Documento interno de control"):
        assert texto in pdf, texto
    assert b"RUC" not in pdf and b"Gracias" not in pdf


def test_nombre_largo_se_recorta_sin_fallar(ops, con_datos, tmp_path):
    con_datos.productos.agregar("ABONO FOLIAR CONCENTRADO PARA CULTIVOS DE ALTURA PRESENTACION GRANDE", 50, 30, 5)
    bid = ops.registrar_venta(carrito(("ABONO FOLIAR CONCENTRADO PARA CULTIVOS DE ALTURA PRESENTACION GRANDE", 50, 1)),
                              HOY, "Administradora", "PÚBLICO GENERAL")
    pdf = _pdf(con_datos, bid, tmp_path / "largo.pdf")
    assert b"ABONO FOLIAR" in pdf and b"PRESENTACION GRANDE" not in pdf


def test_ruta_para(tmp_path):
    assert boleta_pdf.ruta_para(str(tmp_path / "negocio.db"), 7) == str(tmp_path / "boletas" / "boleta_000007.pdf")
    assert boleta_pdf.ruta_para(":memory:", 12).endswith(os.path.join("boletas", "boleta_000012.pdf"))
