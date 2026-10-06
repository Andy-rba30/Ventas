"""Pantalla Inicio (por defecto al abrir): lo de hoy, lo que hay que reponer, lo que hay que cobrar."""
import customtkinter as ctk

from agro.servicios.formato import cantidad, moneda
from agro.servicios.reportes import DIAS_FIADO_ANTIGUO
from agro.ui.componentes import Columna, Encabezado, Tabla, Tarjeta, boton_exito, boton_info, boton_secundario
from agro.ui.tema import COLOR, ESPACIO, fuente


class PantallaInicio(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self._construir()

    def _construir(self):
        s, m, l = ESPACIO["s"], ESPACIO["m"], ESPACIO["l"]
        self.encabezado = Encabezado(self, "Inicio", "")
        self.encabezado.pack(fill="x", padx=l, pady=(l, m))

        f_cards = ctk.CTkFrame(self, fg_color="transparent")
        f_cards.pack(fill="x", padx=l, pady=(0, m))
        self.card_ventas_hoy = Tarjeta(f_cards, "VENTAS DE HOY", moneda(0), "exito_suave", alto=72)
        self.card_por_cobrar = Tarjeta(f_cards, "FIADOS PENDIENTES (total)", moneda(0), "aviso_suave", alto=72)
        self.card_bajo_minimo = Tarjeta(f_cards, "PRODUCTOS BAJO MÍNIMO", "0", "peligro_suave", alto=72)
        for c in (self.card_ventas_hoy, self.card_por_cobrar, self.card_bajo_minimo):
            c.pack(side="left", expand=True, fill="x", padx=ESPACIO["xs"])

        f_acciones = ctk.CTkFrame(self, fg_color="transparent")
        f_acciones.pack(fill="x", padx=l, pady=(0, m))
        boton_exito(f_acciones, "Nueva venta", lambda: self.app.mostrar_pantalla("ventas"), height=56,
                    font=fuente("subtitulo")).pack(side="left", expand=True, fill="x", padx=(0, s))
        boton_info(f_acciones, "Ingreso de mercadería", lambda: self.app.mostrar_pantalla("compras"), height=56,
                   font=fuente("subtitulo")).pack(side="left", expand=True, fill="x", padx=(s, 0))

        listas = ctk.CTkFrame(self, fg_color="transparent")
        listas.pack(fill="both", expand=True, padx=l, pady=(0, l))
        listas.grid_columnconfigure(0, weight=1, uniform="col")
        listas.grid_columnconfigure(1, weight=1, uniform="col")
        listas.grid_rowconfigure(0, weight=1)

        f_rep = ctk.CTkFrame(listas)
        f_rep.grid(row=0, column=0, sticky="nsew", padx=(0, s))
        cab = ctk.CTkFrame(f_rep, fg_color="transparent")
        cab.pack(fill="x", padx=m, pady=(m, ESPACIO["xs"]))
        ctk.CTkLabel(cab, text="Productos por reponer", font=fuente("cuerpo_negrita")).pack(side="left")
        boton_secundario(cab, "Ir a Inventario", lambda: self.app.mostrar_pantalla("productos"), height=26, font=fuente("pequeña")).pack(side="right")
        self.tabla_reponer = Tabla(f_rep, [
            Columna("producto", "Producto", 180),
            Columna("stock", "Stock", 70, "e", estirar=False),
            Columna("minimo", "Mínimo", 70, "e", estirar=False),
            Columna("unidad", "Unidad", 60, "center", estirar=False),
        ])
        self.tabla_reponer.pack(fill="both", expand=True, padx=m, pady=(0, m))

        f_fia = ctk.CTkFrame(listas)
        f_fia.grid(row=0, column=1, sticky="nsew", padx=(s, 0))
        cab2 = ctk.CTkFrame(f_fia, fg_color="transparent")
        cab2.pack(fill="x", padx=m, pady=(m, ESPACIO["xs"]))
        ctk.CTkLabel(cab2, text=f"Fiados con más de {DIAS_FIADO_ANTIGUO} días", font=fuente("cuerpo_negrita")).pack(side="left")
        boton_secundario(cab2, "Ir a Fiados", lambda: self.app.mostrar_pantalla("fiados"), height=26, font=fuente("pequeña")).pack(side="right")
        self.tabla_fiados_antiguos = Tabla(f_fia, [
            Columna("cliente", "Cliente", 180),
            Columna("deuda", "Deuda", 90, "e", estirar=False),
            Columna("dias", "Días", 60, "e", estirar=False),
        ])
        self.tabla_fiados_antiguos.pack(fill="both", expand=True, padx=m, pady=(0, m))

    def refrescar(self):
        r = self.app.reportes.resumen_inicio()
        self.encabezado.lbl_subtitulo.configure(text=f"Encargada: {self.app.encargada_actual()}")
        self.card_ventas_hoy.set_valor(f"{moneda(r.ventas_hoy)}  ({r.boletas_hoy} boleta{'s' if r.boletas_hoy != 1 else ''})")
        self.card_por_cobrar.set_valor(moneda(r.por_cobrar_total), "aviso_suave" if r.por_cobrar_total > 0 else "exito_suave")
        self.card_bajo_minimo.set_valor(str(len(r.bajo_minimo)), "peligro_suave" if r.bajo_minimo else "exito_suave")
        self.tabla_reponer.cargar(
            ({"producto": p.nombre, "stock": cantidad(p.stock), "minimo": cantidad(p.stock_minimo), "unidad": p.unidad} for p in r.bajo_minimo),
            tags=lambda f: ("alerta",))
        self.tabla_fiados_antiguos.cargar(
            ({"cliente": d.cliente, "deuda": moneda(d.deuda), "dias": d.dias} for d in r.fiados_antiguos),
            tags=lambda f: ("alerta",))

    # Se refresca cuando cambian productos o fiados, y al entrar.
    refrescar_productos = refrescar
    refrescar_fiados = refrescar
    al_mostrar = refrescar
