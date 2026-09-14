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


class PantallaMovimiento(ctk.CTkFrame):
    TIPO = ""                      # "ventas" | "compras"
    TITULO_IZQ = ""
    TITULO_DER = ""
    ETIQUETA_CANT = "Cant:"
    COL_PRECIO = "P. Venta"
    COL_STOCK = "Stock"
    COL_PUNIT_CARRITO = "P.Unit"
    PREFIJO_TOTAL = "TOTAL: S/."
    COLOR_TOTAL = "#D32F2F"
    ACTUALIZA_STOCK_CON_CARRITO = False   # Ventas muestra stock - carrito

    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self.carrito = Carrito()
        # Producto seleccionado (agro.db.Producto o None). Se guarda como estado porque el
        # Treeview pierde la selección al recargarse.
        self.producto_sel = None
        self._construir()

    # ------------------------------------------------------------------ construcción
    def _construir(self):
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        f_izq = ctk.CTkFrame(self)
        f_izq.grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        ctk.CTkLabel(f_izq, text=self.TITULO_IZQ, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        f_buscador = ctk.CTkFrame(f_izq, fg_color="transparent")
        f_buscador.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_buscador, text="🔍 Buscar:").pack(side="left")
        self.ent_buscar = ctk.CTkEntry(f_buscador)
        self.ent_buscar.pack(side="left", fill="x", expand=True, padx=10)
        self.ent_buscar.bind("<KeyRelease>", lambda e: self.refrescar_productos())

        container = ctk.CTkFrame(f_izq)
        container.pack(fill='both', expand=True, padx=15, pady=10)
        scroll = ttk.Scrollbar(container, orient="vertical")
        self.tree_productos = ttk.Treeview(container, columns=("Producto", "Precio", "Stock"), show="headings", yscrollcommand=scroll.set)
        scroll.config(command=self.tree_productos.yview)
        self.tree_productos.heading("Producto", text="Producto")
        self.tree_productos.heading("Precio", text=self.COL_PRECIO)
        self.tree_productos.heading("Stock", text=self.COL_STOCK)
        self.tree_productos.column("Producto", width=300)
        self.tree_productos.column("Precio", width=100, anchor="center")
        self.tree_productos.column("Stock", width=100, anchor="center")
        self.tree_productos.tag_configure('bajo_stock', foreground='#D32F2F', font=('Segoe UI', 10, 'bold'))
        scroll.pack(side="right", fill="y")
        self.tree_productos.pack(side="left", fill="both", expand=True)
        self.tree_productos.bind("<<TreeviewSelect>>", lambda e: self._al_seleccionar_producto())

        f_acciones = ctk.CTkFrame(self, width=350)
        f_acciones.grid(row=0, column=1, padx=(0, 15), pady=15, sticky="nsew")
        ctk.CTkLabel(f_acciones, text=self.TITULO_DER, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 5))

        f_fecha = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_fecha.pack(fill="x", padx=20, pady=5)
        self.ent_fecha = ctk.CTkEntry(f_fecha, justify='center')
        self.ent_fecha.pack(side="left", fill="x", expand=True)
        self.ent_fecha.insert(0, hoy())
        self.ent_fecha.configure(state='readonly')
        ctk.CTkButton(f_fecha, text="📆", width=40, command=lambda: dialogos.abrir_calendario_popup(self.app, self.ent_fecha)).pack(side="right", padx=5)

        self.lbl_sel_prod = ctk.CTkLabel(f_acciones, text="---", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1F6AA5")
        self.lbl_sel_prod.pack(anchor="w", padx=20, pady=(10, 0))

        f_cant = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_cant.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f_cant, text=self.ETIQUETA_CANT).pack(side="left")
        self.ent_cantidad = ctk.CTkEntry(f_cant, width=60)
        self.ent_cantidad.pack(side="left", padx=10)
        ctk.CTkButton(f_cant, text="➕ Agregar", width=100, command=self.agregar_al_carrito).pack(side="right")

        self.tree_carrito = ttk.Treeview(f_acciones, columns=("Prod", "P.Unit", "Cant", "Subt"), show="headings", height=5)
        self.tree_carrito.heading("Prod", text="Prod"); self.tree_carrito.column("Prod", width=110)
        self.tree_carrito.heading("P.Unit", text=self.COL_PUNIT_CARRITO); self.tree_carrito.column("P.Unit", width=60, anchor="center")
        self.tree_carrito.heading("Cant", text="Cant"); self.tree_carrito.column("Cant", width=40, anchor="center")
        self.tree_carrito.heading("Subt", text="Subt"); self.tree_carrito.column("Subt", width=60, anchor="e")
        self.tree_carrito.pack(fill="x", padx=20, pady=5)
        self.tree_carrito.bind("<Double-1>", self._editar_celda)
        ctk.CTkLabel(f_acciones, text="(Doble clic en Precio, Cantidad o Subtotal para editar)", font=ctk.CTkFont(size=11, slant="italic")).pack()

        self.lbl_total = ctk.CTkLabel(f_acciones, text=f"{self.PREFIJO_TOTAL} 0.00", font=ctk.CTkFont(size=16, weight="bold"), text_color=self.COLOR_TOTAL)
        self.lbl_total.pack(anchor="e", padx=20, pady=(0, 5))

        f_botones = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_botones.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkButton(f_botones, text="🗑️ Quitar Item", fg_color="#FF9800", hover_color="#F57C00", command=self.quitar_del_carrito).pack(side="left", expand=True, padx=(0, 5))
        ctk.CTkButton(f_botones, text="🗑️ Vaciar Todo", fg_color="#F44336", hover_color="#D32F2F", command=self.vaciar_carrito).pack(side="right", expand=True, padx=(5, 0))

        self._construir_pie(f_acciones)

    def _construir_pie(self, f_acciones):
        """Cliente/proveedor y botones de finalizar. Lo define cada subclase."""
        raise NotImplementedError

    # ------------------------------------------------------------------ productos
    def _fila_producto(self, p):
        """(values, tags) para la tabla de productos. Sobrescribible."""
        return (p.nombre, moneda(p.precio_venta), cantidad(p.stock)), ()

    def refrescar_productos(self):
        filtro = self.ent_buscar.get().lower()
        for r in self.tree_productos.get_children(): self.tree_productos.delete(r)
        for p in self.app.db.productos.listar():
            if filtro in p.nombre.lower():
                values, tags = self._fila_producto(p)
                self.tree_productos.insert("", "end", values=values, tags=tags)
        self._restaurar_seleccion()

    def _al_seleccionar_producto(self):
        s = self.tree_productos.selection()
        if not s: return
        nombre = str(self.tree_productos.item(s[0])['values'][0])
        self.producto_sel = self.app.db.productos.obtener(nombre)
        self.lbl_sel_prod.configure(text=nombre if self.producto_sel else "---")

    def _restaurar_seleccion(self):
        """Tras recargar la tabla, vuelve a marcar la fila del producto en estado si sigue visible."""
        if not self.producto_sel: return
        for iid in self.tree_productos.get_children():
            if str(self.tree_productos.item(iid)['values'][0]) == self.producto_sel.nombre:
                self.tree_productos.selection_set(iid)
                self.tree_productos.see(iid)
                return

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
        for r in self.tree_carrito.get_children(): self.tree_carrito.delete(r)
        for l in self.carrito:
            self.tree_carrito.insert("", "end", values=(l.producto, moneda(l.precio_unit), cantidad(l.cantidad), moneda(l.subtotal)))
        self.lbl_total.configure(text=f"{self.PREFIJO_TOTAL} {self.carrito.total:.2f}")
        if self.ACTUALIZA_STOCK_CON_CARRITO:
            self.refrescar_productos()

    def quitar_del_carrito(self):
        sel = self.tree_carrito.selection()
        if not sel:
            return messagebox.showwarning("Atención", "Selecciona un producto del carrito para quitarlo.")
        self.carrito.quitar(self.tree_carrito.index(sel[0]))
        self._actualizar_carrito_ui()

    def vaciar_carrito(self):
        self.carrito.vaciar()
        self._actualizar_carrito_ui()

    def _editar_celda(self, event):
        """Edición en línea de Precio (#2), Cantidad (#3) o Subtotal (#4) del carrito."""
        tree = self.tree_carrito
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
