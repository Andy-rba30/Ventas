"""Pequeñas utilidades del sistema operativo (abrir un archivo o carpeta con el programa asociado)."""
import os
import subprocess
import sys

from agro.registro import log


def abrir_archivo(ruta):
    """Abre `ruta` (archivo o carpeta) con la aplicación predeterminada. Devuelve True si se pudo lanzar."""
    ruta = os.path.abspath(ruta)
    try:
        if sys.platform.startswith("win"):
            os.startfile(ruta)  # noqa: S606 - solo existe en Windows
        elif sys.platform == "darwin":
            subprocess.Popen(["open", ruta])
        else:
            subprocess.Popen(["xdg-open", ruta], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("No se pudo abrir %s: %s", ruta, e)
        return False
