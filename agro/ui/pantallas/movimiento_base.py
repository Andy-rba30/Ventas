"""Base común de las pantallas Ventas y Compras: tabla de productos + carrito.

Las subclases definen los textos, cómo se calcula el precio de una línea y el pie
(cliente/proveedor y botones de finalizar).
"""
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from agro.servicios.carrito import Carrito
from agro.servicios.formato import cantidad, hoy, moneda, parse_cantidad
from agro.ui import dialogos
from agro.ui.componentes import Columna, Tabla, boton_alerta, boton_peligro, boton_primario
from agro.ui.tema import COLOR, ESPACIO, fuente


class PantallaMovimiento(ctk.CTkFrame):
    TIPO = ""                      # "ventas" | "compras"
    TITULO_IZQ = ""
    TITULO_DER = ""
    ETIQUETA_CANT = "Cant:"
    COL_PRECIO = "P. Venta"
    COL_STOCK = "Stock"
    COL_PUNIT_CARRITO = "P.Unit"
    PREFIJO_TOTAL = "TOTAL: S/."
    COLOR_TOTAL = "peligro_hover"          # token de tema
    ACTUALIZA_STOCK_CON_CARRITO = False    # Ventas muestra stock - carrito

    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self.carrito = Carrito()
        # Producto seleccionado (agro.db.Producto o None). Se guarda como estado porque la
        # tabla pierde la selección al recargarse.
        self.producto_sel = None
        self._construir()

    # ------------------------------------------------------------------ construcción
    def _construir(self):
        m, l = ESPACIO["m"], ESPACIO["l"]
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        f_izq = ctk.CTkFrame(self)
        f_izq.grid(row=0, column=0, padx=m - 1, pady=m - 1, sticky="nsew")
        ctk.CTkLabel(f_izq, text=self.TITULO_IZQ, font=fuente("subtitulo")).pack(pady=ESPACIO["s"] + 2)

        f_buscador = ctk.CTkFrame(f_izq, fg_color="transparent")
        f_buscador.pack(fill="x", padx=m - 1, pady=ESPACIO["xs"] + 1)
        ctk.CTkLabel(f_buscador, text="🔍 Buscar:").pack(side="left")
        self.ent_buscar = ctk.CTkEntry(f_buscador)
        self.ent_buscar.pack(side="left", fill="x", expand=True, padx=ESPACIO["s"] + 2)
        self.ent_buscar.bind("<KeyRelease>", lambda e: self.refrescar_productos())

        self.tabla_productos = Tabla(f_izq, [
            Columna("producto", "Producto", 300),
            Columna("precio", self.COL_PRECIO, 100, "center"),
            Columna("stock", self.COL_STOCK, 100, "center"),
        ], on_select=self._al_seleccionar_producto)
        self.tabla_productos.pack(fill="both", expand=True, padx=m - 1, pady=ESPACIO["s"] + 2)

        f_acciones = ctk.CTkFrame(self, width=350)
        f_acciones.grid(row=0, column=1, padx=(0, m - 1), pady=m - 1, sticky="nsew")
        ctk.CTkLabel(f_acciones, text=self.TITULO_DER, font=fuente("subtitulo")).pack(pady=(m - 1, ESPACIO["xs"] + 1))

        f_fecha = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_fecha.pack(fill="x", padx=m + 4, pady=ESPACIO["xs"] + 1)
        self.ent_fecha = ctk.CTkEntry(f_fecha, justify='center')
        self.ent_fecha.pack(side="left", fill="x", expand=True)
        self.ent_fecha.insert(0, hoy())
        self.ent_fecha.configure(state='readonly')
        boton_primario(f_fecha, "📆", lambda: dialogos.abrir_calendario_popup(self.app, self.ent_fecha), width=40).pack(side="right", padx=ESPACIO["xs"] + 1)

        self.lbl_sel_prod = ctk.CTkLabel(f_acciones, text="---", font=fuente("destacado"), text_color=COLOR["primario"])
        self.lbl_sel_prod.pack(anchor="w", padx=m + 4, pady=(ESPACIO["s"] + 2, 0))

        f_cant = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_cant.pack(fill="x", padx=m + 4, pady=ESPACIO["xs"] + 1)
        ctk.CTkLabel(f_cant, text=self.ETIQUETA_CANT).pack(side="left")
        self.ent_cantidad = ctk.CTkEntry(f_cant, width=60)
        self.ent_cantidad.pack(side="left", padx=ESPACIO["s"] + 2)
        boton_primario(f_cant, "➕ Agregar", self.agregar_al_carrito, width=100).pack(side="right")

        self.tabla_carrito = Tabla(f_acciones, [
            Columna("prod", "Prod", 110),
            Columna("punit", self.COL_PUNIT_CARRITO, 60, "center"),
            Columna("cant", "Cant", 40, "center"),
            Columna("subt", "Subt", 60, "e"),
        ], alto=5, on_doble_clic=self._editar_celda)
        self.tabla_carrito.pack(fill="x", padx=m + 4, pady=ESPACIO["xs"] + 1)
        ctk.CTkLabel(f_acciones, text="(Doble clic en Precio, Cantidad o Subtotal para editar)", font=fuente("pequeña_cursiva")).pack()

        self.lbl_total = ctk.CTkLabel(f_acciones, text=f"{self.PREFIJO_TOTAL} 0.00", font=fuente("subtitulo"), text_color=COLOR[self.COLOR_TOTAL])
        self.lbl_total.pack(anchor="e", padx=m + 4, pady=(0, ESPACIO["xs"] + 1))

        f_botones = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_botones.pack(fill="x", padx=m + 4, pady=(0, ESPACIO["s"] + 2))
        boton_alerta(f_botones, "🗑️ Quitar Item", self.quitar_del_carrito).pack(side="left", expand=True, padx=(0, ESPACIO["xs"] + 1))
        boton_peligro(f_botones, "🗑️ Vaciar Todo", self.vaciar_carrito).pack(side="right", expand=True, padx=(ESPACIO["xs"] + 1, 0))

        self._construir_pie(f_acciones)

    def _construir_pie(self, f_acciones):
        """Cliente/proveedor y botones de finalizar. Lo define cada subclase."""
        raise NotImplementedError

    # ------------------------------------------------------------------ productos
    def _fila_producto(self, p):
        """(dict de la fila, tags) para la tabla de productos. Sobrescribible."""
        return {"producto": p.nombre, "precio": moneda(p.precio_venta), "stock": cantidad(p.stock)}, ()

    def refrescar_productos(self):
        filtro = self.ent_buscar.get().lower()
        self.tabla_productos.limpiar()
        for p in self.app.db.productos.listar():
            if filtro in p.nombre.lower():
                fila, tags = self._fila_producto(p)
                self.tabla_productos.insertar(fila, tags=tags)
        self._restaurar_seleccion()

    def _al_seleccionar_producto(self, fila):
        if not fila: return
        nombre = str(fila["producto"])
        self.producto_sel = self.app.db.productos.obtener(nombre)
        self.lbl_sel_prod.configure(text=nombre if self.producto_sel else "---")

    def _restaurar_seleccion(self):
        """Tras recargar la tabla, vuelve a marcar la fila del producto en estado si sigue visible."""
        if self.producto_sel:
            self.tabla_productos.seleccionar_por_valor("producto", self.producto_sel.nombre)

    def _producto_para_carrito(self):
        """Relee de la BD el producto seleccionado. None (y aviso) si no hay o ya no existe."""
        if self.producto_sel is None:
            messagebox.showwarning("Atención", "Selecciona un producto primero.")
            return None
        prod = self.app.db.productos.obtener(self.producto_sel.nombre)
        if prod is None:
            messagebox.showwarning("Atención", f"El producto '{self.producto_sel.nombre}' ya no existe en el inventario.")
            self.producto_sel = None
            self.lbl_sel_prod.configure(text="---")
            return None
        self.producto_sel = prod
        return prod

    # ------------------------------------------------------------------ carrito
    def _precio_para(self, prod, cant):
        """Precio unitario de la línea, o None para cancelar. Lo define cada subclase."""
        raise NotImplementedError

    def agregar_al_carrito(self):
        prod = self._producto_para_carrito()
        if prod is None: return
        try:
            cant = parse_cantidad(self.ent_cantidad.get())
            if cant <= 0: raise ValueError
        except ValueError:
            return messagebox.showerror("Error", "La cantidad debe ser un número o fracción (ej: 1/2) mayor a cero.")
        precio = self._precio_para(prod, cant)
        if precio is None: return
        self.carrito.agregar(prod.nombre, precio, cant)
        self._actualizar_carrito_ui()
        self.ent_cantidad.delete(0, tk.END)

    def _actualizar_carrito_ui(self):
        self.tabla_carrito.cargar(
            {"prod": l.producto, "punit": moneda(l.precio_unit), "cant": cantidad(l.cantidad), "subt": moneda(l.subtotal)}
            for l in self.carrito)
        self.lbl_total.configure(text=f"{self.PREFIJO_TOTAL} {self.carrito.total:.2f}")
        if self.ACTUALIZA_STOCK_CON_CARRITO:
            self.refrescar_productos()

    def quitar_del_carrito(self):
        iid = self.tabla_carrito.iid_seleccionado()
        if not iid:
            return messagebox.showwarning("Atención", "Selecciona un producto del carrito para quitarlo.")
        self.carrito.quitar(self.tabla_carrito.indice(iid))
        self._actualizar_carrito_ui()

    def vaciar_carrito(self):
        self.carrito.vaciar()
        self._actualizar_carrito_ui()

    def _editar_celda(self, event):
        """Edición en línea de Precio (#2), Cantidad (#3) o Subtotal (#4) del carrito."""
        tree = self.tabla_carrito.tree
        if tree.identify_region(event.x, event.y) != "cell": return
        item_id = tree.identify_row(event.y)
        column = tree.identify_column(event.x)
        if not item_id or column not in ('#2', '#3', '#4'): return
        idx = tree.index(item_id)
        if idx >= len(self.carrito): return
        campo = {'#2': 'precio_unit', '#3': 'cantidad', '#4': 'subtotal'}[column]
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

    # ------------------------------------------------------------------ utilidades
    def _limpiar_tras_procesar(self):
        self.vaciar_carrito()
        self.ent_buscar.delete(0, tk.END)
        self.app.refrescar_productos()
