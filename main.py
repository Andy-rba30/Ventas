"""Punto de entrada: `python main.py` (o el ejecutable AgroNegocio empaquetado con PyInstaller)."""
import os
from tkinter import messagebox

import customtkinter as ctk

from agro import rutas
from agro.config import TEMA_COLOR
from agro.registro import configurar_logging, log
from agro.ui.app import Aplicacion


def main():
    # La apariencia (claro/oscuro/sistema) la aplica Aplicacion desde config.json.
    ctk.set_default_color_theme(TEMA_COLOR)
    ruta_db = rutas.ruta_bd()
    configurar_logging(ruta_db)
    aviso = None
    try:
        movidos = rutas.trasladar_datos_antiguos(destino=os.path.dirname(ruta_db))
    except OSError as e:
        log.error("No se pudieron trasladar los datos antiguos: %s", e)
        movidos, aviso = [], ("error", "No se pudieron mover los datos antiguos que estaban junto al programa:\n"
                                       f"{e}\n\nCópialos a mano a:\n{os.path.dirname(ruta_db)}")
    if movidos:
        aviso = ("info", "Tus datos ahora se guardan en:\n" + os.path.dirname(ruta_db) +
                 "\n\nSe movieron desde la carpeta del programa: " + ", ".join(os.path.basename(m) for m in movidos) +
                 ".\nLos respaldos y las boletas también se crean allí (Ajustes muestra la ruta).")
    app = Aplicacion(ruta_db)
    if aviso:
        tipo, texto = aviso
        app.after(500, lambda: (messagebox.showerror if tipo == "error" else messagebox.showinfo)("Ubicación de los datos", texto))
    app.mainloop()


if __name__ == "__main__":
    main()
