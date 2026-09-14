"""Pantalla Contactos: directorio de clientes y proveedores."""
import tkinter as tk
from tkinter import messagebox, ttk

import customtkinter as ctk

from agro.config import CLIENTE_GENERAL


class PantallaContactos(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self._construir()

    def _construir(self):
        ctk.CTkLabel(self, text="DIRECTORIO DE CONTACTOS", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=15)

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=30, pady=10)
        t_cli = self.tabs.add("👥 Clientes")
        t_prov = self.tabs.add("🏭 Proveedores")

        # Clientes
        f_form_cli = ctk.CTkFrame(t_cli, fg_color="transparent")
        f_form_cli.pack(fill="x", pady=10)
        ctk.CTkLabel(f_form_cli, text="Nombre:").pack(side="left", padx=5)
        self.ent_cli_nom = ctk.CTkEntry(f_form_cli, width=200); self.ent_cli_nom.pack(side="left", padx=5)
        ctk.CTkLabel(f_form_cli, text="DNI/RUC:").pack(side="left", padx=5)
        self.ent_cli_doc = ctk.CTkEntry(f_form_cli, width=120); self.ent_cli_doc.pack(side="left", padx=5)
        ctk.CTkLabel(f_form_cli, text="Teléfono:").pack(side="left", padx=5)
        self.ent_cli_tel = ctk.CTkEntry(f_form_cli, width=120); self.ent_cli_tel.pack(side="left", padx=5)
        ctk.CTkButton(f_form_cli, text="Guardar", command=lambda: self.guardar("cliente")).pack(side="left", padx=20)
        ctk.CTkButton(f_form_cli, text="🗑️ Borrar", fg_color="#F44336", command=lambda: self.borrar("cliente")).pack(side="left", padx=5)

        self.tree_clientes = ttk.Treeview(t_cli, columns=("ID", "Nombre", "Documento", "Teléfono"), show="headings")
        self.tree_clientes.heading("Nombre", text="Nombre"); self.tree_clientes.column("Nombre", width=300)
        self.tree_clientes.heading("Documento", text="DNI/RUC"); self.tree_clientes.column("Documento", width=150)
        self.tree_clientes.heading("Teléfono", text="Teléfono"); self.tree_clientes.column("Teléfono", width=150)
        self.tree_clientes.column("ID", width=0, stretch=tk.NO)
        self.tree_clientes.pack(fill="both", expand=True, pady=10)

        # Proveedores
        f_form_prov = ctk.CTkFrame(t_prov, fg_color="transparent")
        f_form_prov.pack(fill="x", pady=10)
        ctk.CTkLabel(f_form_prov, text="Empresa/Nombre:").pack(side="left", padx=5)
        self.ent_prov_nom = ctk.CTkEntry(f_form_prov, width=200); self.ent_prov_nom.pack(side="left", padx=5)
        ctk.CTkLabel(f_form_prov, text="Contacto (Persona):").pack(side="left", padx=5)
        self.ent_prov_doc = ctk.CTkEntry(f_form_prov, width=150); self.ent_prov_doc.pack(side="left", padx=5)
        ctk.CTkLabel(f_form_prov, text="Teléfono:").pack(side="left", padx=5)
        self.ent_prov_tel = ctk.CTkEntry(f_form_prov, width=120); self.ent_prov_tel.pack(side="left", padx=5)
        ctk.CTkButton(f_form_prov, text="Guardar", command=lambda: self.guardar("proveedor")).pack(side="left", padx=20)
        ctk.CTkButton(f_form_prov, text="🗑️ Borrar", fg_color="#F44336", command=lambda: self.borrar("proveedor")).pack(side="left", padx=5)

        self.tree_proveedores = ttk.Treeview(t_prov, columns=("ID", "Nombre", "Contacto", "Teléfono"), show="headings")
        self.tree_proveedores.heading("Nombre", text="Empresa/Nombre"); self.tree_proveedores.column("Nombre", width=300)
        self.tree_proveedores.heading("Contacto", text="Contacto Vendedor"); self.tree_proveedores.column("Contacto", width=200)
        self.tree_proveedores.heading("Teléfono", text="Teléfono"); self.tree_proveedores.column("Teléfono", width=150)
        self.tree_proveedores.column("ID", width=0, stretch=tk.NO)
        self.tree_proveedores.pack(fill="both", expand=True, pady=10)

    def _campos(self, tipo):
        if tipo == "cliente":
            return self.ent_cli_nom, self.ent_cli_doc, self.ent_cli_tel
        return self.ent_prov_nom, self.ent_prov_doc, self.ent_prov_tel

    def guardar(self, tipo):
        e_nom, e_doc, e_tel = self._campos(tipo)
        n = e_nom.get().strip().upper()
        if not n:
            return messagebox.showerror("Error", f"Nombre de {tipo} obligatorio")
        if self.app.db.contactos.agregar(tipo, n, e_doc.get().strip(), e_tel.get().strip()):
            for e in (e_nom, e_doc, e_tel): e.delete(0, tk.END)
            self.app.refrescar_contactos()
        else:
            messagebox.showerror("Error", f"{tipo.capitalize()} ya existe")

    def borrar(self, tipo):
        tree = self.tree_clientes if tipo == "cliente" else self.tree_proveedores
        sel = tree.selection()
        if not sel: return
        nombre = tree.item(sel[0])['values'][1]
        if messagebox.askyesno("Borrar", f"¿Eliminar a {nombre}?"):
            if self.app.db.contactos.eliminar(tipo, nombre):
                self.app.refrescar_contactos()
            else:
                messagebox.showerror("Error", f"No se puede eliminar (quizás es {CLIENTE_GENERAL})")

    def refrescar_contactos(self, clientes, proveedores):
        for r in self.tree_clientes.get_children(): self.tree_clientes.delete(r)
        for r in self.tree_proveedores.get_children(): self.tree_proveedores.delete(r)
        for c in self.app.db.contactos.listar("cliente"): self.tree_clientes.insert("", "end", values=c)
        for p in self.app.db.contactos.listar("proveedor"): self.tree_proveedores.insert("", "end", values=p)

    def al_mostrar(self):
        self.refrescar_contactos(None, None)
