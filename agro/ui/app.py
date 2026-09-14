"""Ventana principal: sidebar de navegación, encargada activa, atajos, apariencia y respaldo."""
import datetime
import os
import re
import shutil
import sqlite3
from functools import partial
from tkinter import filedialog, messagebox

import customtkinter as ctk

from agro import __version__
from agro.config import ENCARGADA_DEFAULT, GEOMETRIA_INICIAL, NOMBRE_APP, RUTA_BD
from agro.db import BaseDatos
from agro.preferencias import Preferencias
from agro.registro import log
from agro.servicios.operaciones import ServicioOperaciones
from agro.servicios.reportes import ServicioReportes
from agro.ui import dialogos, tema
from agro.ui.componentes import BotonNavegacion, Tabla, Toast, boton_secundario
from agro.ui.pantallas.ajustes import PantallaAjustes
from agro.ui.pantallas.contactos import PantallaContactos
from agro.ui.pantallas.fiados import PantallaFiados
from agro.ui.pantallas.inicio import PantallaInicio
from agro.ui.pantallas.inventario import PantallaInventario
from agro.ui.pantallas.movimiento import PantallaMovimiento
from agro.ui.pantallas.reportes import PantallaReportes
from agro.ui.tema import COLOR, ESPACIO, fuente

TAMANO_MINIMO = (1024, 680)

# (texto, nombre de pantalla, fábrica (master, app) -> pantalla, tecla)
NAVEGACION = [
    ("Inicio", "inicio", PantallaInicio, "<F1>"),
    ("Ventas", "ventas", partial(PantallaMovimiento, modo="venta"), "<F2>"),
    ("Compras", "compras", partial(PantallaMovimiento, modo="compra"), "<F3>"),
    ("Fiados", "fiados", PantallaFiados, "<F4>"),
    ("Inventario", "productos", PantallaInventario, "<F5>"),
    ("Contactos", "contactos", PantallaContactos, "<F6>"),
    ("Reportes", "reportes", PantallaReportes, "<F7>"),
    ("Ajustes", "ajustes", PantallaAjustes, "<F8>"),
]


class Aplicacion(ctk.CTk):
    def __init__(self, ruta_db=RUTA_BD):
        super().__init__()
        self.title(f"{NOMBRE_APP} v{__version__}")
        self.db = BaseDatos(ruta_db)
        self.prefs = Preferencias(ruta_db)
        self.operaciones = ServicioOperaciones(self.db)
        self.reportes = ServicioReportes(self.db)
        self.toast = Toast(self)
        self.pantalla_actual = None
        self._encargada = ENCARGADA_DEFAULT
        # Los errores dentro de callbacks de Tk no llegan a la consola en el .exe: van al log y a un aviso.
        self.report_callback_exception = self._error_no_controlado

        self.minsize(*TAMANO_MINIMO)
        self.geometry(self._geometria_inicial())
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.aplicar_apariencia(self.prefs.get("apariencia"))

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._crear_sidebar()
        self._crear_pantallas()
        self._crear_atajos()
        self.actualizar_encargadas()
        self.refrescar_contactos()
        self.refrescar_productos()
        self.refrescar_fiados()
        self.mostrar_pantalla("inicio")

    def _error_no_controlado(self, exc_type, exc_value, exc_tb):
        log.exception("Error no controlado en la interfaz", exc_info=(exc_type, exc_value, exc_tb))
        messagebox.showerror("Error inesperado", f"{exc_type.__name__}: {exc_value}\n\nEl detalle quedó en app.log.")

    # ------------------------------------------------------------------ ventana
    def _geometria_inicial(self):
        guardada = self.prefs.get("geometria")
        if guardada and re.fullmatch(r"\d{3,5}x\d{3,5}([+-]\d+[+-]\d+)?", guardada):
            ancho, alto = (int(v) for v in guardada.split("+")[0].split("-")[0].split("x"))
            if ancho >= TAMANO_MINIMO[0] and alto >= TAMANO_MINIMO[1]:
                return guardada
        return GEOMETRIA_INICIAL

    def cerrar(self):
        try:
            self.prefs.set("geometria", self.geometry())
        finally:
            self.db.cerrar()
            self.destroy()

    def aplicar_apariencia(self, modo):
        ctk.set_appearance_mode(modo)
        tema.aplicar_estilo_treeview(ctk.get_appearance_mode())

    def cambiar_apariencia(self, modo):
        self.prefs.set("apariencia", modo)
        self.aplicar_apariencia(modo)

    # ------------------------------------------------------------------ sidebar
    def _crear_sidebar(self):
        s, m = ESPACIO["s"], ESPACIO["m"]
        sb = ctk.CTkFrame(self, width=220, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_columnconfigure(0, weight=1)
        self.sidebar_frame = sb

        ctk.CTkLabel(sb, text="Agro-Negocio", font=fuente("marca"), text_color=COLOR["primario"]).grid(
            row=0, column=0, padx=m, pady=(ESPACIO["xl"], ESPACIO["l"]), sticky="w")

        self.botones_nav = {}
        for i, (texto, nombre, _, tecla) in enumerate(NAVEGACION, start=1):
            btn = BotonNavegacion(sb, f"{texto}", lambda n=nombre: self.mostrar_pantalla(n))
            btn.grid(row=i, column=0, padx=m, pady=2, sticky="ew")
            self.botones_nav[nombre] = btn
        sb.grid_rowconfigure(len(NAVEGACION) + 1, weight=1)

        f_enc = ctk.CTkFrame(sb, fg_color="transparent")
        f_enc.grid(row=len(NAVEGACION) + 2, column=0, padx=m, pady=(s, m), sticky="ew")
        self.lbl_encargada = ctk.CTkLabel(f_enc, text="", font=fuente("cuerpo"), anchor="w", justify="left", wraplength=190)
        self.lbl_encargada.pack(fill="x")
        boton_secundario(f_enc, "Cambiar encargada", self.elegir_encargada, height=28, font=fuente("pequeña")).pack(anchor="w", pady=(ESPACIO["xs"], 0))

    def _resaltar_nav(self, nombre):
        for n, btn in self.botones_nav.items():
            btn.set_activo(n == nombre)

    # ------------------------------------------------------------------ pantallas
    def _crear_pantallas(self):
        self.pantallas = {nombre: clase(self, self) for _, nombre, clase, _ in NAVEGACION}
        for p in self.pantallas.values():
            p.grid(row=0, column=1, sticky="nsew")

    def mostrar_pantalla(self, nombre):
        for p in self.pantallas.values():
            p.grid_remove()
        pantalla = self.pantallas[nombre]
        pantalla.grid()
        self.pantalla_actual = nombre
        self._resaltar_nav(nombre)
        if hasattr(pantalla, "al_mostrar"):
            pantalla.al_mostrar()

    # ------------------------------------------------------------------ atajos
    def _crear_atajos(self):
        for _, nombre, _, tecla in NAVEGACION:
            self.bind_all(tecla, lambda e, n=nombre: self.mostrar_pantalla(n))
        self.bind_all("<Control-b>", lambda e: self.enfocar_buscador())
        self.bind_all("<Control-B>", lambda e: self.enfocar_buscador())
        self.bind_all("<Escape>", lambda e: self.limpiar_seleccion())

    def enfocar_buscador(self):
        pantalla = self.pantallas.get(self.pantalla_actual)
        buscador = getattr(pantalla, "ent_buscar", None)
        if buscador is not None:
            buscador.focus_set()
            return True
        return False

    def limpiar_seleccion(self):
        pantalla = self.pantallas.get(self.pantalla_actual)
        if pantalla is None:
            return
        if hasattr(pantalla, "limpiar_seleccion"):
            pantalla.limpiar_seleccion()
            return
        for atributo in vars(pantalla).values():
            if isinstance(atributo, Tabla):
                atributo.deseleccionar()

    # Refrescos cruzados: cada pantalla implementa solo los que necesita.
    def refrescar_productos(self):
        for p in self.pantallas.values():
            if hasattr(p, "refrescar_productos"): p.refrescar_productos()

    def refrescar_contactos(self):
        clientes = self.db.contactos.nombres("cliente")
        proveedores = self.db.contactos.nombres("proveedor")
        for p in self.pantallas.values():
            if hasattr(p, "refrescar_contactos"): p.refrescar_contactos(clientes, proveedores)

    def refrescar_fiados(self):
        for p in self.pantallas.values():
            if hasattr(p, "refrescar_fiados"): p.refrescar_fiados()

    def refrescar_reportes(self):
        self.pantallas["reportes"].generar()

    # ------------------------------------------------------------------ encargadas
    def encargada_actual(self):
        return self._encargada

    def set_encargada(self, nombre):
        self._encargada = nombre
        self.lbl_encargada.configure(text=f"Encargada: {nombre}")

    def actualizar_encargadas(self):
        """Tras cambios en la lista: si la activa ya no está, pasa a la primera disponible."""
        lista = self.db.contactos.encargadas()
        if self._encargada not in lista:
            self.set_encargada(lista[0] if lista else ENCARGADA_DEFAULT)
        else:
            self.set_encargada(self._encargada)

    def elegir_encargada(self):
        lista = self.db.contactos.encargadas()
        elegida = dialogos.elegir_opcion(self, "Encargada", "¿Quién atiende ahora?", lista, self._encargada)
        if elegida:
            self.set_encargada(elegida)

    # ------------------------------------------------------------------ respaldo
    def respaldar_bd(self):
        fp = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite DB", "*.db")], initialfile="Copia_AgroNegocio.db")
        if not fp: return False
        try:
            self.db.respaldar_a(fp)
            self.prefs.set("ultimo_respaldo", {"fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "ruta": fp})
            messagebox.showinfo("Éxito", "Copia guardada en:\n" + fp)
            return True
        except (sqlite3.Error, OSError) as e:
            log.error("Fallo al respaldar en %s: %s", fp, e)
            messagebox.showerror("Error", f"Fallo al respaldar: {e}")
            return False

    def restaurar_bd(self):
        fp = filedialog.askopenfilename(filetypes=[("SQLite DB", "*.db")], title="Selecciona el archivo")
        if not fp: return
        if not messagebox.askyesno("⚠️ Advertencia", "Esto reemplazará TODOS los datos actuales.\n¿Continuar?"): return
        ruta_db = self.db.db_name
        try:
            self.db.cerrar()
            # Si quedaran archivos WAL de la BD anterior, corromperían la restaurada.
            for sufijo in ("-wal", "-shm"):
                if os.path.exists(ruta_db + sufijo): os.remove(ruta_db + sufijo)
            shutil.copy(fp, ruta_db)
            log.info("BD restaurada desde %s", fp)
            messagebox.showinfo("Éxito", "Base de datos restaurada.")
        except (sqlite3.Error, OSError) as e:
            log.error("Fallo al restaurar desde %s: %s", fp, e)
            messagebox.showerror("Error", f"Fallo al restaurar: {e}")
        finally:
            self.db = BaseDatos(ruta_db)
            self.operaciones = ServicioOperaciones(self.db)
            self.reportes = ServicioReportes(self.db)
            self.actualizar_encargadas()
            self.refrescar_contactos()
            self.refrescar_productos()
            self.refrescar_fiados()
            if self.pantalla_actual == "ajustes":
                self.pantallas["ajustes"].refrescar()
