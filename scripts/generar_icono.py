"""Genera assets/icono.png (256 px) y assets/icono.ico (16-256 px) con Pillow.

Uso: python scripts/generar_icono.py   (solo hace falta al cambiar el diseño; los archivos van al repo).
Dibuja un saco de fertilizante con un brote sobre fondo verde, en los colores del tema.
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agro.ui.tema import COLOR  # noqa: E402

CARPETA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")


def dibujar(tamano=256):
    img = Image.new("RGBA", (tamano, tamano), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = tamano / 256  # unidad de diseño
    d.rounded_rectangle((8 * u, 8 * u, 248 * u, 248 * u), radius=56 * u, fill=COLOR["exito"])
    # saco (trapecio claro) con banda
    d.rounded_rectangle((64 * u, 112 * u, 192 * u, 224 * u), radius=18 * u, fill="#F5EFE0")
    d.rectangle((64 * u, 150 * u, 192 * u, 172 * u), fill=COLOR["primario"])
    d.rectangle((96 * u, 96 * u, 160 * u, 118 * u), fill="#E0D6BF")
    # brote: tallo y dos hojas
    d.line((128 * u, 100 * u, 128 * u, 44 * u), fill="#FFFFFF", width=int(10 * u))
    d.ellipse((72 * u, 44 * u, 128 * u, 84 * u), fill="#A5D6A7")
    d.ellipse((128 * u, 24 * u, 184 * u, 64 * u), fill="#A5D6A7")
    return img


def main():
    os.makedirs(CARPETA, exist_ok=True)
    grande = dibujar(256)
    grande.save(os.path.join(CARPETA, "icono.png"))
    grande.save(os.path.join(CARPETA, "icono.ico"), sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("Icono generado en", CARPETA)


if __name__ == "__main__":
    main()
