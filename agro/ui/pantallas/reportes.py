"""Pantalla Reportes: selector de periodo, filtros colapsables y dos pestañas:
Resumen (tarjetas + movimiento por producto) y Movimientos (boletas con líneas, exportar, eliminar).
La consulta se ejecuta al cambiar cualquier filtro; no hay botón Consultar."""
import calendar
import datetime
from tkinter import filedialog, messagebox

import customtkinter as ctk

from agro.servicios.formato import MESES, cantidad, moneda
from agro.servicios.reportes import TIPOS
from agro.ui.componentes import (Columna, Encabezado, Tabla, Tarjeta, boton_exito, boton_peligro, boton_secundario)
from agro.ui.tema import COLOR, ESPACIO, fuente

TODOS = "Todos"


class PantallaReportes(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        hoy = datetime.date.today()
        self.anio, self.mes = hoy.year, hoy.month
        self.filtros_visibles = False
        self.reporte = None
        self._construir()

    # ------------------------------------------------------------------ construcción
    def _construir(self):
        s, m, l = ESPACIO["s"], ESPACIO["m"], ESPACIO["l"]
        enc = Encabezado(self, "Reportes", "Caja, compras, margen y movimientos del periodo")
        enc.pack(fill="x", padx=l, pady=(l, m))

        # --- barra de periodo ---
        barra = ctk.CTkFrame(self, fg_color="transparent")
        barra.pack(fill="x", padx=l, pady=(0, s))
        boton_secundario(barra, "◀", lambda: self.cambiar_mes(-1), width=36).pack(side="left")
        self.lbl_periodo = ctk.CTkLabel(barra, text="", font=fuente("subtitulo"), width=200)
        self.lbl_periodo.pack(side="left", padx=s)
        boton_secundario(barra, "▶", lambda: self.cambiar_mes(1), width=36).pack(side="left")
        boton_secundario(barra, "Hoy", self.ir_a_hoy, width=60).pack(side="left", padx=(m, 0))
        self.btn_filtros = boton_secundario(barra, "Filtros ▾", self.alternar_filtros, width=110)
        self.btn_filtros.pack(side="right")
        self.lbl_filtros_activos = ctk.CTkLabel(barra, text="", font=fuente("pequeña"), text_color=COLOR["texto_suave"])
        self.lbl_filtros_activos.pack(side="right", padx=s)

        # --- panel de filtros (colapsable) ---
        self.f_filtros = ctk.CTkFrame(self)
        fila = ctk.CTkFrame(self.f_filtros, fg_color="transparent")
        fila.pack(fill="x", padx=m, pady=s)
        ctk.CTkLabel(fila, text="Día:").pack(side="left")
        self.combo_dia = ctk.CTkOptionMenu(fila, values=[TODOS], width=80, command=lambda v: self.generar())
        self.combo_dia.pack(side="left", padx=(ESPACIO["xs"], m))
        ctk.CTkLabel(fila, text="Cliente:").pack(side="left")
        self.combo_cli = ctk.CTkOptionMenu(fila, values=[TODOS], width=150, command=lambda v: self.generar())
        self.combo_cli.pack(side="left", padx=(ESPACIO["xs"], m))
        ctk.CTkLabel(fila, text="Proveedor:").pack(side="left")
        self.combo_prov = ctk.CTkOptionMenu(fila, values=[TODOS], width=150, command=lambda v: self.generar())
        self.combo_prov.pack(side="left", padx=(ESPACIO["xs"], m))
        ctk.CTkLabel(fila, text="Tipo:").pack(side="left")
        self.combo_tipo = ctk.CTkOptionMenu(fila, values=[TODOS] + TIPOS, width=130, command=lambda v: self.generar())
        self.combo_tipo.pack(side="left", padx=(ESPACIO["xs"], m))
        boton_secundario(fila, "Limpiar filtros", self.limpiar_filtros, width=120, height=28, font=fuente("pequeña")).pack(side="right")
        self._actualizar_dias()

        # --- pestañas ---
        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=l, pady=(0, l))
        t_res = self.tabs.add("Resumen")
        t_mov = self.tabs.add("Movimientos")

        # Resumen: tarjetas
        f_cards = ctk.CTkFrame(t_res, fg_color="transparent")
        f_cards.pack(fill="x", pady=(s, m))
        self.card_ingresos = Tarjeta(f_cards, "INGRESOS (caja)", moneda(0), "exito_suave", alto=64)
        self.card_compras = Tarjeta(f_cards, "COMPRAS", moneda(0), "alerta_suave", alto=64)
        self.card_margen = Tarjeta(f_cards, "MARGEN BRUTO", moneda(0), "info_suave", alto=64)
        self.card_por_cobrar = Tarjeta(f_cards, "POR COBRAR (total)", moneda(0), "aviso_suave", alto=64)
        for c in (self.card_ingresos, self.card_compras, self.card_margen, self.card_por_cobrar):
            c.pack(side="left", expand=True, fill="x", padx=ESPACIO["xs"])
        self.lbl_balance = ctk.CTkLabel(t_res, text="", font=fuente("cuerpo"), anchor="w")
        self.lbl_balance.pack(fill="x", padx=ESPACIO["xs"])
        self.barra_caja = ctk.CTkProgressBar(t_res, height=10, progress_color=COLOR["exito"], fg_color=COLOR["peligro_suave"])
        self.barra_caja.pack(fill="x", padx=ESPACIO["xs"], pady=(ESPACIO["xs"], m))
        self.barra_caja.set(0)

        ctk.CTkLabel(t_res, text="Movimiento por producto", font=fuente("cuerpo_negrita"), anchor="w").pack(fill="x", padx=ESPACIO["xs"])
        self.tabla_resumen = Tabla(t_res, [
            Columna("producto", "Producto", 260),
            Columna("unidad", "Unidad", 60, "center", estirar=False),
            Columna("salidas", "Salidas", 90, "e", estirar=False),
            Columna("entradas", "Entradas", 90, "e", estirar=False),
            Columna("stock", "Stock actual", 100, "e", estirar=False),
        ])
        self.tabla_resumen.pack(fill="both", expand=True, pady=(ESPACIO["xs"], s))

        # Movimientos: toolbar + tabla jerárquica
        toolbar = ctk.CTkFrame(t_mov, fg_color="transparent")
        toolbar.pack(fill="x", pady=(s, ESPACIO["xs"]))
        self.lbl_movimientos = ctk.CTkLabel(toolbar, text="", font=fuente("cuerpo"), text_color=COLOR["texto_suave"])
        self.lbl_movimientos.pack(side="left")
        boton_peligro(toolbar, "Eliminar seleccionado", self.borrar_operacion, width=170, height=30).pack(side="right")
        boton_exito(toolbar, "Exportar Excel", self.exportar_excel, width=140, height=30).pack(side="right", padx=(0, s))
        boton_secundario(toolbar, "🖨 Imprimir boleta", self.imprimir_boleta, width=140, height=30).pack(side="right", padx=(0, s))
        self.tabla_mensual = Tabla(t_mov, [
            Columna("clave", "ID", oculta=True),
            Columna("fecha", "Fecha", 90, estirar=False),
            Columna("hora", "Hora", 70, "center", estirar=False),
            Columna("tipo", "Tipo", 110, estirar=False),
            Columna("persona", "Cliente / Proveedor", 180),
            Columna("encargada", "Encargada", 110, estirar=False),
            Columna("total", "Total", 95, "e", estirar=False),
            Columna("estado", "Estado", 90, "center", estirar=False),
        ], arbol=True)
        self.tabla_mensual.pack(fill="both", expand=True, pady=(0, s))
        self._actualizar_periodo()

    # ------------------------------------------------------------------ periodo y filtros
    def _actualizar_periodo(self):
        self.lbl_periodo.configure(text=f"{MESES[self.mes - 1]} {self.anio}")
        self._actualizar_dias()

    def _actualizar_dias(self):
        opciones = [TODOS] + [str(i) for i in range(1, calendar.monthrange(self.anio, self.mes)[1] + 1)]
        actual = self.combo_dia.get()
        self.combo_dia.configure(values=opciones)
        self.combo_dia.set(actual if actual in opciones else TODOS)

    def cambiar_mes(self, delta):
        mes = self.mes + delta
        self.anio += (mes - 1) // 12
        self.mes = (mes - 1) % 12 + 1
        self.combo_dia.set(TODOS)
        self._actualizar_periodo()
        self.generar()

    def ir_a_hoy(self):
        hoy = datetime.date.today()
        self.anio, self.mes = hoy.year, hoy.month
        self.combo_dia.set(TODOS)
        self._actualizar_periodo()
        self.generar()

    def alternar_filtros(self):
        self.filtros_visibles = not self.filtros_visibles
        if self.filtros_visibles:
            self.f_filtros.pack(fill="x", padx=ESPACIO["l"], pady=(0, ESPACIO["s"]), before=self.tabs)
            self.btn_filtros.configure(text="Filtros ▴")
        else:
            self.f_filtros.pack_forget()
            self.btn_filtros.configure(text="Filtros ▾")

    def limpiar_filtros(self):
        for combo in (self.combo_dia, self.combo_cli, self.combo_prov, self.combo_tipo):
            combo.set(TODOS)
        self.generar()

    def filtros(self):
        """Filtros actuales como dict listo para ServicioReportes.generar."""
        def valor(combo):
            v = combo.get()
            return None if v == TODOS else v
        dia = valor(self.combo_dia)
        return dict(dia=int(dia) if dia else None, cliente=valor(self.combo_cli), proveedor=valor(self.combo_prov), tipo=valor(self.combo_tipo))

    def refrescar_contactos(self, clientes, proveedores):
        for combo, lista in ((self.combo_cli, clientes), (self.combo_prov, proveedores)):
            actual = combo.get()
            combo.configure(values=[TODOS] + list(lista or []))
            combo.set(actual if actual in (lista or []) else TODOS)

    def al_mostrar(self):
        self.generar()

    def limpiar_seleccion(self):
        self.tabla_mensual.deseleccionar()
        self.tabla_resumen.deseleccionar()

    # ------------------------------------------------------------------ reporte
    def generar(self):
        f = self.filtros()
        rep = self.app.reportes.generar(self.anio, self.mes, **f)
        self.reporte = rep
        activos = [t for t, v in (("día", f["dia"]), ("cliente", f["cliente"]), ("proveedor", f["proveedor"]), ("tipo", f["tipo"])) if v]
        self.lbl_filtros_activos.configure(text=("Filtrando por " + ", ".join(activos)) if activos else "")

        self.card_ingresos.set_valor(moneda(rep.ingresos))
        self.card_compras.set_valor(moneda(rep.gastos))
        self.card_margen.set_valor(moneda(rep.margen_bruto), "exito_suave" if rep.margen_bruto >= 0 else "peligro_suave")
        self.card_por_cobrar.set_valor(f"{moneda(rep.por_cobrar_total)}\nde este periodo: {moneda(rep.por_cobrar)}")
        total_caja = rep.ingresos + rep.gastos
        self.barra_caja.set(rep.ingresos / total_caja if total_caja else 0)
        signo = "a favor" if rep.balance >= 0 else "en contra"
        self.lbl_balance.configure(
            text=f"Caja del periodo: {moneda(rep.balance)} {signo}  ·  Vendido {moneda(rep.ventas)} con costo {moneda(rep.costo_vendido)}  ·  Stock total {cantidad(rep.stock_total)}",
            text_color=COLOR["exito"] if rep.balance >= 0 else COLOR["peligro_hover"])

        self.tabla_resumen.cargar(
            {"producto": mv.producto, "unidad": mv.unidad, "salidas": cantidad(mv.salidas), "entradas": cantidad(mv.entradas),
             "stock": cantidad(mv.stock_actual)}
            for mv in rep.movimientos)

        self.tabla_mensual.limpiar()
        for b in rep.boletas:
            padre = self.tabla_mensual.insertar(
                {"clave": b.clave, "fecha": b.fecha, "hora": b.hora, "tipo": b.tipo, "persona": b.persona, "encargada": b.encargada,
                 "total": moneda(b.total), "estado": b.estado}, tags=("resaltada",), texto="➕")
            for l in b.lineas:
                detalle = f"{l.producto} (x{cantidad(l.cantidad)})" if l.cantidad else l.producto
                self.tabla_mensual.insertar({"clave": l.clave, "persona": detalle, "total": moneda(l.total)}, padre=padre, texto="↳")
        n = len(rep.boletas)
        self.lbl_movimientos.configure(text=f"{n} movimiento(s) en el periodo" if n else "Sin movimientos con estos filtros")

    # ------------------------------------------------------------------ acciones
    def borrar_operacion(self):
        seleccion = self.tabla_mensual.iids_seleccionados()
        if not seleccion:
            return messagebox.showwarning("Atención", "Selecciona una boleta, una línea o un pago en la pestaña Movimientos.")
        if not messagebox.askyesno("Confirmar", f"¿Eliminar {len(seleccion)} fila(s) seleccionada(s)?\n\n"
                                                "Si es una boleta entera se revertirá el stock de todos sus productos. Esta acción no se puede deshacer."):
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
        elif not bloqueados:
            self.app.toast.mostrar(f"{len(claves)} operación(es) eliminada(s)", "alerta")

    def imprimir_boleta(self):
        """PDF de la boleta seleccionada (o de la boleta a la que pertenece la línea seleccionada)."""
        iid = self.tabla_mensual.iid_seleccionado()
        if not iid:
            return messagebox.showwarning("Atención", "Selecciona una boleta en la pestaña Movimientos.")
        iid = self.tabla_mensual.padre(iid) or iid
        clave = str(self.tabla_mensual.valores(iid)["clave"])
        if not clave.startswith("B:"):
            return messagebox.showwarning("Atención", "Los pagos de fiados no tienen boleta imprimible; selecciona una venta, fiado o ingreso.")
        return self.app.imprimir_boleta(int(clave[2:]))

    def exportar_excel(self):
        nombre = f"movimientos_{self.anio}_{self.mes:02d}.xlsx"
        fp = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], initialfile=nombre)
        if not fp:
            return
        if self.app.reportes.exportar_excel(fp, self.anio, self.mes, **self.filtros()):
            self.app.toast.mostrar(f"Exportado a {fp}", "exito", 4000)
        else:
            messagebox.showinfo("Sin datos", "No hay movimientos con estos filtros para exportar.")
