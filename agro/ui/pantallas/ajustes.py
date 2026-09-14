"""Pantalla Ajustes: encargadas, respaldo, apariencia y acerca de."""
import os
from tkinter import messagebox

import customtkinter as ctk

from agro import __version__
from agro.config import ENCARGADA_DEFAULT, NOMBRE_APP
from agro.ui.componentes import (Campo, Columna, Encabezado, Seccion, Tabla, boton_alerta, boton_exito,
                                 boton_peligro, boton_primario)
from agro.ui.tema import COLOR, ESPACIO, fuente

APARIENCIAS = {"Claro": "Light", "Oscuro": "Dark", "Sistema": "System"}
_NOMBRE_APARIENCIA = {v: k for k, v in APARIENCIAS.items()}


class PantallaAjustes(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self._construir()

    def _construir(self):
        m, l = ESPACIO["m"], ESPACIO["l"]
        Encabezado(self, "Ajustes", "Encargadas, respaldo de datos y apariencia").pack(fill="x", padx=l, pady=(l, m))
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=l - ESPACIO["s"], pady=(0, m))

        # --- Encargadas ---
        sec = Seccion(self.scroll, "Encargadas", "Quién atiende. La encargada activa se elige en la barra lateral y queda "
                                                 "registrada en cada boleta y pago. Una encargada con historial se desactiva en vez de borrarse.")
        sec.pack(fill="x", pady=(0, m))
        fila = ctk.CTkFrame(sec.cuerpo, fg_color="transparent")
        fila.pack(fill="x")
        self.tabla_encargadas = Tabla(fila, [Columna("nombre", "Nombre", 260)], alto=5)
        self.tabla_encargadas.pack(side="left", fill="x", expand=True)
        acciones = ctk.CTkFrame(fila, fg_color="transparent")
        acciones.pack(side="left", padx=(m, 0), anchor="n")
        self.campo_encargada = Campo(acciones, "Nueva:", ancho=160, obligatorio=True)
        self.campo_encargada.pack(anchor="w", pady=(0, ESPACIO["s"]))
        self.campo_encargada.entry.bind("<Return>", lambda e: self.agregar_encargada())
        boton_primario(acciones, "Agregar", self.agregar_encargada, width=160).pack(anchor="w", pady=(0, ESPACIO["s"]))
        boton_peligro(acciones, "Quitar seleccionada", self.quitar_encargada, width=160).pack(anchor="w")

        # --- Respaldo ---
        sec = Seccion(self.scroll, "Respaldo", "Guarda una copia de la base de datos en la carpeta que elijas, o restaura una copia anterior. "
                                               "Restaurar reemplaza TODOS los datos actuales.")
        sec.pack(fill="x", pady=(0, m))
        self.lbl_ruta_bd = ctk.CTkLabel(sec.cuerpo, text="", font=fuente("cuerpo"), text_color=COLOR["texto_suave"], anchor="w", justify="left")
        self.lbl_ruta_bd.pack(fill="x")
        self.lbl_ultimo_respaldo = ctk.CTkLabel(sec.cuerpo, text="", font=fuente("cuerpo"), anchor="w", justify="left")
        self.lbl_ultimo_respaldo.pack(fill="x", pady=(ESPACIO["xs"], ESPACIO["s"]))
        botones = ctk.CTkFrame(sec.cuerpo, fg_color="transparent")
        botones.pack(anchor="w")
        boton_exito(botones, "💾 Respaldar ahora", self._respaldar, width=180).pack(side="left", padx=(0, ESPACIO["s"]))
        boton_alerta(botones, "📂 Restaurar copia…", self.app.restaurar_bd, width=180).pack(side="left")

        # --- Apariencia ---
        sec = Seccion(self.scroll, "Apariencia", "Se guarda en config.json junto a la base de datos.")
        sec.pack(fill="x", pady=(0, m))
        self.seg_apariencia = ctk.CTkSegmentedButton(sec.cuerpo, values=list(APARIENCIAS), command=self._cambiar_apariencia)
        self.seg_apariencia.pack(anchor="w")

        # --- Acerca de ---
        sec = Seccion(self.scroll, "Acerca de")
        sec.pack(fill="x")
        self.lbl_acerca = ctk.CTkLabel(sec.cuerpo, text="", font=fuente("cuerpo"), anchor="w", justify="left")
        self.lbl_acerca.pack(fill="x")

    # --- refresco ---
    def refrescar(self):
        self.tabla_encargadas.cargar({"nombre": n} for n in self.app.db.contactos.encargadas())
        ruta = os.path.abspath(self.app.db.db_name)
        self.lbl_ruta_bd.configure(text=f"Base de datos: {ruta}")
        ultimo = self.app.prefs.get("ultimo_respaldo")
        self.lbl_ultimo_respaldo.configure(
            text=f"Último respaldo: {ultimo['fecha']}  →  {ultimo['ruta']}" if ultimo else "Último respaldo: todavía no se ha hecho ninguno.")
        self.seg_apariencia.set(_NOMBRE_APARIENCIA.get(self.app.prefs.get("apariencia"), "Claro"))
        self.lbl_acerca.configure(text=f"{NOMBRE_APP}\nVersión {__version__}\nRegistro de actividad: {os.path.join(os.path.dirname(ruta), 'app.log')}")

    al_mostrar = refrescar

    # --- acciones ---
    def agregar_encargada(self):
        try:
            nombre = self.campo_encargada.valor().title()
        except ValueError:
            return
        if self.app.db.contactos.agregar_encargada(nombre):
            self.campo_encargada.limpiar()
            self.app.actualizar_encargadas()
            self.refrescar()
        else:
            messagebox.showerror("Error", f"'{nombre}' ya existe.")

    def quitar_encargada(self):
        fila = self.tabla_encargadas.seleccion()
        if not fila:
            return messagebox.showwarning("Atención", "Selecciona una encargada de la lista.")
        nombre = str(fila["nombre"])
        if nombre == ENCARGADA_DEFAULT:
            return messagebox.showerror("Error", f"No se puede quitar a {ENCARGADA_DEFAULT}.")
        if messagebox.askyesno("Quitar", f"¿Quitar a {nombre}?"):
            if self.app.db.contactos.eliminar_encargada(nombre):
                self.app.actualizar_encargadas()
                self.refrescar()

    def _respaldar(self):
        self.app.respaldar_bd()
        self.refrescar()

    def _cambiar_apariencia(self, etiqueta):
        self.app.cambiar_apariencia(APARIENCIAS[etiqueta])
