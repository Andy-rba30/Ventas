"""Punto de entrada: `python main.py`."""
import customtkinter as ctk

from agro.config import TEMA_COLOR
from agro.ui.app import Aplicacion


def main():
    # La apariencia (claro/oscuro/sistema) la aplica Aplicacion desde config.json.
    ctk.set_default_color_theme(TEMA_COLOR)
    app = Aplicacion()
    app.mainloop()


if __name__ == "__main__":
    main()
