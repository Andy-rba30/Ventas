"""Pantalla Contactos: directorio de clientes y proveedores."""
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from agro.config import CLIENTE_GENERAL
from agro.ui.componentes import Columna, Tabla, boton_peligro, boton_primario
from agro.ui.tema import ESPACIO, fuente


class PantallaContactos(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self._construir()

    def _construir(self):
        s, m = ESPACIO["s"], ESPACIO["m"]
        ctk.CTkLabel(self, text="DIRECTORIO DE CONTACTOS", font=fuente("titulo")).pack(pady=m - 1)

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=ESPACIO["xl"] - 2, pady=s + 2)
        t_cli = self.tabs.add("👥 Clientes")
        t_prov = self.tabs.add("🏭 Proveedores")

        # Clientes
        f_form_cli = ctk.CTkFrame(t_cli, fg_color="transparent")
        f_form_cli.pack(fill="x", pady=s + 2)
        ctk.CTkLabel(f_form_cli, text="Nombre:").pack(side="left", padx=ESPACIO["xs"] + 1)
        self.ent_cli_nom = ctk.CTkEntry(f_form_cli, width=200); self.ent_cli_nom.pack(side="left", padx=ESPACIO["xs"] + 1)
        ctk.CTkLabel(f_form_cli, text="DNI/RUC:").pack(side="left", padx=ESPACIO["xs"] + 1)
        self.ent_cli_doc = ctk.CTkEntry(f_form_cli, width=120); self.ent_cli_doc.pack(side="left", padx=ESPACIO["xs"] + 1)
        ctk.CTkLabel(f_form_cli, text="Teléfono:").pack(side="left", padx=ESPACIO["xs"] + 1)
        self.ent_cli_tel = ctk.CTkEntry(f_form_cli, width=120); self.ent_cli_tel.pack(side="left", padx=ESPACIO["xs"] + 1)
        boton_primario(f_form_cli, "Guardar", lambda: self.guardar("cliente")).pack(side="left", padx=m + 4)
        boton_peligro(f_form_cli, "🗑️ Borrar", lambda: self.borrar("cliente")).pack(side="left", padx=ESPACIO["xs"] + 1)

        self.tabla_clientes = Tabla(t_cli, [
            Columna("id", "ID", oculta=True), Columna("nombre", "Nombre", 300),
            Columna("documento", "DNI/RUC", 150), Columna("telefono", "Teléfono", 150),
        ])
        self.tabla_clientes.pack(fill="both", expand=True, pady=s + 2)

        # Proveedores
        f_form_prov = ctk.CTkFrame(t_prov, fg_color="transparent")
        f_form_prov.pack(fill="x", pady=s + 2)
        ctk.CTkLabel(f_form_prov, text="Empresa/Nombre:").pack(side="left", padx=ESPACIO["xs"] + 1)
        self.ent_prov_nom = ctk.CTkEntry(f_form_prov, width=200); self.ent_prov_nom.pack(side="left", padx=ESPACIO["xs"] + 1)
        ctk.CTkLabel(f_form_prov, text="Contacto (Persona):").pack(side="left", padx=ESPACIO["xs"] + 1)
        self.ent_prov_doc = ctk.CTkEntry(f_form_prov, width=150); self.ent_prov_doc.pack(side="left", padx=ESPACIO["xs"] + 1)
        ctk.CTkLabel(f_form_prov, text="Teléfono:").pack(side="left", padx=ESPACIO["xs"] + 1)
        self.ent_prov_tel = ctk.CTkEntry(f_form_prov, width=120); self.ent_prov_tel.pack(side="left", padx=ESPACIO["xs"] + 1)
        boton_primario(f_form_prov, "Guardar", lambda: self.guardar("proveedor")).pack(side="left", padx=m + 4)
        boton_peligro(f_form_prov, "🗑️ Borrar", lambda: self.borrar("proveedor")).pack(side="left", padx=ESPACIO["xs"] + 1)

        self.tabla_proveedores = Tabla(t_prov, [
            Columna("id", "ID", oculta=True), Columna("nombre", "Empresa/Nombre", 300),
            Columna("contacto", "Contacto Vendedor", 200), Columna("telefono", "Teléfono", 150),
        ])
        self.tabla_proveedores.pack(fill="both", expand=True, pady=s + 2)

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
        tabla = self.tabla_clientes if tipo == "cliente" else self.tabla_proveedores
        fila = tabla.seleccion()
        if not fila: return
        nombre = str(fila["nombre"])
        if messagebox.askyesno("Borrar", f"¿Eliminar a {nombre}?"):
            if self.app.db.contactos.eliminar(tipo, nombre):
                self.app.refrescar_contactos()
            else:
                messagebox.showerror("Error", f"No se puede eliminar (quizás es {CLIENTE_GENERAL})")

    def refrescar_contactos(self, clientes, proveedores):
        self.tabla_clientes.cargar(self.app.db.contactos.listar("cliente"))
        self.tabla_proveedores.cargar(self.app.db.contactos.listar("proveedor"))

    def al_mostrar(self):
        self.refrescar_contactos(None, None)
