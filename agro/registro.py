"""Logging de la aplicación: un solo logger 'agro' que escribe app.log junto a la BD."""
import logging
import os
from logging.handlers import RotatingFileHandler

log = logging.getLogger("agro")


def configurar_logging(ruta_db):
    """Escribe app.log junto a la BD (1 MB x 3 archivos). Idempotente."""
    if any(getattr(h, "_agro", False) for h in log.handlers):
        return
    carpeta = os.path.dirname(os.path.abspath(ruta_db)) if ruta_db != ":memory:" else os.getcwd()
    handler = RotatingFileHandler(os.path.join(carpeta, "app.log"), maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    handler._agro = True
    log.addHandler(handler)
    log.setLevel(logging.INFO)
