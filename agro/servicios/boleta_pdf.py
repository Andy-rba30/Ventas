"""Boleta imprimible: PDF tipo ticket de 80 mm de ancho generado con reportlab.

reportlab se importa solo al generar (no pesa en el arranque). Si falta, `generar` lanza
ImportError y la UI lo traduce en un aviso con la instrucción de instalación.
"""
import os

from agro.config import NOMBRE_APP
from agro.servicios.formato import cantidad, moneda

ANCHO_MM = 80
MARGEN_MM = 5
TITULOS = {
    "VENTA": "BOLETA DE VENTA",
    "FIADO": "BOLETA DE VENTA AL CRÉDITO",
    "ENTRADA": "INGRESO DE MERCADERÍA",
    "COBRO_DEUDA": "COMPROBANTE DE PAGO",
}


def ruta_para(ruta_db, boleta_id):
    """boletas/boleta_000012.pdf junto a la BD (o en la carpeta actual con ':memory:')."""
    base = os.getcwd() if ruta_db == ":memory:" else os.path.dirname(os.path.abspath(ruta_db))
    return os.path.join(base, "boletas", f"boleta_{int(boleta_id):06d}.pdf")


def _renglones(boleta, negocio):
    """Lista de (texto_izq, texto_der | None, estilo). Estilos: titulo, negrita, normal, pequeño, linea, espacio."""
    negocio = negocio or {}
    r = [(negocio.get("nombre") or NOMBRE_APP, None, "titulo")]
    if negocio.get("ruc"):
        r.append((f"RUC {negocio['ruc']}", None, "pequeño"))
    if negocio.get("direccion"):
        r.append((negocio["direccion"], None, "pequeño"))
    r += [(None, None, "linea"),
          (TITULOS.get(boleta.tipo, boleta.tipo), None, "negrita"),
          (f"N° {boleta.id:06d}", None, "normal"),
          (f"Fecha: {boleta.fecha}  {boleta.hora or ''}".rstrip(), None, "normal")]
    if boleta.cliente:
        r.append((f"Cliente: {boleta.cliente}", None, "normal"))
    if boleta.proveedor:
        r.append((f"Proveedor: {boleta.proveedor}", None, "normal"))
    r += [(f"Atendió: {boleta.encargada}", None, "normal"), (None, None, "linea")]
    for l in boleta.lineas:
        r.append((l.producto, None, "normal"))
        r.append((f"  {cantidad(l.cantidad)} x {moneda(l.precio_unit)}", moneda(l.subtotal), "normal"))
    r += [(None, None, "linea"), ("TOTAL", moneda(boleta.total), "titulo")]
    if boleta.tipo == "FIADO":
        r += [("Pagado", moneda(boleta.pagado), "normal"), ("Saldo pendiente", moneda(boleta.saldo), "negrita"),
              (f"Estado: {boleta.estado}", None, "normal")]
    if boleta.notas:
        r.append((f"Nota: {boleta.notas}", None, "pequeño"))
    r.append((None, None, "espacio"))
    r.append(("Documento interno de control" if boleta.tipo == "ENTRADA" else "¡Gracias por su compra!", None, "pequeño"))
    return r


_ESTILOS = {  # (fuente, tamaño en puntos, alto de renglón en puntos)
    "titulo": ("Helvetica-Bold", 11, 15),
    "negrita": ("Helvetica-Bold", 9, 12),
    "normal": ("Helvetica", 8.5, 11.5),
    "pequeño": ("Helvetica", 7.5, 10),
    "linea": (None, 0, 8),
    "espacio": (None, 0, 6),
}


def _recortar(pdf, texto, fuente, tamano, ancho_max):
    if pdf.stringWidth(texto, fuente, tamano) <= ancho_max:
        return texto
    while texto and pdf.stringWidth(texto + "…", fuente, tamano) > ancho_max:
        texto = texto[:-1]
    return texto + "…"


def generar(boleta, negocio, ruta):
    """Escribe el PDF en `ruta` (crea la carpeta) y devuelve la ruta."""
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    renglones = _renglones(boleta, negocio)
    ancho = ANCHO_MM * mm
    margen = MARGEN_MM * mm
    alto = sum(_ESTILOS[e][2] for _, _, e in renglones) + 2 * margen
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    pdf = canvas.Canvas(ruta, pagesize=(ancho, alto), pageCompression=0)
    pdf.setTitle(f"{TITULOS.get(boleta.tipo, boleta.tipo)} {boleta.id:06d}")
    y = alto - margen
    ancho_texto = ancho - 2 * margen
    for izq, der, estilo in renglones:
        fuente, tamano, alto_r = _ESTILOS[estilo]
        y -= alto_r
        if estilo == "linea":
            pdf.setLineWidth(0.5)
            pdf.line(margen, y + alto_r / 2, ancho - margen, y + alto_r / 2)
            continue
        if estilo == "espacio":
            continue
        pdf.setFont(fuente, tamano)
        if der is not None:
            pdf.drawRightString(ancho - margen, y, der)
            disponible = ancho_texto - pdf.stringWidth(der, fuente, tamano) - 2 * mm
        else:
            disponible = ancho_texto
        if estilo == "titulo" and der is None:
            pdf.drawCentredString(ancho / 2, y, _recortar(pdf, izq, fuente, tamano, ancho_texto))
        else:
            pdf.drawString(margen, y, _recortar(pdf, izq, fuente, tamano, disponible))
    pdf.showPage()
    pdf.save()
    return ruta
