"""Preferencias de la usuaria en config.json, junto a la BD: apariencia, tamaño de
ventana y último respaldo. Nunca contienen datos del negocio."""
import json
import os

from agro.registro import log

VALORES_DEFECTO = {
    "apariencia": "Light",      # Light | Dark | System
    "geometria": None,          # "1200x800+100+50" tal como lo devuelve Tk
    "ultimo_respaldo": None,    # {"fecha": "2026-09-14 10:30", "ruta": "..."}
}


class Preferencias:
    def __init__(self, ruta_db):
        if ruta_db == ":memory:":
            self.ruta = None
        else:
            self.ruta = os.path.join(os.path.dirname(os.path.abspath(ruta_db)), "config.json")
        self.datos = dict(VALORES_DEFECTO)
        self.cargar()

    def cargar(self):
        if not self.ruta or not os.path.exists(self.ruta):
            return
        try:
            with open(self.ruta, encoding="utf-8") as f:
                leidos = json.load(f)
            if not isinstance(leidos, dict):
                raise ValueError("config.json no contiene un objeto")
            for clave in VALORES_DEFECTO:
                if clave in leidos:
                    self.datos[clave] = leidos[clave]
        except (OSError, ValueError) as e:
            log.warning("config.json ilegible, se usan valores por defecto: %s", e)

    def guardar(self):
        if not self.ruta:
            return
        try:
            temporal = self.ruta + ".tmp"
            with open(temporal, "w", encoding="utf-8") as f:
                json.dump(self.datos, f, ensure_ascii=False, indent=2)
            os.replace(temporal, self.ruta)
        except OSError as e:
            log.error("No se pudo guardar config.json: %s", e)

    def get(self, clave):
        return self.datos.get(clave, VALORES_DEFECTO.get(clave))

    def set(self, clave, valor):
        if clave not in VALORES_DEFECTO:
            raise KeyError(f"Preferencia desconocida: {clave}")
        self.datos[clave] = valor
        self.guardar()
