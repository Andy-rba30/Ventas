"""Pantalla Contactos en maestro-detalle: pestañas Clientes / Proveedores, cada una con la
tabla a la izquierda y el panel de edición a la derecha. El alta abre un diálogo."""
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from agro.config import CLIENTE_GENERAL
from agro.servicios.formato import moneda
from agro.ui import dialogos
from agro.ui.componentes import Campo, Columna, Encabezado, Tabla, boton_enlace, boton_primario, boton_secundario
from agro.ui.tema import COLOR, ESPACIO, fuente

ETIQUETAS = {
    "cliente": dict(singular="cliente", titulo="Nuevo cliente", doc="DNI / RUC", nombre="Nombre"),
    "proveedor": dict(singular="proveedor", titulo="Nuevo proveedor", doc="Persona de contacto", nombre="Empresa / Nombre"),
}


class FormularioContacto(ctk.CTkFrame):
    """Campos verticales de un cliente o proveedor. leer() valida y devuelve un dict."""

    def __init__(self, parent, tipo, **kw):
        kw.setdefault("fg_color", "transparent")
        super().__init__(parent, **kw)
        et = ETIQUETAS[tipo]
        ancho = 260
        self.nombre = Campo(self, et["nombre"], ancho=ancho, horizontal=False, obligatorio=True)
        self.nombre.pack(fill="x", pady=(0, ESPACIO["s"]))
        self.documento = Campo(self, et["doc"], ancho=ancho, horizontal=False)
        self.documento.pack(fill="x", pady=(0, ESPACIO["s"]))
        self.telefono = Campo(self, "Teléfono", ancho=ancho, horizontal=False)
        self.telefono.pack(fill="x", pady=(0, ESPACIO["s"]))
        ctk.CTkLabel(self, text="Notas", font=fuente("cuerpo")).pack(anchor="w")
        self.notas = ctk.CTkTextbox(self, height=70, width=ancho, font=fuente("cuerpo"))
        self.notas.pack(fill="x", pady=(0, ESPACIO["s"]))

    def cargar(self, c):
        self.nombre.set(c.nombre)
        self.documento.set(c.documento)
        self.telefono.set(c.telefono)
        self.notas.delete("1.0", tk.END)
        self.notas.insert("1.0", c.notas)

    def leer(self):
        return {
            "nombre": self.nombre.valor().upper(),
            "documento": self.documento.get(),
            "telefono": self.telefono.get(),
            "notas": self.notas.get("1.0", tk.END).strip(),
        }

    def enfocar(self):
        self.nombre.focus()


class SeccionContactos(ctk.CTkFrame):
    """Una pestaña: tabla + panel de detalle para un tipo de contacto."""

    def __init__(self, master, app, tipo):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.tipo = tipo
        self.seleccionado = None
        self._construir()

    def _construir(self):
        s, m = ESPACIO["s"], ESPACIO["m"]
        et = ETIQUETAS[self.tipo]
        self.grid_columnconfigure(0, weight=13, uniform="col")
        self.grid_columnconfigure(1, weight=7, uniform="col")
        self.grid_rowconfigure(0, weight=1)

        f_izq = ctk.CTkFrame(self)
        f_izq.grid(row=0, column=0, sticky="nsew", padx=(0, s))
        self.tabla = Tabla(f_izq, [
            Columna("id", "ID", oculta=True),
            Columna("nombre", et["nombre"], 220),
            Columna("documento", et["doc"], 140),
            Columna("telefono", "Teléfono", 110, estirar=False),
        ], on_select=self._al_seleccionar)
        self.tabla.pack(fill="both", expand=True, padx=m, pady=m)

        self.f_der = ctk.CTkFrame(self)
        self.f_der.grid(row=0, column=1, sticky="nsew", padx=(s, 0))
        self.lbl_vacio = ctk.CTkLabel(self.f_der, text=f"Selecciona un {et['singular']}\no crea uno nuevo", font=fuente("cuerpo"),
                                      text_color=COLOR["texto_suave"], justify="center")
        self.panel = ctk.CTkFrame(self.f_der, fg_color="transparent")
        self.lbl_titulo = ctk.CTkLabel(self.panel, text="", font=fuente("subtitulo"), anchor="w")
        self.lbl_titulo.pack(fill="x", pady=(m, s))
        self.formulario = FormularioContacto(self.panel, self.tipo)
        self.formulario.pack(fill="x")
        if self.tipo == "cliente":
            f_deuda = ctk.CTkFrame(self.panel, fg_color="transparent")
            f_deuda.pack(fill="x", pady=(0, s))
            self.lbl_deuda = ctk.CTkLabel(f_deuda, text="", font=fuente("cuerpo_negrita"), anchor="w")
            self.lbl_deuda.pack(side="left")
            boton_secundario(f_deuda, "Ver fiados", self.ver_fiados, width=100, height=28, font=fuente("pequeña")).pack(side="right")
        self.btn_guardar = boton_primario(self.panel, "Guardar cambios", self.guardar_cambios, height=40)
        self.btn_guardar.pack(fill="x", pady=(s, ESPACIO["xs"]))
        self.btn_eliminar = boton_enlace(self.panel, f"Eliminar {et['singular']}", self.eliminar)
        self.btn_eliminar.pack(anchor="w")
        self._mostrar_panel(False)

    def _mostrar_panel(self, visible):
        if visible:
            self.lbl_vacio.pack_forget()
            self.panel.pack(fill="both", expand=True, padx=ESPACIO["m"], pady=(0, ESPACIO["m"]))
        else:
            self.panel.pack_forget()
            self.lbl_vacio.pack(expand=True)

    # --- datos ---
    def refrescar(self):
        self.tabla.cargar({"id": r[0], "nombre": r[1], "documento": r[2] or "", "telefono": r[3] or ""}
                          for r in self.app.db.contactos.listar(self.tipo))
        if self.seleccionado:
            if self.tabla.seleccionar_por_valor("nombre", self.seleccionado):
                self.mostrar_detalle(self.seleccionado)
            else:
                self.limpiar_seleccion()

    def limpiar_seleccion(self):
        self.tabla.deseleccionar()
        self.seleccionado = None
        self._mostrar_panel(False)

    def _al_seleccionar(self, fila):
        if fila:
            self.mostrar_detalle(str(fila["nombre"]))

    def mostrar_detalle(self, nombre):
        c = self.app.db.contactos.obtener(self.tipo, nombre)
        if c is None:
            self.limpiar_seleccion()
            return
        self.seleccionado = c.nombre
        self.formulario.cargar(c)
        self.lbl_titulo.configure(text=c.nombre)
        es_general = self.tipo == "cliente" and c.nombre == CLIENTE_GENERAL
        self.btn_eliminar.configure(state="disabled" if es_general else "normal")
        if self.tipo == "cliente":
            deuda = self.app.db.boletas.total_por_cobrar(c.nombre)
            self.lbl_deuda.configure(text=f"Deuda pendiente: {moneda(deuda)}",
                                     text_color=COLOR["peligro_hover"] if deuda > 0 else COLOR["exito"])
        self._mostrar_panel(True)

    # --- acciones ---
    def guardar_cambios(self):
        if not self.seleccionado:
            return False
        try:
            d = self.formulario.leer()
        except ValueError:
            return False
        if not self.app.db.contactos.modificar(self.tipo, self.seleccionado, d["nombre"], d["documento"], d["telefono"], d["notas"]):
            messagebox.showerror("Error", f"No se pudo guardar: ¿ya existe otro {ETIQUETAS[self.tipo]['singular']} llamado '{d['nombre']}'?")
            return False
        self.seleccionado = d["nombre"]
        self.app.refrescar_contactos()
        self.app.toast.mostrar(f"{ETIQUETAS[self.tipo]['singular'].capitalize()} '{d['nombre']}' actualizado", "exito")
        return True

    def eliminar(self):
        nombre = self.seleccionado
        if not nombre:
            return
        if not messagebox.askyesno("Eliminar", f"¿Eliminar a {nombre}?\n\nSi tiene boletas registradas solo se ocultará; su historial se conserva."):
            return
        if self.app.db.contactos.eliminar(self.tipo, nombre):
            self.seleccionado = None
            self.app.refrescar_contactos()
            self.app.toast.mostrar(f"'{nombre}' eliminado", "alerta")
        else:
            messagebox.showerror("Error", f"No se puede eliminar a {nombre}.")

    def ver_fiados(self):
        if self.seleccionado:
            self.app.mostrar_pantalla("fiados")
            self.app.pantallas["fiados"].filtrar_cliente(self.seleccionado)

    def nuevo(self):
        et = ETIQUETAS[self.tipo]

        def al_guardar(d):
            if not self.app.db.contactos.agregar(self.tipo, d["nombre"], d["documento"], d["telefono"], d["notas"]):
                messagebox.showerror("Error", f"Ya existe un {et['singular']} llamado '{d['nombre']}'.")
                return False
            self.seleccionado = d["nombre"]
            self.app.refrescar_contactos()
            self.app.toast.mostrar(f"{et['singular'].capitalize()} '{d['nombre']}' creado", "exito")
            return True
        return dialogos.DialogoFormulario(self.app, et["titulo"], lambda padre: FormularioContacto(padre, self.tipo), al_guardar,
                                          texto_guardar="Crear", tamano="380x420")


class PantallaContactos(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self._construir()

    def _construir(self):
        s, m, l = ESPACIO["s"], ESPACIO["m"], ESPACIO["l"]
        enc = Encabezado(self, "Contactos", "Clientes a los que vendes y proveedores a los que compras")
        enc.pack(fill="x", padx=l, pady=(l, m))
        boton_primario(enc.acciones, "+ Nuevo cliente", lambda: self.nuevo("cliente"), height=36).pack(side="left", padx=(0, s))
        boton_primario(enc.acciones, "+ Nuevo proveedor", lambda: self.nuevo("proveedor"), height=36).pack(side="left")

        self.tabs = ctk.CTkTabview(self)
        self.tabs.pack(fill="both", expand=True, padx=l, pady=(0, l))
        self.secciones = {
            "cliente": SeccionContactos(self.tabs.add("Clientes"), self.app, "cliente"),
            "proveedor": SeccionContactos(self.tabs.add("Proveedores"), self.app, "proveedor"),
        }
        for sec in self.secciones.values():
            sec.pack(fill="both", expand=True)

    # --- protocolo con la app ---
    def refrescar_contactos(self, clientes, proveedores):
        for sec in self.secciones.values():
            sec.refrescar()

    def al_mostrar(self):
        self.refrescar_contactos(None, None)

    def limpiar_seleccion(self):
        for sec in self.secciones.values():
            sec.limpiar_seleccion()

    def nuevo(self, tipo):
        self.tabs.set("Clientes" if tipo == "cliente" else "Proveedores")
        return self.secciones[tipo].nuevo()
