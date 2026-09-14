"""Pantalla Fiados: cuentas por cobrar (una fila por boleta fiada) y registro de pagos."""
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from agro.servicios.formato import cantidad, moneda
from agro.servicios.operaciones import ErrorOperacion
from agro.ui import dialogos


class PantallaFiados(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self._construir()

    def _construir(self):
        ctk.CTkLabel(self, text="CUENTAS POR COBRAR (FIADOS)", font=ctk.CTkFont(size=20, weight="bold"), text_color="#D32F2F").pack(pady=20)

        container = ctk.CTkFrame(self)
        container.pack(fill="both", expand=True, padx=30, pady=10)

        cols = ("ID", "Fecha", "Cliente", "Detalle", "Total", "Pagado", "Saldo")
        self.tree_fiados = ttk.Treeview(container, columns=cols, show="headings", height=15)
        self.tree_fiados.heading("ID", text="ID"); self.tree_fiados.column("ID", width=0, stretch=tk.NO)
        self.tree_fiados.heading("Fecha", text="Fecha"); self.tree_fiados.column("Fecha", width=100)
        self.tree_fiados.heading("Cliente", text="Cliente"); self.tree_fiados.column("Cliente", width=180)
        self.tree_fiados.heading("Detalle", text="Productos"); self.tree_fiados.column("Detalle", width=280)
        self.tree_fiados.heading("Total", text="Total"); self.tree_fiados.column("Total", width=90, anchor="e")
        self.tree_fiados.heading("Pagado", text="Pagado"); self.tree_fiados.column("Pagado", width=90, anchor="e")
        self.tree_fiados.heading("Saldo", text="Saldo"); self.tree_fiados.column("Saldo", width=90, anchor="e")

        scroll = ttk.Scrollbar(container, orient="vertical", command=self.tree_fiados.yview)
        scroll.pack(side="right", fill="y")
        self.tree_fiados.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.tree_fiados.configure(yscrollcommand=scroll.set)
        self.tree_fiados.bind("<Double-1>", self.ver_historial_cliente)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="🔄 Actualizar", command=self.refrescar).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="✅ REGISTRAR PAGO", fg_color="#4CAF50", hover_color="#388E3C", height=40,
                      font=ctk.CTkFont(weight="bold"), command=self.cobrar_deuda).pack(side="left", padx=10)
        ctk.CTkLabel(btn_frame, text="(Doble clic en un cliente para ver detalles)", font=ctk.CTkFont(size=12, slant="italic")).pack(side="left", padx=20)

    def refrescar(self):
        for r in self.tree_fiados.get_children(): self.tree_fiados.delete(r)
        for b in self.app.db.boletas.deudas_pendientes():
            detalle = ", ".join(f"{l.producto} x{cantidad(l.cantidad)}" for l in b.lineas)
            self.tree_fiados.insert("", "end", values=(b.id, b.fecha, b.cliente, detalle, moneda(b.total), moneda(b.pagado), moneda(b.saldo)))

    def cobrar_deuda(self):
        sel = self.tree_fiados.selection()
        if not sel: return
        val = self.tree_fiados.item(sel[0])['values']
        boleta_id, cliente, saldo = val[0], val[2], val[6]
        if messagebox.askyesno("Cobro", f"¿{cliente} paga {saldo}?"):
            try:
                self.app.operaciones.cobrar_fiado(boleta_id, self.app.encargada_actual())
            except ErrorOperacion as e:
                return messagebox.showwarning("Atención", str(e))
            self.refrescar()
            self.app.refrescar_reportes()

    def ver_historial_cliente(self, event):
        sel = self.tree_fiados.selection()
        if not sel: return
        cliente = self.tree_fiados.item(sel[0])['values'][2]
        dialogos.abrir_historial_cliente(self.app, cliente, self.app.db.boletas.fiados_pendientes_de(cliente))
