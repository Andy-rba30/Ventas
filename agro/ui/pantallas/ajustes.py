"""Pantalla Ajustes: encargadas, datos del negocio, respaldo manual y automático, apariencia y acerca de."""
import os
from tkinter import messagebox

import customtkinter as ctk

from agro import __version__
from agro.config import ENCARGADA_DEFAULT, NOMBRE_APP
from agro.servicios import respaldos, sistema
from agro.servicios.formato import tamano_archivo
from agro.ui.componentes import (Campo, Columna, Encabezado, Seccion, Tabla, boton_alerta, boton_exito,
                                 boton_peligro, boton_primario, boton_secundario)
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
        Encabezado(self, "Ajustes", "Encargadas, datos del negocio, respaldo de datos y apariencia").pack(fill="x", padx=l, pady=(l, m))
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

        # --- Datos del negocio ---
        sec = Seccion(self.scroll, "Datos del negocio", "Aparecen en la cabecera de la boleta imprimible (PDF de 80 mm). "
                                                        "Si el nombre queda vacío se usa el nombre del programa.")
        sec.pack(fill="x", pady=(0, m))
        fila = ctk.CTkFrame(sec.cuerpo, fg_color="transparent")
        fila.pack(fill="x")
        self.campo_negocio_nombre = Campo(fila, "Nombre:", ancho=300)
        self.campo_negocio_nombre.pack(side="left", padx=(0, m))
        self.campo_negocio_ruc = Campo(fila, "RUC:", ancho=140)
        self.campo_negocio_ruc.pack(side="left")
        fila2 = ctk.CTkFrame(sec.cuerpo, fg_color="transparent")
        fila2.pack(fill="x", pady=(ESPACIO["s"], 0))
        self.campo_negocio_direccion = Campo(fila2, "Dirección:", ancho=480)
        self.campo_negocio_direccion.pack(side="left", padx=(0, m))
        boton_primario(fila2, "Guardar datos", self.guardar_negocio, width=140).pack(side="left")

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

        # --- Respaldos automáticos ---
        sec = Seccion(self.scroll, "Respaldos automáticos",
                      f"Cada vez que se cierra el programa se guarda una copia en la carpeta backups/ junto a la base de datos "
                      f"y se conservan las {respaldos.CONSERVAR} más recientes. Las copias previas a una actualización no se borran. "
                      "Para restaurar una, selecciónala y confirma; antes se guarda una copia de los datos actuales.")
        sec.pack(fill="x", pady=(0, m))
        fila = ctk.CTkFrame(sec.cuerpo, fg_color="transparent")
        fila.pack(fill="x")
        self.tabla_respaldos = Tabla(fila, [Columna("fecha", "Fecha", 140, estirar=False), Columna("tipo", "Tipo", 120, estirar=False),
                                            Columna("tamano", "Tamaño", 90, "e", estirar=False), Columna("nombre", "Archivo", 300),
                                            Columna("ruta", "", oculta=True)], alto=6)
        self.tabla_respaldos.pack(side="left", fill="x", expand=True)
        acciones = ctk.CTkFrame(fila, fg_color="transparent")
        acciones.pack(side="left", padx=(m, 0), anchor="n")
        boton_exito(acciones, "💾 Respaldar ahora aquí", self._respaldar_automatico, width=190).pack(anchor="w", pady=(0, ESPACIO["s"]))
        boton_alerta(acciones, "↩ Restaurar seleccionada", self.restaurar_seleccionado, width=190).pack(anchor="w", pady=(0, ESPACIO["s"]))
        boton_secundario(acciones, "Abrir carpeta", self._abrir_carpeta, width=190).pack(anchor="w")
        self.lbl_respaldos = ctk.CTkLabel(sec.cuerpo, text="", font=fuente("cuerpo"), text_color=COLOR["texto_suave"], anchor="w", justify="left")
        self.lbl_respaldos.pack(fill="x", pady=(ESPACIO["xs"], 0))

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
        self.refrescar_respaldos()
        negocio = self.app.prefs.get("negocio")
        self.campo_negocio_nombre.set(negocio["nombre"])
        self.campo_negocio_ruc.set(negocio["ruc"])
        self.campo_negocio_direccion.set(negocio["direccion"])
        self.seg_apariencia.set(_NOMBRE_APARIENCIA.get(self.app.prefs.get("apariencia"), "Claro"))
        self.lbl_acerca.configure(text=f"{NOMBRE_APP}\nVersión {__version__}\nRegistro de actividad: {os.path.join(os.path.dirname(ruta), 'app.log')}")

    def refrescar_respaldos(self):
        carpeta = respaldos.carpeta_de(self.app.db.db_name)
        lista = respaldos.listar_respaldos(carpeta)
        self.tabla_respaldos.cargar({"fecha": r.fecha.strftime("%d/%m/%Y %H:%M"), "tipo": "Automático" if r.automatico else "Otra copia",
                                     "tamano": tamano_archivo(r.tamano), "nombre": r.nombre, "ruta": r.ruta} for r in lista)
        self.lbl_respaldos.configure(text=f"Carpeta: {carpeta}" if carpeta else "La base de datos en memoria no se respalda.")

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

    def guardar_negocio(self):
        self.app.prefs.set("negocio", {"nombre": self.campo_negocio_nombre.get(), "ruc": self.campo_negocio_ruc.get(),
                                       "direccion": self.campo_negocio_direccion.get()})
        self.app.toast.mostrar("Datos del negocio guardados", "exito")

    def _respaldar(self):
        self.app.respaldar_bd()
        self.refrescar()

    def _respaldar_automatico(self):
        ruta = self.app.respaldo_automatico()
        if ruta:
            self.app.toast.mostrar("Copia guardada en backups/", "exito")
        else:
            messagebox.showerror("Error", "No se pudo guardar la copia. Revisa app.log.")
        self.refrescar()

    def restaurar_seleccionado(self):
        fila = self.tabla_respaldos.seleccion()
        if not fila:
            return messagebox.showwarning("Atención", "Selecciona una copia de la lista.")
        if self.app.restaurar_desde(str(fila["ruta"])):
            self.app.toast.mostrar("Datos restaurados desde la copia.", "exito")
        self.refrescar()

    def _abrir_carpeta(self):
        carpeta = respaldos.carpeta_de(self.app.db.db_name)
        if not carpeta:
            return
        os.makedirs(carpeta, exist_ok=True)
        if not sistema.abrir_archivo(carpeta):
            messagebox.showinfo("Carpeta de respaldos", carpeta)

    def _cambiar_apariencia(self, etiqueta):
        self.app.cambiar_apariencia(APARIENCIAS[etiqueta])
