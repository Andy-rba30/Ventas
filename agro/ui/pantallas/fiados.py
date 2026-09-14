"""Pantalla Fiados: cuentas por cobrar (una fila por boleta fiada) y registro de pagos."""
from tkinter import messagebox

import customtkinter as ctk

from agro.servicios.formato import cantidad, moneda
from agro.servicios.operaciones import ErrorOperacion
from agro.ui import dialogos
from agro.ui.componentes import Columna, Tabla, boton_exito, boton_secundario
from agro.ui.tema import COLOR, ESPACIO, fuente


class PantallaFiados(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self._construir()

    def _construir(self):
        s, m = ESPACIO["s"], ESPACIO["m"]
        ctk.CTkLabel(self, text="CUENTAS POR COBRAR (FIADOS)", font=fuente("titulo"), text_color=COLOR["peligro_hover"]).pack(pady=m + 4)

        self.tabla_fiados = Tabla(self, [
            Columna("id", "ID", oculta=True),
            Columna("fecha", "Fecha", 100),
            Columna("cliente", "Cliente", 180),
            Columna("detalle", "Productos", 280),
            Columna("total", "Total", 90, "e"),
            Columna("pagado", "Pagado", 90, "e"),
            Columna("saldo", "Saldo", 90, "e"),
        ], alto=15, on_doble_clic=self.ver_historial_cliente)
        self.tabla_fiados.pack(fill="both", expand=True, padx=ESPACIO["xl"] - 2, pady=s + 2)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=m + 4)
        boton_secundario(btn_frame, "🔄 Actualizar", self.refrescar).pack(side="left", padx=s + 2)
        boton_exito(btn_frame, "✅ REGISTRAR PAGO", self.cobrar_deuda, height=40, font=fuente("cuerpo_negrita")).pack(side="left", padx=s + 2)
        ctk.CTkLabel(btn_frame, text="(Doble clic en un cliente para ver detalles)", font=fuente("nota_cursiva")).pack(side="left", padx=m + 4)

    def refrescar(self):
        self.tabla_fiados.cargar(
            {"id": b.id, "fecha": b.fecha, "cliente": b.cliente,
             "detalle": ", ".join(f"{l.producto} x{cantidad(l.cantidad)}" for l in b.lineas),
             "total": moneda(b.total), "pagado": moneda(b.pagado), "saldo": moneda(b.saldo)}
            for b in self.app.db.boletas.deudas_pendientes())

    refrescar_fiados = refrescar

    def cobrar_deuda(self):
        fila = self.tabla_fiados.seleccion()
        if not fila: return
        if messagebox.askyesno("Cobro", f"¿{fila['cliente']} paga {fila['saldo']}?"):
            try:
                self.app.operaciones.cobrar_fiado(fila["id"], self.app.encargada_actual())
            except ErrorOperacion as e:
                return messagebox.showwarning("Atención", str(e))
            self.refrescar()
            self.app.refrescar_reportes()

    def ver_historial_cliente(self, event=None):
        fila = self.tabla_fiados.seleccion()
        if not fila: return
        cliente = str(fila["cliente"])
        dialogos.abrir_historial_cliente(self.app, cliente, self.app.db.boletas.fiados_pendientes_de(cliente))
