"""Pantalla Reportes: filtros por periodo, tarjetas, resumen por producto, gráfico y detalle."""
import calendar
import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from agro.registro import log
from agro.servicios.formato import MES_A_NUMERO, MESES, cantidad, moneda
from agro.ui.componentes import Columna, Tabla, Tarjeta, boton_exito, boton_peligro, boton_primario
from agro.ui.tema import COLOR, ESPACIO, fuente


class PantallaReportes(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self.canvas_grafico = None
        self._construir()

    def _construir(self):
        xs, s, m = ESPACIO["xs"] + 1, ESPACIO["s"] + 2, ESPACIO["m"] + 4
        f_filtro = ctk.CTkFrame(self)
        f_filtro.pack(fill="x", padx=m, pady=s)

        ahora = datetime.datetime.now()
        ctk.CTkLabel(f_filtro, text="Mes/Año:").pack(side="left", padx=xs)
        self.combo_mes = ctk.CTkOptionMenu(f_filtro, values=MESES, width=100, command=self.actualizar_dias)
        self.combo_mes.set(MESES[ahora.month - 1]); self.combo_mes.pack(side="left", padx=2)
        self.combo_anio = ctk.CTkOptionMenu(f_filtro, values=[str(x) for x in range(2024, 2031)], width=80, command=self.actualizar_dias)
        self.combo_anio.set(str(ahora.year)); self.combo_anio.pack(side="left", padx=2)
        ctk.CTkLabel(f_filtro, text="Día:").pack(side="left", padx=xs)
        self.combo_dia = ctk.CTkOptionMenu(f_filtro, values=["Todos"], width=70); self.combo_dia.pack(side="left", padx=2)
        self.actualizar_dias()

        ctk.CTkLabel(f_filtro, text=" | ").pack(side="left", padx=xs)
        ctk.CTkLabel(f_filtro, text="Cliente:").pack(side="left", padx=2)
        self.combo_cli = ctk.CTkOptionMenu(f_filtro, values=["Todos"], width=120); self.combo_cli.pack(side="left", padx=2)
        ctk.CTkLabel(f_filtro, text="Proveedor:").pack(side="left", padx=2)
        self.combo_prov = ctk.CTkOptionMenu(f_filtro, values=["Todos"], width=120); self.combo_prov.pack(side="left", padx=2)
        boton_primario(f_filtro, "🔎 CONSULTAR", self.generar).pack(side="right", padx=s)

        f_cards = ctk.CTkFrame(self, fg_color="transparent")
        f_cards.pack(fill="x", padx=m, pady=xs)
        self.card_ventas = Tarjeta(f_cards, "INGRESOS (Caja)", moneda(0), "exito_suave")
        self.card_gastos = Tarjeta(f_cards, "COMPRAS", moneda(0), "alerta_suave")
        self.card_ganancia = Tarjeta(f_cards, "CAJA REAL", moneda(0), "info_suave")
        self.card_fiados = Tarjeta(f_cards, "POR COBRAR", moneda(0), "aviso_suave")
        self.card_stock_total = Tarjeta(f_cards, "STOCK TOTAL", "0", "neutro", ancho=150)
        for card in (self.card_ventas, self.card_gastos, self.card_ganancia, self.card_fiados, self.card_stock_total):
            card.pack(side="left", padx=xs, expand=True)

        f_mid = ctk.CTkFrame(self, fg_color="transparent")
        f_mid.pack(fill="x", padx=m, pady=(ESPACIO["m"] - 1, 0))
        f_mid.grid_columnconfigure(0, weight=1); f_mid.grid_columnconfigure(1, weight=1)

        container1 = ctk.CTkFrame(f_mid, height=180)
        container1.grid(row=0, column=0, sticky="nsew", padx=(0, xs)); container1.pack_propagate(False)
        ctk.CTkLabel(container1, text="RESUMEN DE STOCK:", font=fuente("destacado")).pack(anchor="w", padx=s, pady=(xs, 0))
        self.tabla_resumen = Tabla(container1, [
            Columna("producto", "Producto", 180),
            Columna("salidas", "Salidas", 70, "center"),
            Columna("entradas", "Entradas", 70, "center"),
            Columna("cierre", "Stock Cierre", 80, "center"),
        ])
        self.tabla_resumen.pack(fill="both", expand=True)

        self.f_grafico = ctk.CTkFrame(f_mid, height=180)
        self.f_grafico.grid(row=0, column=1, sticky="nsew", padx=(xs, 0)); self.f_grafico.pack_propagate(False)

        f_toolbar = ctk.CTkFrame(self, fg_color="transparent")
        f_toolbar.pack(fill="x", padx=m, pady=(ESPACIO["m"] - 1, 0))
        ctk.CTkLabel(f_toolbar, text="DETALLE CRONOLÓGICO:", font=fuente("destacado")).pack(side="left")
        boton_peligro(f_toolbar, "🗑️ ELIMINAR SELECCIÓN", self.borrar_operacion).pack(side="right")

        self.tabla_mensual = Tabla(self, [
            Columna("clave", "ID", oculta=True),
            Columna("fecha", "Fecha", 80),
            Columna("tipo", "Tipo", 100),
            Columna("producto", "Producto", 150),
            Columna("total", "Total", 80, "e"),
            Columna("persona", "Cliente/Proveedor", 150),
            Columna("encargada", "Encargada", 80),
        ], arbol=True)
        self.tabla_mensual.pack(fill="both", expand=True, padx=m, pady=xs)

        boton_exito(self, "📥 Exportar Excel", self.exportar_excel).pack(pady=s)

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

        self.tabla_mensual.limpiar()
        self.tabla_resumen.limpiar()
        self.card_stock_total.set_valor(f"{cantidad(rep.stock_total)} unid.")
        if self.canvas_grafico:
            self.canvas_grafico.get_tk_widget().destroy()
            self.canvas_grafico = None

        self.card_ventas.set_valor(moneda(rep.ingresos))
        self.card_gastos.set_valor(moneda(rep.gastos))
        self.card_fiados.set_valor(moneda(rep.por_cobrar))
        if rep.vacio:
            self.card_ganancia.set_valor(moneda(0), "info_suave")
            return
        self.card_ganancia.set_valor(moneda(rep.balance), "exito_suave" if rep.balance >= 0 else "peligro_suave")

        self.tabla_resumen.cargar(
            {"producto": mv.producto, "salidas": cantidad(mv.salidas), "entradas": cantidad(mv.entradas),
             "cierre": cantidad(mv.cierre) if mv.cierre is not None else "-"}
            for mv in rep.movimientos)

        for b in rep.boletas:
            titulo = "🛒 TOTAL BOLETA" if len(b.lineas) > 1 else "🛒 BOLETA (1 Item)"
            tipo = f"{b.tipo} ({b.estado})" if b.tipo == "FIADO" else b.tipo
            padre = self.tabla_mensual.insertar(
                {"clave": b.clave, "fecha": b.fecha, "tipo": tipo, "producto": titulo, "total": moneda(b.total),
                 "persona": b.persona, "encargada": b.encargada}, tags=("resaltada",), texto="➕")
            for l in b.lineas:
                detalle = f"{l.producto} (x{cantidad(l.cantidad)})" if l.cantidad else l.producto
                self.tabla_mensual.insertar({"clave": l.clave, "producto": detalle, "total": moneda(l.total)}, padre=padre, texto="↳")

        fig = Figure(figsize=(4, 2), dpi=100)
        fig.patch.set_facecolor(COLOR["fondo_tarjeta"])
        ax = fig.add_subplot(111)
        ax.bar(['Ingresos', 'Gastos'], [rep.ingresos, rep.gastos], color=[COLOR["exito"], COLOR["peligro"]])
        ax.set_ylabel('Soles (S/.)')
        ax.set_title('Desempeño del Periodo', fontsize=10)
        fig.tight_layout()
        self.canvas_grafico = FigureCanvasTkAgg(fig, master=self.f_grafico)
        self.canvas_grafico.draw()
        self.canvas_grafico.get_tk_widget().pack(fill="both", expand=True)

    def borrar_operacion(self):
        seleccion = self.tabla_mensual.iids_seleccionados()
        if not seleccion: return
        if not messagebox.askyesno("Confirmar", f"¿Estás seguro de eliminar {len(seleccion)} fila(s) seleccionada(s)? "
                                                "(Si seleccionaste una boleta entera, se revertirán todos sus productos)"):
            return

        # Una boleta seleccionada entera se elimina como boleta ("B:id"); si además se marcó una de
        # sus líneas, la boleta ya la incluye. Un pago se muestra como boleta COBRO_DEUDA ("P:id").
        claves = []
        padres_seleccionados = {iid for iid in seleccion if self.tabla_mensual.hijos(iid)}
        for iid in seleccion:
            if self.tabla_mensual.padre(iid) in padres_seleccionados:
                continue
            clave = str(self.tabla_mensual.valores(iid)["clave"])
            if clave and clave not in claves:
                claves.append(clave)
        if not claves: return

        bloqueados, errores = self.app.operaciones.eliminar_operaciones(claves)
        self.generar()
        self.app.refrescar_productos()
        self.app.refrescar_fiados()
        if bloqueados:
            messagebox.showwarning("Fiados con pagos",
                                   f"No se eliminaron {len(bloqueados)} fiado(s) porque ya tienen pagos registrados.\n"
                                   "Primero elimina sus pagos (filas COBRO_DEUDA) y vuelve a intentarlo.")
        if errores:
            messagebox.showerror("Error", f"No se pudieron eliminar {len(errores)} fila(s). Revisa app.log.")

    def exportar_excel(self):
        fp = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if fp and self.app.reportes.exportar_excel(fp):
            messagebox.showinfo("Listo", "Exportado.")
