"""Pantalla Inicio: indicadores rápidos y accesos a las dos operaciones más frecuentes.
(El 4.6 la completa con ventas de hoy y listas de reposición y fiados antiguos.)"""
import customtkinter as ctk

from agro.servicios.formato import moneda
from agro.ui.componentes import Encabezado, Tarjeta, boton_exito, boton_info
from agro.ui.tema import ESPACIO, fuente


class PantallaInicio(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self._construir()

    def _construir(self):
        m, l = ESPACIO["m"], ESPACIO["l"]
        Encabezado(self, "Inicio", "Resumen del negocio y accesos rápidos").pack(fill="x", padx=l, pady=(l, m))

        f_cards = ctk.CTkFrame(self, fg_color="transparent")
        f_cards.pack(fill="x", padx=l, pady=(0, l))
        self.card_por_cobrar = Tarjeta(f_cards, "POR COBRAR (total)", moneda(0), "aviso_suave", alto=72)
        self.card_bajo_minimo = Tarjeta(f_cards, "PRODUCTOS BAJO MÍNIMO", "0", "peligro_suave", alto=72)
        self.card_productos = Tarjeta(f_cards, "PRODUCTOS ACTIVOS", "0", "info_suave", alto=72)
        for c in (self.card_por_cobrar, self.card_bajo_minimo, self.card_productos):
            c.pack(side="left", expand=True, fill="x", padx=ESPACIO["xs"])

        ctk.CTkLabel(self, text="¿Qué quieres hacer?", font=fuente("subtitulo")).pack(anchor="w", padx=l)
        f_acciones = ctk.CTkFrame(self, fg_color="transparent")
        f_acciones.pack(fill="x", padx=l, pady=m)
        boton_exito(f_acciones, "🛒  Nueva venta", lambda: self.app.mostrar_pantalla("ventas"), height=64,
                    font=fuente("subtitulo")).pack(side="left", expand=True, fill="x", padx=(0, ESPACIO["s"]))
        boton_info(f_acciones, "🚚  Ingreso de mercadería", lambda: self.app.mostrar_pantalla("compras"), height=64,
                   font=fuente("subtitulo")).pack(side="left", expand=True, fill="x", padx=(ESPACIO["s"], 0))

    def refrescar(self):
        productos = self.app.db.productos.listar()
        bajo = [p for p in productos if p.bajo_stock]
        self.card_por_cobrar.set_valor(moneda(self.app.db.boletas.total_por_cobrar()))
        self.card_bajo_minimo.set_valor(str(len(bajo)), "peligro_suave" if bajo else "exito_suave")
        self.card_productos.set_valor(str(len(productos)))

    # Se refresca cuando cambian productos o fiados, y al entrar.
    refrescar_productos = refrescar
    refrescar_fiados = refrescar
    al_mostrar = refrescar
