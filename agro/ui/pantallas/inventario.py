"""Pantalla Inventario: alta, edición y lista de productos."""
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from agro.servicios.formato import cantidad, moneda, parse_cantidad


class PantallaInventario(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self._construir()

    def _construir(self):
        f_crear = ctk.CTkFrame(self)
        f_crear.pack(fill="x", padx=30, pady=(30, 10))
        ctk.CTkLabel(f_crear, text="CREAR NUEVO PRODUCTO", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10))

        f_campos = ctk.CTkFrame(f_crear, fg_color="transparent")
        f_campos.pack(pady=10)
        ctk.CTkLabel(f_campos, text="Nombre:").grid(row=0, column=0, padx=5)
        self.e_new_nom = ctk.CTkEntry(f_campos, width=160); self.e_new_nom.grid(row=0, column=1, padx=5)
        ctk.CTkLabel(f_campos, text="P. Venta:").grid(row=0, column=2, padx=5)
        self.e_new_prec = ctk.CTkEntry(f_campos, width=70); self.e_new_prec.grid(row=0, column=3, padx=5)
        ctk.CTkLabel(f_campos, text="P. Compra (Costo):").grid(row=0, column=4, padx=5)
        self.e_new_prec_comp = ctk.CTkEntry(f_campos, width=70); self.e_new_prec_comp.grid(row=0, column=5, padx=5)
        ctk.CTkLabel(f_campos, text="Stock Inicial:").grid(row=0, column=6, padx=5)
        self.e_new_stk = ctk.CTkEntry(f_campos, width=70); self.e_new_stk.grid(row=0, column=7, padx=5)
        ctk.CTkButton(f_campos, text="Guardar", fg_color="#2196F3", width=80, command=self.crear_producto).grid(row=0, column=8, padx=20)

        f_edit = ctk.CTkFrame(self)
        f_edit.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(f_edit, text="GESTIÓN DE PRODUCTOS EXISTENTES", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10))

        f_campos_edit = ctk.CTkFrame(f_edit, fg_color="transparent")
        f_campos_edit.pack(pady=10)
        ctk.CTkLabel(f_campos_edit, text="Seleccione:").grid(row=0, column=0, padx=5)
        self.combo_edit_prod = ctk.CTkOptionMenu(f_campos_edit, values=[], width=140, command=self.cargar_producto_en_formulario)
        self.combo_edit_prod.grid(row=0, column=1, padx=5)
        ctk.CTkLabel(f_campos_edit, text="Nombre:").grid(row=0, column=2, padx=5)
        self.e_edit_nom = ctk.CTkEntry(f_campos_edit, width=120); self.e_edit_nom.grid(row=0, column=3, padx=5)
        ctk.CTkLabel(f_campos_edit, text="P. Venta:").grid(row=0, column=4, padx=5)
        self.e_edit_prec = ctk.CTkEntry(f_campos_edit, width=60); self.e_edit_prec.grid(row=0, column=5, padx=5)
        ctk.CTkLabel(f_campos_edit, text="P. Compra:").grid(row=0, column=6, padx=5)
        self.e_edit_prec_comp = ctk.CTkEntry(f_campos_edit, width=60); self.e_edit_prec_comp.grid(row=0, column=7, padx=5)
        ctk.CTkLabel(f_campos_edit, text="Stock:").grid(row=0, column=8, padx=5)
        self.e_edit_stk = ctk.CTkEntry(f_campos_edit, width=60); self.e_edit_stk.grid(row=0, column=9, padx=5)
        ctk.CTkButton(f_campos_edit, text="Actualizar", fg_color="#FF9800", hover_color="#F57C00", width=80, command=self.actualizar_producto).grid(row=0, column=10, padx=10)
        ctk.CTkButton(f_campos_edit, text="🗑️", fg_color="#D32F2F", hover_color="#C62828", width=40, command=self.borrar_producto).grid(row=0, column=11, padx=5)

        f_lista = ctk.CTkFrame(self)
        f_lista.pack(fill="both", expand=True, padx=30, pady=(10, 30))
        ctk.CTkLabel(f_lista, text="LISTA COMPLETA: PRECIOS Y STOCK ACTUALIZADO", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)

        self.tree_precios = ttk.Treeview(f_lista, columns=("Producto", "Stock", "P. Venta", "P. Compra Unit."), show="headings")
        self.tree_precios.heading("Producto", text="Producto"); self.tree_precios.column("Producto", width=300)
        self.tree_precios.heading("Stock", text="Stock Actual"); self.tree_precios.column("Stock", width=100, anchor="center")
        self.tree_precios.heading("P. Venta", text="Precio Venta"); self.tree_precios.column("P. Venta", width=150, anchor="center")
        self.tree_precios.heading("P. Compra Unit.", text="Costo Unit. Compra"); self.tree_precios.column("P. Compra Unit.", width=150, anchor="center")
        scroll = ttk.Scrollbar(f_lista, orient="vertical", command=self.tree_precios.yview)
        scroll.pack(side="right", fill="y"); self.tree_precios.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        self.tree_precios.configure(yscrollcommand=scroll.set)
        self.tree_precios.bind("<<TreeviewSelect>>", self._al_seleccionar_en_tabla)

    # --- refresco ---
    def refrescar_productos(self):
        for r in self.tree_precios.get_children(): self.tree_precios.delete(r)
        for p in self.app.db.productos.listar():
            self.tree_precios.insert("", "end", values=(p.nombre, cantidad(p.stock), moneda(p.precio), moneda(p.precio_compra)))
        nombres = self.app.db.productos.nombres()
        if nombres:
            self.combo_edit_prod.configure(values=nombres)
            if self.combo_edit_prod.get() not in nombres:
                self.combo_edit_prod.set(nombres[0])
            self.cargar_producto_en_formulario(self.combo_edit_prod.get())

    def _al_seleccionar_en_tabla(self, event):
        s = self.tree_precios.selection()
        if s:
            nombre = str(self.tree_precios.item(s[0])['values'][0])
            self.combo_edit_prod.set(nombre)
            self.cargar_producto_en_formulario(nombre)

    def cargar_producto_en_formulario(self, nombre):
        if not nombre: return
        p = self.app.db.productos.obtener(nombre)
        if p:
            self.e_edit_nom.delete(0, tk.END); self.e_edit_nom.insert(0, p.nombre)
            self.e_edit_prec.delete(0, tk.END); self.e_edit_prec.insert(0, p.precio)
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
        if messagebox.askyesno("Eliminar", f"¿Eliminar '{nombre}'?"):
            if self.app.db.productos.eliminar(nombre):
                self.app.refrescar_productos()
