"""Pantalla Reportes: filtros por periodo, tarjetas, resumen por producto, gráfico y detalle."""
import datetime
import calendar
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from agro.registro import log
from agro.servicios.formato import MES_A_NUMERO, MESES, cantidad, moneda


class PantallaReportes(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self.canvas_grafico = None
        self._construir()

    def _construir(self):
        f_filtro = ctk.CTkFrame(self)
        f_filtro.pack(fill="x", padx=20, pady=10)

        ahora = datetime.datetime.now()
        ctk.CTkLabel(f_filtro, text="Mes/Año:").pack(side="left", padx=5)
        self.combo_mes = ctk.CTkOptionMenu(f_filtro, values=MESES, width=100, command=self.actualizar_dias)
        self.combo_mes.set(MESES[ahora.month - 1]); self.combo_mes.pack(side="left", padx=2)
        self.combo_anio = ctk.CTkOptionMenu(f_filtro, values=[str(x) for x in range(2024, 2031)], width=80, command=self.actualizar_dias)
        self.combo_anio.set(str(ahora.year)); self.combo_anio.pack(side="left", padx=2)
        ctk.CTkLabel(f_filtro, text="Día:").pack(side="left", padx=5)
        self.combo_dia = ctk.CTkOptionMenu(f_filtro, values=["Todos"], width=70); self.combo_dia.pack(side="left", padx=2)
        self.actualizar_dias()

        ctk.CTkLabel(f_filtro, text=" | ").pack(side="left", padx=5)
        ctk.CTkLabel(f_filtro, text="Cliente:").pack(side="left", padx=2)
        self.combo_cli = ctk.CTkOptionMenu(f_filtro, values=["Todos"], width=120); self.combo_cli.pack(side="left", padx=2)
        ctk.CTkLabel(f_filtro, text="Proveedor:").pack(side="left", padx=2)
        self.combo_prov = ctk.CTkOptionMenu(f_filtro, values=["Todos"], width=120); self.combo_prov.pack(side="left", padx=2)
        ctk.CTkButton(f_filtro, text="🔎 CONSULTAR", fg_color="#673AB7", command=self.generar).pack(side="right", padx=10)

        f_cards = ctk.CTkFrame(self, fg_color="transparent")
        f_cards.pack(fill="x", padx=20, pady=5)
        fuente_card = ctk.CTkFont(size=14, weight="bold")
        self.card_ventas = ctk.CTkLabel(f_cards, text="INGRESOS (Caja)\nS/. 0.00", font=fuente_card, fg_color="#C8E6C9", text_color="black", width=200, height=60, corner_radius=8)
        self.card_ventas.pack(side="left", padx=5, expand=True)
        self.card_gastos = ctk.CTkLabel(f_cards, text="COMPRAS\nS/. 0.00", font=fuente_card, fg_color="#FFCCBC", text_color="black", width=200, height=60, corner_radius=8)
        self.card_gastos.pack(side="left", padx=5, expand=True)
        self.card_ganancia = ctk.CTkLabel(f_cards, text="CAJA REAL\nS/. 0.00", font=fuente_card, fg_color="#BBDEFB", text_color="black", width=200, height=60, corner_radius=8)
        self.card_ganancia.pack(side="left", padx=5, expand=True)
        self.card_fiados = ctk.CTkLabel(f_cards, text="POR COBRAR\nS/. 0.00", font=fuente_card, fg_color="#FFF9C4", text_color="black", width=200, height=60, corner_radius=8)
        self.card_fiados.pack(side="left", padx=5, expand=True)
        self.card_stock_total = ctk.CTkLabel(f_cards, text="STOCK TOTAL\n0", font=fuente_card, fg_color="#E0E0E0", text_color="black", width=150, height=60, corner_radius=8)
        self.card_stock_total.pack(side="left", padx=5, expand=True)

        f_mid = ctk.CTkFrame(self, fg_color="transparent")
        f_mid.pack(fill="x", padx=20, pady=(15, 0))
        f_mid.grid_columnconfigure(0, weight=1); f_mid.grid_columnconfigure(1, weight=1)

        container1 = ctk.CTkFrame(f_mid, height=180)
        container1.grid(row=0, column=0, sticky="nsew", padx=(0, 5)); container1.pack_propagate(False)
        ctk.CTkLabel(container1, text="RESUMEN DE STOCK:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(5, 0))
        self.tree_resumen = ttk.Treeview(container1, columns=("Producto", "Ventas", "Compras", "Cierre"), show="headings")
        self.tree_resumen.heading("Producto", text="Producto"); self.tree_resumen.column("Producto", width=180)
        self.tree_resumen.heading("Ventas", text="Salidas"); self.tree_resumen.column("Ventas", width=70, anchor="center")
        self.tree_resumen.heading("Compras", text="Entradas"); self.tree_resumen.column("Compras", width=70, anchor="center")
        self.tree_resumen.heading("Cierre", text="Stock Cierre"); self.tree_resumen.column("Cierre", width=80, anchor="center")
        scroll_res = ttk.Scrollbar(container1, orient="vertical", command=self.tree_resumen.yview)
        scroll_res.pack(side="right", fill="y"); self.tree_resumen.pack(side="left", fill="both", expand=True)

        self.f_grafico = ctk.CTkFrame(f_mid, height=180)
        self.f_grafico.grid(row=0, column=1, sticky="nsew", padx=(5, 0)); self.f_grafico.pack_propagate(False)

        f_toolbar = ctk.CTkFrame(self, fg_color="transparent")
        f_toolbar.pack(fill="x", padx=20, pady=(15, 0))
        ctk.CTkLabel(f_toolbar, text="DETALLE CRONOLÓGICO:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left")
        ctk.CTkButton(f_toolbar, text="🗑️ ELIMINAR SELECCIÓN", fg_color="#F44336", hover_color="#D32F2F", command=self.borrar_operacion).pack(side="right")

        container2 = ctk.CTkFrame(self)
        container2.pack(fill="both", expand=True, padx=20, pady=5)
        self.tree_mensual = ttk.Treeview(container2, columns=("ID", "Fecha", "Tipo", "Producto", "Total", "Persona", "Encargada"), show="tree headings")
        self.tree_mensual.column("#0", width=40, stretch=tk.NO, anchor="center")
        self.tree_mensual.heading("#0", text="Ver")
        self.tree_mensual.column("ID", width=0, stretch=tk.NO)
        self.tree_mensual.heading("Fecha", text="Fecha"); self.tree_mensual.column("Fecha", width=80)
        self.tree_mensual.heading("Tipo", text="Tipo"); self.tree_mensual.column("Tipo", width=100)
        self.tree_mensual.heading("Producto", text="Producto"); self.tree_mensual.column("Producto", width=150)
        self.tree_mensual.heading("Total", text="Total"); self.tree_mensual.column("Total", width=80, anchor="e")
        self.tree_mensual.heading("Persona", text="Cliente/Proveedor"); self.tree_mensual.column("Persona", width=150)
        self.tree_mensual.heading("Encargada", text="Encargada"); self.tree_mensual.column("Encargada", width=80)
        self.tree_mensual.tag_configure('boleta_total', background='#E3F2FD', font=('Segoe UI', 10, 'bold'))
        scroll_det = ttk.Scrollbar(container2, orient="vertical", command=self.tree_mensual.yview)
        scroll_det.pack(side="right", fill="y"); self.tree_mensual.pack(side="left", fill="both", expand=True)

        ctk.CTkButton(self, text="📥 Exportar Excel", fg_color="#4CAF50", hover_color="#388E3C", command=self.exportar_excel).pack(pady=10)

    # --- filtros ---
    def actualizar_dias(self, value=None):
        try:
            mes = MES_A_NUMERO[self.combo_mes.get()]
            anio = int(self.combo_anio.get())
            opciones = ["Todos"] + [str(i) for i in range(1, calendar.monthrange(anio, mes)[1] + 1)]
            sel_actual = self.combo_dia.get()
            self.combo_dia.configure(values=opciones)
            self.combo_dia.set(sel_actual if sel_actual in opciones else "Todos")
        except (KeyError, ValueError) as e:
            log.warning("No se pudo actualizar la lista de días: %s", e)

    def refrescar_contactos(self, clientes, proveedores):
        if clientes:
            self.combo_cli.configure(values=["Todos"] + clientes); self.combo_cli.set("Todos")
        if proveedores:
            self.combo_prov.configure(values=["Todos"] + proveedores); self.combo_prov.set("Todos")

    # --- reporte ---
    def generar(self):
        dia = self.combo_dia.get()
        cli = self.combo_cli.get()
        prov = self.combo_prov.get()
        rep = self.app.reportes.generar(
            int(self.combo_anio.get()), self.combo_mes.get(),
            dia=int(dia) if dia != "Todos" else None,
            cliente=cli if cli != "Todos" else None,
            proveedor=prov if prov != "Todos" else None,
        )

        for r in self.tree_mensual.get_children(): self.tree_mensual.delete(r)
        for r in self.tree_resumen.get_children(): self.tree_resumen.delete(r)
        self.card_stock_total.configure(text=f"STOCK TOTAL\n{cantidad(rep.stock_total)} unid.")
        if self.canvas_grafico:
            self.canvas_grafico.get_tk_widget().destroy()
            self.canvas_grafico = None

        self.card_ventas.configure(text=f"INGRESOS (Caja)\n{moneda(rep.ingresos)}")
        self.card_gastos.configure(text=f"COMPRAS\n{moneda(rep.gastos)}")
        self.card_fiados.configure(text=f"POR COBRAR\n{moneda(rep.por_cobrar)}")
        if rep.vacio:
            self.card_ganancia.configure(text="CAJA REAL\nS/. 0.00", fg_color="#BBDEFB")
            return
        self.card_ganancia.configure(text=f"CAJA REAL\n{moneda(rep.balance)}", fg_color="#C8E6C9" if rep.balance >= 0 else "#FFCDD2")

        for m in rep.movimientos:
            cierre = cantidad(m.cierre) if m.cierre is not None else "-"
            self.tree_resumen.insert("", "end", values=(m.producto, cantidad(m.salidas), cantidad(m.entradas), cierre))

        for b in rep.boletas:
            titulo = "🛒 TOTAL BOLETA" if len(b.lineas) > 1 else "🛒 BOLETA (1 Item)"
            padre = self.tree_mensual.insert("", "end", text="➕", values=("", b.fecha, b.tipo, titulo, moneda(b.total), b.persona, b.encargada),
                                             tags=('boleta_total',), open=False)
            for l in b.lineas:
                self.tree_mensual.insert(padre, "end", text="↳", values=(l.id, "", "", f"{l.producto} (x{cantidad(l.cantidad)})", moneda(l.total), "", ""))

        fig = Figure(figsize=(4, 2), dpi=100)
        fig.patch.set_facecolor('#EBEBEB')
        ax = fig.add_subplot(111)
        ax.bar(['Ingresos', 'Gastos'], [rep.ingresos, rep.gastos], color=['#4CAF50', '#F44336'])
        ax.set_ylabel('Soles (S/.)')
        ax.set_title('Desempeño del Periodo', fontsize=10)
        fig.tight_layout()
        self.canvas_grafico = FigureCanvasTkAgg(fig, master=self.f_grafico)
        self.canvas_grafico.draw()
        self.canvas_grafico.get_tk_widget().pack(fill="both", expand=True)

    def borrar_operacion(self):
        seleccion = self.tree_mensual.selection()
        if not seleccion: return
        if not messagebox.askyesno("Confirmar", f"¿Estás seguro de eliminar {len(seleccion)} fila(s) seleccionada(s)? "
                                                "(Si seleccionaste una boleta entera, se revertirán todos sus productos)"):
            return

        ids = set()  # evita repetir un ID si se seleccionó padre e hijo
        for iid in seleccion:
            hijos = self.tree_mensual.get_children(iid)
            filas = hijos if hijos else (iid,)
            for f in filas:
                id_tx = self.tree_mensual.item(f)['values'][0]
                if str(id_tx).isdigit(): ids.add(int(id_tx))
        if not ids: return

        bloqueados, errores = self.app.operaciones.eliminar_operaciones(sorted(ids))
        self.generar()
        self.app.refrescar_productos()
        self.app.refrescar_fiados()
        if bloqueados:
            messagebox.showwarning("Fiados ya cobrados",
                                   f"No se eliminaron {len(bloqueados)} fiado(s) porque ya fueron pagados.\n"
                                   "Primero elimina el cobro asociado (fila COBRO_DEUDA) y vuelve a intentarlo.")
        if errores:
            messagebox.showerror("Error", f"No se pudieron eliminar {len(errores)} fila(s). Revisa app.log.")

    def exportar_excel(self):
        fp = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if fp and self.app.reportes.exportar_excel(fp):
            messagebox.showinfo("Listo", "Exportado.")
