"""Punto de entrada: `python main.py`."""
import customtkinter as ctk

from agro.config import MODO_APARIENCIA, TEMA_COLOR
from agro.ui.app import Aplicacion


def main():
    ctk.set_appearance_mode(MODO_APARIENCIA)
    ctk.set_default_color_theme(TEMA_COLOR)
    app = Aplicacion()
    app.mainloop()


if __name__ == "__main__":
    main()
