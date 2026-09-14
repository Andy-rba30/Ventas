"""Pantalla Fiados: deudores a la izquierda; a la derecha las boletas con saldo del cliente
elegido, el registro de pagos (totales o parciales) y su historial."""
from tkinter import messagebox

import customtkinter as ctk

from agro.servicios.formato import cantidad, moneda
from agro.servicios.operaciones import ErrorOperacion
from agro.ui import dialogos
from agro.ui.componentes import Columna, Encabezado, Tabla, Tarjeta, boton_exito
from agro.ui.tema import COLOR, ESPACIO, fuente

DIAS_ALERTA = 30   # un fiado con más días se resalta


class PantallaFiados(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self.cliente_sel = None
        self._construir()

    # ------------------------------------------------------------------ construcción
    def _construir(self):
        s, m, l = ESPACIO["s"], ESPACIO["m"], ESPACIO["l"]
        enc = Encabezado(self, "Cuentas por cobrar", "Clientes con fiados pendientes", color="peligro_hover")
        enc.pack(fill="x", padx=l, pady=(l, m))
        self.ent_buscar = ctk.CTkEntry(enc.acciones, placeholder_text="Buscar cliente", width=200)
        self.ent_buscar.pack(side="left", padx=(0, m))
        self.ent_buscar.bind("<KeyRelease>", lambda e: self.refrescar())
        self.card_total = Tarjeta(enc.acciones, "TOTAL POR COBRAR", moneda(0), "aviso_suave", ancho=200, alto=56)
        self.card_total.pack(side="left")

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=l, pady=(0, l))
        cuerpo.grid_columnconfigure(0, weight=11, uniform="col")
        cuerpo.grid_columnconfigure(1, weight=9, uniform="col")
        cuerpo.grid_rowconfigure(0, weight=1)

        # --- izquierda: deudores ---
        f_izq = ctk.CTkFrame(cuerpo)
        f_izq.grid(row=0, column=0, sticky="nsew", padx=(0, s))
        self.tabla_deudores = Tabla(f_izq, [
            Columna("cliente", "Cliente", 200),
            Columna("boletas", "Boletas", 60, "center", estirar=False),
            Columna("deuda", "Deuda", 95, "e", estirar=False),
            Columna("antigua", "Más antigua", 95, "center", estirar=False),
            Columna("dias", "Días", 50, "e", estirar=False),
        ], on_select=self._al_seleccionar_deudor)
        self.tabla_deudores.pack(fill="both", expand=True, padx=m, pady=m)
        ctk.CTkLabel(f_izq, text=f"En rojo: fiados con más de {DIAS_ALERTA} días", font=fuente("pequeña"),
                     text_color=COLOR["texto_suave"]).pack(anchor="w", padx=m, pady=(0, m))

        # --- derecha: detalle del cliente ---
        self.f_der = ctk.CTkFrame(cuerpo)
        self.f_der.grid(row=0, column=1, sticky="nsew", padx=(s, 0))
        self.lbl_vacio = ctk.CTkLabel(self.f_der, text="Selecciona un cliente\npara ver sus fiados y registrar pagos",
                                      font=fuente("cuerpo"), text_color=COLOR["texto_suave"], justify="center")
        self.panel = ctk.CTkFrame(self.f_der, fg_color="transparent")
        self.lbl_cliente = ctk.CTkLabel(self.panel, text="", font=fuente("subtitulo"), anchor="w")
        self.lbl_cliente.pack(fill="x", pady=(m, 0))
        self.lbl_deuda = ctk.CTkLabel(self.panel, text="", font=fuente("cuerpo"), text_color=COLOR["peligro_hover"], anchor="w")
        self.lbl_deuda.pack(fill="x", pady=(0, s))

        ctk.CTkLabel(self.panel, text="Boletas con saldo (doble clic para ver los productos)", font=fuente("cuerpo_negrita"), anchor="w").pack(fill="x")
        self.tabla_boletas = Tabla(self.panel, [
            Columna("id", "ID", oculta=True),
            Columna("fecha", "Fecha", 90, estirar=False),
            Columna("lineas", "Líneas", 55, "center", estirar=False),
            Columna("total", "Total", 85, "e"),
            Columna("pagado", "Pagado", 85, "e"),
            Columna("saldo", "Saldo", 85, "e"),
        ], alto=6, on_doble_clic=self.ver_detalle_boleta)
        self.tabla_boletas.pack(fill="x", pady=(ESPACIO["xs"], s))

        self.btn_pagar = boton_exito(self.panel, "Registrar pago", self.abrir_dialogo_pago, height=44, font=fuente("subtitulo"))
        self.btn_pagar.pack(fill="x", pady=(0, s))

        ctk.CTkLabel(self.panel, text="Historial de pagos", font=fuente("cuerpo_negrita"), anchor="w").pack(fill="x")
        self.tabla_pagos = Tabla(self.panel, [
            Columna("fecha", "Fecha", 90, estirar=False),
            Columna("boleta", "Boleta", 60, "center", estirar=False),
            Columna("monto", "Monto", 85, "e", estirar=False),
            Columna("encargada", "Encargada", 100),
            Columna("nota", "Nota", 120),
        ])
        self.tabla_pagos.pack(fill="both", expand=True, pady=(ESPACIO["xs"], m))
        self._mostrar_panel(False)

    def _mostrar_panel(self, visible):
        if visible:
            self.lbl_vacio.pack_forget()
            self.panel.pack(fill="both", expand=True, padx=ESPACIO["m"])
        else:
            self.panel.pack_forget()
            self.lbl_vacio.pack(expand=True)

    # ------------------------------------------------------------------ protocolo con la app
    def al_mostrar(self):
        self.refrescar()

    def limpiar_seleccion(self):
        self.tabla_deudores.deseleccionar()
        self.cliente_sel = None
        self._mostrar_panel(False)

    def refrescar(self):
        filtro = self.ent_buscar.get().strip().lower()
        deudores = self.app.db.boletas.resumen_deudores()
        self.tabla_deudores.cargar(
            ({"cliente": d.cliente, "boletas": d.n_boletas, "deuda": moneda(d.deuda), "antigua": d.fecha_mas_antigua,
              "dias": d.dias, "_tags": ("alerta",) if d.dias > DIAS_ALERTA else ()}
             for d in deudores if not filtro or filtro in d.cliente.lower()),
            tags=lambda f: f["_tags"])
        self.card_total.set_valor(moneda(self.app.db.boletas.total_por_cobrar()))
        if self.cliente_sel:
            if self.tabla_deudores.seleccionar_por_valor("cliente", self.cliente_sel):
                self._cargar_panel(self.cliente_sel)
            else:
                self.cliente_sel = None
                self._mostrar_panel(False)

    refrescar_fiados = refrescar

    # ------------------------------------------------------------------ cliente
    def _al_seleccionar_deudor(self, fila):
        if fila:
            self._cargar_panel(str(fila["cliente"]))

    def seleccionar_cliente(self, nombre):
        """Marca al cliente en la tabla (si tiene deuda) y muestra su panel. Devuelve True si lo encontró."""
        self.refrescar()
        if self.tabla_deudores.seleccionar_por_valor("cliente", nombre):
            self._cargar_panel(nombre)
            return True
        self.app.toast.mostrar(f"{nombre} no tiene fiados pendientes", "info")
        return False

    # Alias usado por Contactos > Ver fiados
    filtrar_cliente = seleccionar_cliente

    def _cargar_panel(self, cliente):
        self.cliente_sel = cliente
        boletas = self.app.db.boletas.deudas_pendientes(cliente)
        self.lbl_cliente.configure(text=cliente)
        self.lbl_deuda.configure(text=f"Deuda pendiente: {moneda(sum(b.saldo for b in boletas))} en {len(boletas)} boleta(s)")
        self.tabla_boletas.cargar(
            {"id": b.id, "fecha": b.fecha, "lineas": len(b.lineas), "total": moneda(b.total), "pagado": moneda(b.pagado), "saldo": moneda(b.saldo)}
            for b in boletas)
        if boletas:
            self.tabla_boletas.seleccionar_iid(self.tabla_boletas.iids()[0])  # la más antigua por defecto
        self.tabla_pagos.cargar(
            {"fecha": p.fecha, "boleta": f"#{p.boleta_id}", "monto": moneda(p.monto), "encargada": p.encargada, "nota": p.notas}
            for p in self.app.db.boletas.pagos_de_cliente(cliente))
        self.btn_pagar.configure(state="normal" if boletas else "disabled")
        self._mostrar_panel(True)

    def boleta_seleccionada(self):
        fila = self.tabla_boletas.seleccion()
        return self.app.db.boletas.obtener(int(fila["id"])) if fila else None

    # ------------------------------------------------------------------ acciones
    def abrir_dialogo_pago(self):
        b = self.boleta_seleccionada()
        if b is None:
            messagebox.showwarning("Atención", "Selecciona la boleta a la que corresponde el pago.")
            return None
        return dialogos.DialogoPago(
            self.app, b.cliente, b.saldo, self.app.db.contactos.encargadas(), self.app.encargada_actual(),
            al_confirmar=lambda monto, fecha, encargada, nota: self.registrar_pago(b.id, monto, fecha, encargada, nota))

    def registrar_pago(self, boleta_id, monto, fecha=None, encargada=None, nota=""):
        try:
            self.app.operaciones.cobrar_fiado(boleta_id, encargada or self.app.encargada_actual(), monto=monto, fecha=fecha, notas=nota)
        except ErrorOperacion as e:
            messagebox.showwarning("Atención", str(e))
            return False
        self.app.refrescar_fiados()
        self.app.refrescar_reportes()
        self.app.toast.mostrar(f"Pago de {moneda(monto)} registrado", "exito")
        return True

    def ver_detalle_boleta(self, event=None):
        b = self.boleta_seleccionada()
        if b is not None:
            dialogos.abrir_detalle_boleta(self.app, b)
