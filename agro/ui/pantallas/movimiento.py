"""Pantalla unificada de Ventas (modo='venta') y Compras (modo='compra').

Izquierda: buscador + tabla de productos. Derecha: carrito, total y un solo botón de
finalizar. Agregar al carrito pasa por DialogoCantidad (doble clic o Enter en un producto).
"""
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from agro.config import CLIENTE_GENERAL
from agro.registro import log
from agro.servicios.carrito import Carrito
from agro.servicios.formato import cantidad, hoy, moneda
from agro.servicios.operaciones import ErrorOperacion
from agro.ui import dialogos
from agro.ui.componentes import (Columna, Encabezado, Tabla, Tooltip, boton_exito, boton_fiado, boton_info,
                                 boton_peligro, boton_primario, boton_secundario)
from agro.ui.tema import COLOR, ESPACIO, fuente

MODOS = {
    "venta": dict(nombre="ventas", titulo="Nueva venta", subtitulo="Elige productos, arma el carrito y cobra al contado o al fiado",
                  persona="Cliente", tipo_persona="cliente", col_precio="P. Venta", col_stock="Stock disp.",
                  col_punit="P. Unit", prefijo_total="TOTAL", color_total="peligro_hover"),
    "compra": dict(nombre="compras", titulo="Ingreso de mercadería", subtitulo="Registra lo que llega del proveedor y su costo unitario",
                   persona="Proveedor", tipo_persona="proveedor", col_precio="Costo ref.", col_stock="Stock actual",
                   col_punit="Costo U.", prefijo_total="TOTAL GASTO", color_total="info"),
}


class PantallaMovimiento(ctk.CTkFrame):
    def __init__(self, master, app, modo):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self.modo = modo
        self.cfg = MODOS[modo]
        self.es_venta = modo == "venta"
        self.carrito = Carrito()
        self.ultimo_producto = None   # para volver a marcarlo tras recargar la tabla
        self._dialogo = None
        self._construir()

    # ------------------------------------------------------------------ construcción
    def _construir(self):
        s, m, l = ESPACIO["s"], ESPACIO["m"], ESPACIO["l"]

        enc = Encabezado(self, self.cfg["titulo"], self.cfg["subtitulo"])
        enc.pack(fill="x", padx=l, pady=(l, m))
        self.ent_fecha = ctk.CTkEntry(enc.acciones, justify="center", width=110)
        self.ent_fecha.pack(side="left")
        self.ent_fecha.insert(0, hoy())
        self.ent_fecha.configure(state="readonly")
        boton_secundario(enc.acciones, "📆", lambda: dialogos.abrir_calendario_popup(self.app, self.ent_fecha), width=36).pack(side="left", padx=(ESPACIO["xs"], m))
        ctk.CTkLabel(enc.acciones, text=f"{self.cfg['persona']}:", font=fuente("cuerpo")).pack(side="left", padx=(0, ESPACIO["xs"]))
        self.combo_persona = ctk.CTkOptionMenu(enc.acciones, values=[CLIENTE_GENERAL] if self.es_venta else ["—"], width=200,
                                               command=lambda v: self._actualizar_pie())
        self.combo_persona.pack(side="left")
        boton_primario(enc.acciones, "+", self._nueva_persona, width=32).pack(side="left", padx=(ESPACIO["xs"], 0))

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=l, pady=(0, l))
        cuerpo.grid_columnconfigure(0, weight=3, uniform="col")
        cuerpo.grid_columnconfigure(1, weight=2, uniform="col")
        cuerpo.grid_rowconfigure(0, weight=1)

        # --- izquierda: productos ---
        f_izq = ctk.CTkFrame(cuerpo)
        f_izq.grid(row=0, column=0, sticky="nsew", padx=(0, s))
        f_buscador = ctk.CTkFrame(f_izq, fg_color="transparent")
        f_buscador.pack(fill="x", padx=m, pady=(m, s))
        ctk.CTkLabel(f_buscador, text="Buscar producto", font=fuente("cuerpo_negrita")).pack(side="left", padx=(0, s))
        self.ent_buscar = ctk.CTkEntry(f_buscador, placeholder_text="Escribe y pulsa Enter para elegir el primero")
        self.ent_buscar.pack(side="left", fill="x", expand=True)
        self.ent_buscar.bind("<KeyRelease>", self._al_escribir_busqueda)
        self.ent_buscar.bind("<Return>", lambda e: self._seleccionar_primero())
        self.ent_buscar.bind("<Down>", lambda e: self._seleccionar_primero())

        self.tabla_productos = Tabla(f_izq, [
            Columna("producto", "Producto", 220),
            Columna("unidad", "Unidad", 60, "center"),
            Columna("precio", self.cfg["col_precio"], 90, "e"),
            Columna("stock", self.cfg["col_stock"], 90, "e"),
        ], on_doble_clic=lambda e: self.abrir_dialogo_cantidad())
        self.tabla_productos.pack(fill="both", expand=True, padx=m, pady=(0, s))
        self.tabla_productos.tree.bind("<Return>", lambda e: self.abrir_dialogo_cantidad())
        ctk.CTkLabel(f_izq, text="Doble clic o Enter sobre un producto para agregarlo al carrito",
                     font=fuente("pequeña"), text_color=COLOR["texto_suave"]).pack(anchor="w", padx=m, pady=(0, m))

        # --- derecha: carrito ---
        f_der = ctk.CTkFrame(cuerpo)
        f_der.grid(row=0, column=1, sticky="nsew", padx=(s, 0))
        cab = ctk.CTkFrame(f_der, fg_color="transparent")
        cab.pack(fill="x", padx=m, pady=(m, s))
        lbl_cab = ctk.CTkLabel(cab, text="Carrito  ⓘ", font=fuente("cuerpo_negrita"))
        lbl_cab.pack(side="left")
        Tooltip(lbl_cab, "Doble clic en Cant, P. Unit o Subtotal para editar la línea.\nSupr quita la línea seleccionada.")
        self.lbl_items = ctk.CTkLabel(cab, text="0 líneas", font=fuente("pequeña"), text_color=COLOR["texto_suave"])
        self.lbl_items.pack(side="right")

        # Solo "Producto" se estira: las columnas numéricas quedan fijas para que Subtotal
        # nunca se recorte por la derecha en la columna del 40 %.
        self.tabla_carrito = Tabla(f_der, [
            Columna("producto", "Producto", 110),
            Columna("cantidad", "Cant", 50, "center", estirar=False),
            Columna("punit", self.cfg["col_punit"], 70, "e", estirar=False),
            Columna("subtotal", "Subtotal", 80, "e", estirar=False),
        ], on_doble_clic=self._editar_celda)
        self.tabla_carrito.pack(fill="both", expand=True, padx=m)
        self.tabla_carrito.tree.bind("<Delete>", lambda e: self.quitar_linea())

        acciones = ctk.CTkFrame(f_der, fg_color="transparent")
        acciones.pack(fill="x", padx=m, pady=(s, 0))
        self.ultima_boleta_id = None
        self.btn_imprimir = boton_secundario(acciones, "🖨 Imprimir última", self.imprimir_ultima, width=130, height=28,
                                             font=fuente("pequeña"), state="disabled")
        self.btn_imprimir.pack(side="left")
        Tooltip(self.btn_imprimir, "Genera el PDF (80 mm) de la última boleta registrada en esta pantalla y lo abre para imprimir.")
        boton_peligro(acciones, "Vaciar", self.vaciar_carrito, width=80, height=28, font=fuente("pequeña")).pack(side="right")
        boton_secundario(acciones, "Quitar", self.quitar_linea, width=80, height=28, font=fuente("pequeña")).pack(side="right", padx=(0, ESPACIO["xs"]))

        self.lbl_total = ctk.CTkLabel(f_der, text=f"{self.cfg['prefijo_total']}  {moneda(0)}", font=fuente("titulo"),
                                      text_color=COLOR[self.cfg["color_total"]], anchor="e")
        self.lbl_total.pack(fill="x", padx=m, pady=(s, 0))

        pie = ctk.CTkFrame(f_der, fg_color="transparent")
        pie.pack(fill="x", padx=m, pady=(s, m))
        if self.es_venta:
            self.seg_tipo = ctk.CTkSegmentedButton(pie, values=["Contado", "Fiado"], command=lambda v: self._actualizar_pie())
            self.seg_tipo.set("Contado")
            self.seg_tipo.pack(fill="x", pady=(0, s))
            self.btn_procesar = boton_exito(pie, "Cobrar", self.procesar, height=48, font=fuente("subtitulo"))
        else:
            self.seg_tipo = None
            self.btn_procesar = boton_info(pie, "Registrar ingreso", self.procesar, height=48, font=fuente("subtitulo"))
        self.btn_procesar.pack(fill="x")
        self.lbl_aviso = ctk.CTkLabel(pie, text="", font=fuente("pequeña"), text_color=COLOR["peligro_hover"], anchor="w")
        self.lbl_aviso.pack(fill="x", pady=(ESPACIO["xs"], 0))

        self.app.bind_all("<Control-Return>", self._atajo_procesar, add="+")
        self._actualizar_pie()

    # ------------------------------------------------------------------ protocolo con la app
    def al_mostrar(self):
        self.ent_buscar.focus_set()

    def limpiar_seleccion(self):
        self.tabla_productos.deseleccionar()
        self.tabla_carrito.deseleccionar()
        self.ultimo_producto = None

    def refrescar_contactos(self, clientes, proveedores):
        opciones = clientes if self.es_venta else proveedores
        if opciones:
            actual = self.combo_persona.get()
            self.combo_persona.configure(values=opciones)
            if self.es_venta:
                self.combo_persona.set(actual if actual in opciones else (CLIENTE_GENERAL if CLIENTE_GENERAL in opciones else opciones[0]))
            else:
                self.combo_persona.set(actual if actual in opciones else opciones[0])
        self._actualizar_pie()

    def refrescar_productos(self):
        filtro = self.ent_buscar.get().strip().lower()
        self.tabla_productos.limpiar()
        for p in self.app.db.productos.listar():
            if filtro and filtro not in p.nombre.lower():
                continue
            stock_visible = self._stock_disponible(p)
            precio = p.precio_venta if self.es_venta else p.precio_compra
            self.tabla_productos.insertar(
                {"producto": p.nombre, "unidad": p.unidad, "precio": moneda(precio), "stock": cantidad(stock_visible)},
                tags=("alerta",) if stock_visible <= p.stock_minimo else ())
        if self.ultimo_producto:
            self.tabla_productos.seleccionar_por_valor("producto", self.ultimo_producto)

    def _stock_disponible(self, p):
        """En venta, el stock mostrado descuenta lo que ya está en el carrito."""
        return p.stock - self.carrito.cantidad_de(p.nombre) if self.es_venta else p.stock

    # ------------------------------------------------------------------ búsqueda y selección
    def _al_escribir_busqueda(self, event):
        if event.keysym in ("Return", "Down", "Up", "Tab"):
            return
        self.refrescar_productos()

    def _seleccionar_primero(self):
        iids = self.tabla_productos.iids()
        if iids:
            self.tabla_productos.seleccionar_iid(iids[0])
            self.tabla_productos.tree.focus_set()

    def producto_seleccionado(self):
        fila = self.tabla_productos.seleccion()
        return self.app.db.productos.obtener(str(fila["producto"])) if fila else None

    # ------------------------------------------------------------------ agregar al carrito
    def abrir_dialogo_cantidad(self):
        """Doble clic / Enter en un producto: pide cantidad (y precio en compras)."""
        p = self.producto_seleccionado()
        if p is None:
            messagebox.showwarning("Atención", "Selecciona un producto de la lista.")
            return None
        precio = p.precio_venta if self.es_venta else p.precio_compra
        self._dialogo = dialogos.DialogoCantidad(
            self.app, p.nombre, precio, p.unidad, self._stock_disponible(p), precio_editable=not self.es_venta,
            al_confirmar=lambda cant, pre: self.agregar_producto(p.nombre, cant, pre))
        return self._dialogo

    def agregar_producto(self, nombre, cant, precio=None):
        """Agrega una línea al carrito. Devuelve True si se agregó."""
        p = self.app.db.productos.obtener(nombre)
        if p is None:
            messagebox.showwarning("Atención", f"El producto '{nombre}' ya no existe en el inventario.")
            return False
        if cant <= 0:
            messagebox.showerror("Error", "La cantidad debe ser mayor a cero.")
            return False
        if precio is None:
            precio = p.precio_venta if self.es_venta else p.precio_compra
        if self.es_venta:
            disp = self._stock_disponible(p)
            if disp < cant and not messagebox.askyesno(
                    "Advertencia de Stock",
                    f"Intenta vender más del stock disponible ({cantidad(disp)} {p.unidad}). Quedará negativo.\n\n¿Continuar de todos modos?"):
                return False
        self.carrito.agregar(p.nombre, precio, cant)
        self.ultimo_producto = p.nombre
        self._actualizar_carrito_ui()
        return True

    # ------------------------------------------------------------------ carrito
    def _actualizar_carrito_ui(self):
        self.tabla_carrito.cargar(
            {"producto": l.producto, "cantidad": cantidad(l.cantidad), "punit": moneda(l.precio_unit), "subtotal": moneda(l.subtotal)}
            for l in self.carrito)
        n = len(self.carrito)
        self.lbl_items.configure(text=f"{n} línea" if n == 1 else f"{n} líneas")
        self.lbl_total.configure(text=f"{self.cfg['prefijo_total']}  {moneda(self.carrito.total)}")
        if self.es_venta:
            self.refrescar_productos()
        self._actualizar_pie()

    def quitar_linea(self):
        iid = self.tabla_carrito.iid_seleccionado()
        if not iid:
            messagebox.showwarning("Atención", "Selecciona una línea del carrito para quitarla.")
            return
        self.carrito.quitar(self.tabla_carrito.indice(iid))
        self._actualizar_carrito_ui()

    def vaciar_carrito(self):
        self.carrito.vaciar()
        self._actualizar_carrito_ui()

    def _editar_celda(self, event):
        """Edición en línea de Cant (#2), P. Unit (#3) o Subtotal (#4) del carrito."""
        tree = self.tabla_carrito.tree
        if tree.identify_region(event.x, event.y) != "cell": return
        item_id = tree.identify_row(event.y)
        column = tree.identify_column(event.x)
        if not item_id or column not in ('#2', '#3', '#4'): return
        idx = tree.index(item_id)
        if idx >= len(self.carrito): return
        campo = {'#2': 'cantidad', '#3': 'precio_unit', '#4': 'subtotal'}[column]
        x, y, width, height = tree.bbox(item_id, column)

        entry = ttk.Entry(tree)
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, str(getattr(self.carrito[idx], campo)))
        entry.select_range(0, tk.END)
        entry.focus()

        # <Return> y <FocusOut> disparan ambos guardar: la bandera evita ejecutar dos veces
        # sobre un Entry ya destruido (TclError).
        cerrado = {"ok": False}

        def cerrar_entry():
            if cerrado["ok"]: return False
            cerrado["ok"] = True
            try: entry.destroy()
            except tk.TclError: pass
            return True

        def guardar(e=None):
            try:
                texto = entry.get()
            except tk.TclError:
                return
            if not cerrar_entry(): return
            try:
                self.carrito.editar(idx, campo, texto)
                self._actualizar_carrito_ui()
            except ValueError:
                messagebox.showerror("Error", "Por favor ingresa un número válido o fracción (ej. 1/2) mayor a cero.")

        entry.bind("<Return>", guardar)
        entry.bind("<FocusOut>", guardar)
        entry.bind("<Escape>", lambda e: cerrar_entry())

    # ------------------------------------------------------------------ pie y finalizar
    def es_fiado(self):
        return self.es_venta and self.seg_tipo.get() == "Fiado"

    def _actualizar_pie(self):
        if not hasattr(self, "btn_procesar"):
            return
        total = moneda(self.carrito.total)
        aviso = ""
        if self.carrito.vacio:
            aviso = "Agrega productos al carrito."
        if self.es_venta:
            if self.es_fiado():
                texto = f"Registrar fiado  {total}"
                if self.combo_persona.get() == CLIENTE_GENERAL:
                    aviso = f"Para fiar elige un cliente distinto de {CLIENTE_GENERAL}."
            else:
                texto = f"Cobrar  {total}"
            self.btn_procesar.configure(text=texto, fg_color=COLOR["fiado"] if self.es_fiado() else COLOR["exito"],
                                        hover_color=COLOR["fiado_hover"] if self.es_fiado() else COLOR["exito_hover"],
                                        text_color=COLOR["texto_oscuro"] if self.es_fiado() else "#FFFFFF")
        else:
            self.btn_procesar.configure(text=f"Registrar ingreso  {total}")
        self.btn_procesar.configure(state="disabled" if aviso else "normal")
        self.lbl_aviso.configure(text=aviso)

    def _atajo_procesar(self, event=None):
        if self.app.pantalla_actual == self.cfg["nombre"] and self.btn_procesar.cget("state") == "normal":
            self.procesar()

    def procesar(self):
        if self.btn_procesar.cget("state") != "normal":
            return False
        total = self.carrito.total
        persona = self.combo_persona.get()
        try:
            if self.es_venta:
                fiado = self.es_fiado()
                boleta_id = self.app.operaciones.registrar_venta(self.carrito, self.ent_fecha.get(), self.app.encargada_actual(), persona, fiado=fiado)
                mensaje = f"{'Fiado' if fiado else 'Venta'} registrado: {moneda(total)}" + (f" a {persona}" if fiado else "")
            else:
                fiado = False
                boleta_id = self.app.operaciones.registrar_compra(self.carrito, self.ent_fecha.get(), self.app.encargada_actual(), persona)
                mensaje = f"Ingreso registrado: {moneda(total)} de {persona}"
        except ErrorOperacion as e:
            messagebox.showwarning("Atención", str(e))
            return False
        except sqlite3.Error as e:
            log.error("Fallo al registrar %s: %s", self.modo, e)
            messagebox.showerror("Error", f"No se guardó la operación (ningún stock fue modificado):\n{e}")
            return False
        self.ultima_boleta_id = boleta_id
        self.btn_imprimir.configure(state="normal")
        self.vaciar_carrito()
        self.ent_buscar.delete(0, tk.END)
        self.ultimo_producto = None
        self.app.refrescar_productos()
        if fiado:
            self.app.refrescar_fiados()
        if self.es_venta:
            self.seg_tipo.set("Contado")
            self._actualizar_pie()
        self.app.toast.mostrar(mensaje, "exito")
        self.ent_buscar.focus_set()
        return True

    def imprimir_ultima(self):
        if self.ultima_boleta_id is None:
            messagebox.showwarning("Atención", "Todavía no se registró ninguna boleta en esta pantalla.")
            return None
        return self.app.imprimir_boleta(self.ultima_boleta_id)

    # ------------------------------------------------------------------ contactos
    def _nueva_persona(self):
        def al_guardar(nombre):
            self.app.refrescar_contactos()
            self.combo_persona.set(nombre)
            self._actualizar_pie()
        dialogos.abrir_popup_contacto(self.app, self.app.db, self.cfg["tipo_persona"], al_guardar)
