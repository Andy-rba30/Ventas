"""Pantalla Fiados: cuentas por cobrar (una fila por boleta fiada) y registro de pagos.
Admite filtrar por un cliente (desde Contactos > Ver fiados)."""
from tkinter import messagebox

import customtkinter as ctk

from agro.servicios.formato import cantidad, moneda
from agro.servicios.operaciones import ErrorOperacion
from agro.ui import dialogos
from agro.ui.componentes import Columna, Encabezado, Tabla, boton_exito, boton_secundario
from agro.ui.tema import COLOR, ESPACIO, fuente


class PantallaFiados(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self.filtro_cliente = None
        self._construir()

    def _construir(self):
        s, m, l = ESPACIO["s"], ESPACIO["m"], ESPACIO["l"]
        self.encabezado = Encabezado(self, "Cuentas por cobrar", "Fiados con saldo pendiente", color="peligro_hover")
        self.encabezado.pack(fill="x", padx=l, pady=(l, m))
        self.lbl_filtro = ctk.CTkLabel(self.encabezado.acciones, text="", font=fuente("cuerpo_negrita"))
        self.btn_quitar_filtro = boton_secundario(self.encabezado.acciones, "Ver todos", lambda: self.filtrar_cliente(None), height=28, font=fuente("pequeña"))

        self.tabla_fiados = Tabla(self, [
            Columna("id", "ID", oculta=True),
            Columna("fecha", "Fecha", 100, estirar=False),
            Columna("cliente", "Cliente", 180),
            Columna("detalle", "Productos", 280),
            Columna("total", "Total", 90, "e", estirar=False),
            Columna("pagado", "Pagado", 90, "e", estirar=False),
            Columna("saldo", "Saldo", 90, "e", estirar=False),
        ], alto=15, on_doble_clic=self.ver_historial_cliente)
        self.tabla_fiados.pack(fill="both", expand=True, padx=l, pady=(0, s))

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(s, l))
        boton_secundario(btn_frame, "Actualizar", self.refrescar).pack(side="left", padx=s)
        boton_exito(btn_frame, "REGISTRAR PAGO", self.cobrar_deuda, height=40, font=fuente("cuerpo_negrita")).pack(side="left", padx=s)
        ctk.CTkLabel(btn_frame, text="(Doble clic en un fiado para ver el detalle del cliente)", font=fuente("nota_cursiva"),
                     text_color=COLOR["texto_suave"]).pack(side="left", padx=m)

    # --- filtro por cliente ---
    def filtrar_cliente(self, nombre):
        self.filtro_cliente = nombre or None
        if self.filtro_cliente:
            self.lbl_filtro.configure(text=f"Cliente: {self.filtro_cliente}")
            self.lbl_filtro.pack(side="left", padx=(0, ESPACIO["s"]))
            self.btn_quitar_filtro.pack(side="left")
        else:
            self.lbl_filtro.pack_forget()
            self.btn_quitar_filtro.pack_forget()
        self.refrescar()

    def refrescar(self):
        deudas = self.app.db.boletas.deudas_pendientes(self.filtro_cliente)
        self.tabla_fiados.cargar(
            {"id": b.id, "fecha": b.fecha, "cliente": b.cliente,
             "detalle": ", ".join(f"{l.producto} x{cantidad(l.cantidad)}" for l in b.lineas),
             "total": moneda(b.total), "pagado": moneda(b.pagado), "saldo": moneda(b.saldo)}
            for b in deudas)
        total = sum(b.saldo for b in deudas)
        quien = f" de {self.filtro_cliente}" if self.filtro_cliente else ""
        self.encabezado.lbl_subtitulo.configure(text=f"{len(deudas)} fiado(s){quien} con saldo pendiente · Total {moneda(total)}")

    refrescar_fiados = refrescar

    def limpiar_seleccion(self):
        self.tabla_fiados.deseleccionar()

    def cobrar_deuda(self):
        fila = self.tabla_fiados.seleccion()
        if not fila: return
        if messagebox.askyesno("Cobro", f"¿{fila['cliente']} paga {fila['saldo']}?"):
            try:
                self.app.operaciones.cobrar_fiado(fila["id"], self.app.encargada_actual())
            except ErrorOperacion as e:
                return messagebox.showwarning("Atención", str(e))
            self.app.refrescar_fiados()
            self.app.refrescar_reportes()
            self.app.toast.mostrar(f"Pago de {fila['saldo']} de {fila['cliente']} registrado", "exito")

    def ver_historial_cliente(self, event=None):
        fila = self.tabla_fiados.seleccion()
        if not fila: return
        cliente = str(fila["cliente"])
        dialogos.abrir_historial_cliente(self.app, cliente, self.app.db.boletas.fiados_pendientes_de(cliente))
