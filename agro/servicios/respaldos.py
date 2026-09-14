"""Respaldos automáticos de la BD en la carpeta backups/ junto a ella, con rotación.

Los automáticos se llaman negocio_YYYYMMDD_HHMMSS.db; solo esos entran en la rotación.
Las copias previas a una migración (negocio_pre_migracion_*) y cualquier otro .db que la
usuaria deje en la carpeta se listan pero nunca se borran.
"""
import datetime
import os
import re
from dataclasses import dataclass

from agro.registro import log

CONSERVAR = 10
# Sufijo opcional _N para dos respaldos en el mismo segundo (p. ej. la red de seguridad al restaurar).
_PATRON_AUTOMATICO = re.compile(r"^negocio_(\d{8})_(\d{6})(?:_\d+)?\.db$")


@dataclass
class Respaldo:
    ruta: str
    nombre: str
    fecha: datetime.datetime          # del nombre si es automático; si no, la de modificación del archivo
    tamano: int                        # bytes
    automatico: bool


def carpeta_de(ruta_db):
    """backups/ junto a la BD (None para ':memory:')."""
    if ruta_db == ":memory:":
        return None
    return os.path.join(os.path.dirname(os.path.abspath(ruta_db)), "backups")


def _leer(carpeta, nombre):
    ruta = os.path.join(carpeta, nombre)
    m = _PATRON_AUTOMATICO.match(nombre)
    if m:
        fecha = datetime.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    else:
        fecha = datetime.datetime.fromtimestamp(os.path.getmtime(ruta))
    return Respaldo(ruta, nombre, fecha, os.path.getsize(ruta), bool(m))


def listar_respaldos(carpeta):
    """Todos los .db de la carpeta, del más reciente al más antiguo."""
    if not carpeta or not os.path.isdir(carpeta):
        return []
    respaldos = []
    for nombre in os.listdir(carpeta):
        if not nombre.lower().endswith(".db"):
            continue
        try:
            respaldos.append(_leer(carpeta, nombre))
        except (OSError, ValueError) as e:
            log.warning("Respaldo ilegible %s: %s", nombre, e)
    respaldos.sort(key=lambda r: (r.fecha, r.nombre), reverse=True)
    return respaldos


def rotar(carpeta, conservar=CONSERVAR):
    """Borra los respaldos automáticos más antiguos dejando `conservar`. Devuelve los borrados."""
    automaticos = [r for r in listar_respaldos(carpeta) if r.automatico]
    borrados = []
    for r in automaticos[conservar:]:
        try:
            os.remove(r.ruta)
            borrados.append(r.ruta)
        except OSError as e:
            log.warning("No se pudo borrar el respaldo antiguo %s: %s", r.ruta, e)
    if borrados:
        log.info("Rotación de respaldos: %d borrados", len(borrados))
    return borrados


def respaldar_automatico(db, carpeta=None, conservar=CONSERVAR, ahora=None):
    """Copia la BD a backups/negocio_YYYYMMDD_HHMMSS.db y rota. Devuelve la ruta (None con ':memory:').
    Los errores de SQLite o del disco se propagan: quien llama decide si avisar."""
    carpeta = carpeta or carpeta_de(db.db_name)
    if carpeta is None:
        return None
    os.makedirs(carpeta, exist_ok=True)
    marca = (ahora or datetime.datetime.now()).strftime("%Y%m%d_%H%M%S")
    ruta = os.path.join(carpeta, f"negocio_{marca}.db")
    n = 1
    while os.path.exists(ruta):  # nunca pisar una copia existente
        ruta = os.path.join(carpeta, f"negocio_{marca}_{n}.db")
        n += 1
    db.respaldar_a(ruta)
    rotar(carpeta, conservar)
    return ruta
