"""Pantalla Inventario: alta, edición y lista de productos."""
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from agro.servicios.formato import cantidad, moneda, parse_cantidad
from agro.ui.componentes import Columna, Tabla, boton_alerta, boton_info, boton_peligro
from agro.ui.tema import ESPACIO, fuente


class PantallaInventario(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self._construir()

    def _construir(self):
        xs, s, m, xl = ESPACIO["xs"] + 1, ESPACIO["s"] + 2, ESPACIO["m"] - 1, ESPACIO["xl"] - 2
        f_crear = ctk.CTkFrame(self)
        f_crear.pack(fill="x", padx=xl, pady=(xl, s))
        ctk.CTkLabel(f_crear, text="CREAR NUEVO PRODUCTO", font=fuente("subtitulo")).pack(pady=(m, s))

        f_campos = ctk.CTkFrame(f_crear, fg_color="transparent")
        f_campos.pack(pady=s)
        ctk.CTkLabel(f_campos, text="Nombre:").grid(row=0, column=0, padx=xs)
        self.e_new_nom = ctk.CTkEntry(f_campos, width=160); self.e_new_nom.grid(row=0, column=1, padx=xs)
        ctk.CTkLabel(f_campos, text="P. Venta:").grid(row=0, column=2, padx=xs)
        self.e_new_prec = ctk.CTkEntry(f_campos, width=70); self.e_new_prec.grid(row=0, column=3, padx=xs)
        ctk.CTkLabel(f_campos, text="P. Compra (Costo):").grid(row=0, column=4, padx=xs)
        self.e_new_prec_comp = ctk.CTkEntry(f_campos, width=70); self.e_new_prec_comp.grid(row=0, column=5, padx=xs)
        ctk.CTkLabel(f_campos, text="Stock Inicial:").grid(row=0, column=6, padx=xs)
        self.e_new_stk = ctk.CTkEntry(f_campos, width=70); self.e_new_stk.grid(row=0, column=7, padx=xs)
        boton_info(f_campos, "Guardar", self.crear_producto, width=80).grid(row=0, column=8, padx=m + 5)

        f_edit = ctk.CTkFrame(self)
        f_edit.pack(fill="x", padx=xl, pady=s)
        ctk.CTkLabel(f_edit, text="GESTIÓN DE PRODUCTOS EXISTENTES", font=fuente("subtitulo")).pack(pady=(m, s))

        f_campos_edit = ctk.CTkFrame(f_edit, fg_color="transparent")
        f_campos_edit.pack(pady=s)
        ctk.CTkLabel(f_campos_edit, text="Seleccione:").grid(row=0, column=0, padx=xs)
        self.combo_edit_prod = ctk.CTkOptionMenu(f_campos_edit, values=[], width=140, command=self.cargar_producto_en_formulario)
        self.combo_edit_prod.grid(row=0, column=1, padx=xs)
        ctk.CTkLabel(f_campos_edit, text="Nombre:").grid(row=0, column=2, padx=xs)
        self.e_edit_nom = ctk.CTkEntry(f_campos_edit, width=120); self.e_edit_nom.grid(row=0, column=3, padx=xs)
        ctk.CTkLabel(f_campos_edit, text="P. Venta:").grid(row=0, column=4, padx=xs)
        self.e_edit_prec = ctk.CTkEntry(f_campos_edit, width=60); self.e_edit_prec.grid(row=0, column=5, padx=xs)
        ctk.CTkLabel(f_campos_edit, text="P. Compra:").grid(row=0, column=6, padx=xs)
        self.e_edit_prec_comp = ctk.CTkEntry(f_campos_edit, width=60); self.e_edit_prec_comp.grid(row=0, column=7, padx=xs)
        ctk.CTkLabel(f_campos_edit, text="Stock:").grid(row=0, column=8, padx=xs)
        self.e_edit_stk = ctk.CTkEntry(f_campos_edit, width=60); self.e_edit_stk.grid(row=0, column=9, padx=xs)
        boton_alerta(f_campos_edit, "Actualizar", self.actualizar_producto, width=80).grid(row=0, column=10, padx=s)
        boton_peligro(f_campos_edit, "🗑️", self.borrar_producto, width=40).grid(row=0, column=11, padx=xs)

        f_lista = ctk.CTkFrame(self)
        f_lista.pack(fill="both", expand=True, padx=xl, pady=(s, xl))
        ctk.CTkLabel(f_lista, text="LISTA COMPLETA: PRECIOS Y STOCK ACTUALIZADO", font=fuente("subtitulo")).pack(pady=s)

        self.tabla_precios = Tabla(f_lista, [
            Columna("producto", "Producto", 300),
            Columna("stock", "Stock Actual", 100, "center"),
            Columna("precio_venta", "Precio Venta", 150, "center"),
            Columna("precio_compra", "Costo Unit. Compra", 150, "center"),
        ], on_select=self._al_seleccionar_en_tabla)
        self.tabla_precios.pack(fill="both", expand=True, padx=xs, pady=xs)

    # --- refresco ---
    def refrescar_productos(self):
        productos = self.app.db.productos.listar()
        self.tabla_precios.cargar(
            ({"producto": p.nombre, "stock": cantidad(p.stock), "precio_venta": moneda(p.precio_venta), "precio_compra": moneda(p.precio_compra)}
             for p in productos),
            tags=lambda fila: ())
        for p, iid in zip(productos, self.tabla_precios.iids()):
            if p.bajo_stock:
                self.tabla_precios.tree.item(iid, tags=("alerta",))
        nombres = [p.nombre for p in productos]
        if nombres:
            self.combo_edit_prod.configure(values=nombres)
            if self.combo_edit_prod.get() not in nombres:
                self.combo_edit_prod.set(nombres[0])
            self.cargar_producto_en_formulario(self.combo_edit_prod.get())

    def _al_seleccionar_en_tabla(self, fila):
        if fila:
            nombre = str(fila["producto"])
            self.combo_edit_prod.set(nombre)
            self.cargar_producto_en_formulario(nombre)

    def cargar_producto_en_formulario(self, nombre):
        if not nombre: return
        p = self.app.db.productos.obtener(nombre)
        if p:
            self.e_edit_nom.delete(0, tk.END); self.e_edit_nom.insert(0, p.nombre)
            self.e_edit_prec.delete(0, tk.END); self.e_edit_prec.insert(0, p.precio_venta)
            self.e_edit_prec_comp.delete(0, tk.END); self.e_edit_prec_comp.insert(0, p.precio_compra)
            self.e_edit_stk.delete(0, tk.END); self.e_edit_stk.insert(0, cantidad(p.stock))

    # --- acciones ---
    def crear_producto(self):
        nombre = self.e_new_nom.get().strip().upper()
        if not nombre: return messagebox.showerror("Error", "Nombre vacío.")
        try:
            precio = float(self.e_new_prec.get())
            p_compra = float(self.e_new_prec_comp.get()) if self.e_new_prec_comp.get() else 0.0
            stock = parse_cantidad(self.e_new_stk.get())
            if precio <= 0 or stock < 0: return messagebox.showerror("Error", "Valores numéricos inválidos.")
            if self.app.db.productos.agregar(nombre, precio, p_compra, stock):
                self.app.refrescar_productos()
                for e in (self.e_new_nom, self.e_new_prec, self.e_new_prec_comp, self.e_new_stk): e.delete(0, tk.END)
                messagebox.showinfo("Éxito", "Producto agregado.")
            else:
                messagebox.showerror("Error", "El producto ya existe.")
        except ValueError:
            messagebox.showerror("Error", "Use números o fracciones válidas (ej: 1/2).")

    def actualizar_producto(self):
        prod = self.combo_edit_prod.get()
        n_nom = self.e_edit_nom.get().strip().upper()
        if not prod or not n_nom: return
        try:
            n_prec = float(self.e_edit_prec.get())
            n_p_comp = float(self.e_edit_prec_comp.get()) if self.e_edit_prec_comp.get() else 0.0
            stk_str = self.e_edit_stk.get().strip()
            n_stk = parse_cantidad(stk_str) if stk_str else None
            if n_prec <= 0: return messagebox.showerror("Error", "Precio > 0.")
            if self.app.db.productos.modificar(prod, n_nom, n_prec, n_p_comp, n_stk):
                self.combo_edit_prod.set(n_nom)
                self.app.refrescar_productos()
                messagebox.showinfo("Ok", "Producto actualizado.")
            else:
                messagebox.showerror("Error", "No se pudo actualizar (¿el nuevo nombre ya existe?).")
        except ValueError:
            messagebox.showerror("Error", "Datos numéricos inválidos.")

    def borrar_producto(self):
        nombre = self.combo_edit_prod.get()
        if not nombre: return
        if messagebox.askyesno("Eliminar", f"¿Eliminar '{nombre}'?\n\nEl producto dejará de aparecer en Ventas, Compras e Inventario, "
                                           "pero su historial de boletas se conserva. Si lo vuelves a crear con el mismo nombre se reactiva."):
            if self.app.db.productos.desactivar(nombre):
                self.app.refrescar_productos()
