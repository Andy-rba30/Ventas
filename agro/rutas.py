"""Dónde viven los datos de la usuaria (BD, config.json, app.log, backups/, boletas/).

Nunca junto al ejecutable (Program Files no es escribible y se pierde al reinstalar):
  Windows  %APPDATA%\\AgroNegocio
  macOS    ~/Library/Application Support/AgroNegocio
  Linux    $XDG_DATA_HOME/agro-negocio  (~/.local/share/agro-negocio)
La variable de entorno AGRO_DATOS fuerza otra carpeta (uso portable en USB, pruebas).
"""
import os
import shutil
import sys

from agro.config import NOMBRE_BD
from agro.registro import log

VARIABLE_ENTORNO = "AGRO_DATOS"
# Se trasladan junto con la BD la primera vez que se arranca con la nueva ubicación.
ACOMPANANTES = ("config.json", "backups", "boletas")


def carpeta_datos(plataforma=None, entorno=None):
    entorno = os.environ if entorno is None else entorno
    plataforma = plataforma or sys.platform
    forzada = entorno.get(VARIABLE_ENTORNO)
    if forzada:
        return os.path.abspath(os.path.expanduser(forzada))
    casa = os.path.expanduser("~")
    if plataforma.startswith("win"):
        base = entorno.get("APPDATA") or os.path.join(casa, "AppData", "Roaming")
        return os.path.join(base, "AgroNegocio")
    if plataforma == "darwin":
        return os.path.join(casa, "Library", "Application Support", "AgroNegocio")
    base = entorno.get("XDG_DATA_HOME") or os.path.join(casa, ".local", "share")
    return os.path.join(base, "agro-negocio")


def ruta_bd(carpeta=None):
    """Ruta de la BD real, creando la carpeta de datos si hace falta."""
    carpeta = carpeta or carpeta_datos()
    os.makedirs(carpeta, exist_ok=True)
    return os.path.join(carpeta, NOMBRE_BD)


def carpeta_ejecutable():
    """Carpeta del .exe empaquetado; al correr desde el código, la carpeta actual."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.getcwd()


def ruta_recurso(relativa):
    """Archivo de assets/ tanto empaquetado (PyInstaller, sys._MEIPASS) como desde el código."""
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relativa)


def trasladar_datos_antiguos(origen=None, destino=None):
    """Versiones anteriores guardaban la BD junto al programa. Si allí hay una BD y en la carpeta
    de datos todavía no, la mueve con sus archivos WAL, config.json, backups/ y boletas/.
    Devuelve las rutas de destino de lo movido (vacío si no había nada que mover).
    Los errores del disco se propagan: quien llama avisa a la usuaria."""
    origen = os.path.abspath(origen or carpeta_ejecutable())
    destino = os.path.abspath(destino or carpeta_datos())
    bd_vieja = os.path.join(origen, NOMBRE_BD)
    if origen == destino or not os.path.isfile(bd_vieja) or os.path.exists(os.path.join(destino, NOMBRE_BD)):
        return []
    os.makedirs(destino, exist_ok=True)
    movidos = []
    for nombre in (NOMBRE_BD, NOMBRE_BD + "-wal", NOMBRE_BD + "-shm", *ACOMPANANTES):
        de, a = os.path.join(origen, nombre), os.path.join(destino, nombre)
        if os.path.exists(de) and not os.path.exists(a):
            shutil.move(de, a)
            movidos.append(a)
    log.info("Datos trasladados de %s a %s: %s", origen, destino, ", ".join(os.path.basename(m) for m in movidos))
    return movidos
