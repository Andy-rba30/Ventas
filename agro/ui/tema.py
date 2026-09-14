"""Tokens de diseño: colores semánticos, espaciado y tipografía, en un solo lugar.

Las pantallas nunca usan literales hex ni tamaños de fuente sueltos: usan
COLOR["exito"], ESPACIO["m"], fuente("titulo"), etc.
"""
from tkinter import ttk

import customtkinter as ctk

COLOR = {
    # acción principal (coincide con el tema "blue" de CustomTkinter)
    "primario": "#1F6AA5",
    "primario_hover": "#144870",
    # informativo (compras / ingresos de mercadería)
    "info": "#2196F3",
    "info_hover": "#1976D2",
    # confirmaciones, cobros, ventas al contado
    "exito": "#4CAF50",
    "exito_hover": "#388E3C",
    # advertencias, fiados, acciones reversibles
    "alerta": "#FF9800",
    "alerta_hover": "#F57C00",
    "fiado": "#FFC107",
    "fiado_hover": "#FFA000",
    # borrar, stock bajo, deudas
    "peligro": "#F44336",
    "peligro_hover": "#D32F2F",
    # fondos suaves para tarjetas y filas resaltadas (texto oscuro encima)
    "neutro": "#E0E0E0",
    "fondo_tarjeta": "#EBEBEB",
    "exito_suave": "#C8E6C9",
    "alerta_suave": "#FFCCBC",
    "info_suave": "#BBDEFB",
    "aviso_suave": "#FFF9C4",
    "peligro_suave": "#FFCDD2",
    "resaltado_suave": "#E3F2FD",
    # texto
    "texto_suave": "#6B7280",
    "texto_oscuro": "#111111",
}

ESPACIO = {"xs": 4, "s": 8, "m": 16, "l": 24, "xl": 32}

# Nombre -> kwargs de CTkFont. Las fuentes se crean bajo demanda porque CTkFont
# necesita que exista la ventana raíz.
_FUENTES = {
    "marca": dict(size=22, weight="bold"),
    "titulo": dict(size=20, weight="bold"),
    "subtitulo": dict(size=16, weight="bold"),
    "destacado": dict(size=14, weight="bold"),
    "cuerpo": dict(size=13),
    "cuerpo_negrita": dict(size=13, weight="bold"),
    "boton": dict(size=14),
    "pequeña": dict(size=11),
    "pequeña_cursiva": dict(size=11, slant="italic"),
    "nota_cursiva": dict(size=12, slant="italic"),
}

FUENTE_TABLA = ("Segoe UI", 10)
FUENTE_TABLA_NEGRITA = ("Segoe UI", 10, "bold")
FUENTE_TABLA_ENCABEZADO = ("Segoe UI", 11, "bold")
ALTO_FILA_TABLA = 32


def fuente(nombre):
    return ctk.CTkFont(**_FUENTES[nombre])


_PALETA_TABLA = {
    "claro": dict(fondo="#FFFFFF", texto="#111111", encabezado="#E0E0E0", texto_encabezado="#111111",
                  seleccion="#1F6AA5", texto_seleccion="#FFFFFF", fila_alterna="#F5F7FA"),
    "oscuro": dict(fondo="#2B2B2B", texto="#E5E5E5", encabezado="#3A3A3A", texto_encabezado="#E5E5E5",
                   seleccion="#1F6AA5", texto_seleccion="#FFFFFF", fila_alterna="#333333"),
}


def aplicar_estilo_treeview(modo=None):
    """Sincroniza el ttk.Treeview con el modo claro/oscuro de CustomTkinter.
    modo: 'Light' | 'Dark' | None (toma el actual)."""
    modo = (modo or ctk.get_appearance_mode()).lower()
    p = _PALETA_TABLA["oscuro" if modo == "dark" else "claro"]
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", font=FUENTE_TABLA, rowheight=ALTO_FILA_TABLA,
                    background=p["fondo"], fieldbackground=p["fondo"], foreground=p["texto"], borderwidth=0)
    style.configure("Treeview.Heading", font=FUENTE_TABLA_ENCABEZADO, background=p["encabezado"],
                    foreground=p["texto_encabezado"], relief="flat")
    style.map("Treeview", background=[("selected", p["seleccion"])], foreground=[("selected", p["texto_seleccion"])])
    style.map("Treeview.Heading", background=[("active", p["encabezado"])])
    return p
