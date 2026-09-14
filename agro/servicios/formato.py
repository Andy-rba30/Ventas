"""Formato y parseo de valores: moneda, cantidades fraccionarias, fechas y meses."""
import datetime

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
MES_A_NUMERO = {nombre: i + 1 for i, nombre in enumerate(MESES)}


def moneda(valor):
    """12.5 -> 'S/. 12.50'"""
    return f"S/. {float(valor):.2f}"


def cantidad(valor):
    """1.50 -> '1.5'; 3.0 -> '3'"""
    return f"{float(valor):g}"


def parse_cantidad(texto):
    """Convierte '1.5', '0,5' o '1/2' en float. Lanza ValueError si no es válido."""
    texto = str(texto).strip().replace(',', '.')
    try:
        if '/' in texto:
            num, den = texto.split('/')
            return float(num) / float(den)
        return float(texto)
    except ZeroDivisionError:
        raise ValueError("El denominador de la fracción no puede ser cero")


def parse_dinero(texto):
    """Acepta '12.5' o 'S/. 12.50'. Lanza ValueError si no es válido."""
    return float(str(texto).replace('S/.', '').strip())


def hoy():
    return datetime.date.today().strftime("%Y-%m-%d")


def hora_actual():
    return datetime.datetime.now().strftime("%H:%M:%S")
