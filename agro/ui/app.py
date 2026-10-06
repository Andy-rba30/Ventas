"""Ventana principal: sidebar de navegación, encargada activa, atajos, apariencia y respaldo."""
import datetime
import os
import re
import shutil
import sqlite3
import sys
import tkinter as tk
from functools import partial
from tkinter import filedialog, messagebox

import customtkinter as ctk

from agro import __version__
from agro import rutas
from agro.config import ENCARGADA_DEFAULT, GEOMETRIA_INICIAL, NOMBRE_APP
from agro.db import BaseDatos
from agro.preferencias import Preferencias
from agro.registro import log
from agro.servicios.operaciones import ServicioOperaciones
from agro.servicios.reportes import ServicioReportes
from agro.servicios import boleta_pdf, sistema
from agro.servicios.respaldos import respaldar_automatico
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
    def __init__(self, ruta_db=None):
        super().__init__()
        self.title(f"{NOMBRE_APP} v{__version__}")
        self._poner_icono()
        ruta_db = ruta_db or rutas.ruta_bd()
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

    def _poner_icono(self):
        """Icono de la ventana (assets/). Si falta el archivo o Tk no lo acepta, se sigue sin icono."""
        try:
            if sys.platform.startswith("win"):
                self.iconbitmap(rutas.ruta_recurso(os.path.join("assets", "icono.ico")))
            self._icono = tk.PhotoImage(file=rutas.ruta_recurso(os.path.join("assets", "icono.png")))
            self.iconphoto(True, self._icono)
        except (tk.TclError, OSError) as e:
            log.warning("No se pudo cargar el icono de la ventana: %s", e)

    def cerrar(self):
        try:
            self.prefs.set("geometria", self.geometry())
            self.respaldo_automatico()
        finally:
            self.db.cerrar()
            self.destroy()

    def respaldo_automatico(self):
        """Copia la BD a backups/ con rotación. Nunca impide cerrar: los fallos van al log."""
        try:
            ruta = respaldar_automatico(self.db)
        except (sqlite3.Error, OSError) as e:
            log.error("Fallo el respaldo automático: %s", e)
            return None
        if ruta:
            self.prefs.set("ultimo_respaldo", {"fecha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "ruta": ruta})
        return ruta

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

    def imprimir_boleta(self, boleta_id, abrir=True):
        """Genera el PDF de la boleta en boletas/ junto a la BD y lo abre con el visor del sistema.
        Devuelve la ruta o None si no se pudo."""
        b = self.db.boletas.obtener(boleta_id)
        if b is None:
            messagebox.showwarning("Atención", "Esa boleta ya no existe.")
            return None
        ruta = boleta_pdf.ruta_para(self.db.db_name, b.id)
        try:
            boleta_pdf.generar(b, self.prefs.get("negocio"), ruta)
        except ImportError:
            log.error("reportlab no está instalado; no se puede generar la boleta PDF")
            messagebox.showerror("Falta un componente", "Para imprimir boletas hace falta instalar reportlab:\n\n    pip install reportlab")
            return None
        except OSError as e:
            log.error("Fallo al generar la boleta %s en %s: %s", boleta_id, ruta, e)
            messagebox.showerror("Error", f"No se pudo guardar la boleta:\n{e}")
            return None
        log.info("Boleta #%s generada en %s", b.id, ruta)
        if abrir and not sistema.abrir_archivo(ruta):
            messagebox.showinfo("Boleta guardada", f"No se encontró un visor de PDF. La boleta quedó en:\n{ruta}")
        self.toast.mostrar(f"Boleta N° {b.id:06d} lista para imprimir", "exito")
        return ruta

    def restaurar_bd(self):
        fp = filedialog.askopenfilename(filetypes=[("SQLite DB", "*.db")], title="Selecciona el archivo")
        if not fp: return False
        return self.restaurar_desde(fp)

    def restaurar_desde(self, ruta_copia):
        """Reemplaza la BD actual por `ruta_copia` tras confirmar. Antes guarda una copia automática de
        los datos actuales en backups/. Devuelve True si se restauró."""
        ruta_db = self.db.db_name
        if os.path.abspath(ruta_copia) == os.path.abspath(ruta_db):
            messagebox.showerror("Error", "Esa es la base de datos en uso, no una copia.")
            return False
        if not messagebox.askyesno("⚠️ Advertencia", "Esto reemplazará TODOS los datos actuales por la copia:\n"
                                                    f"{ruta_copia}\n\n¿Continuar?"):
            return False
        restaurada = False
        try:
            self.respaldo_automatico()  # red de seguridad: los datos actuales quedan en backups/
            self.db.cerrar()
            # Si quedaran archivos WAL de la BD anterior, corromperían la restaurada.
            for sufijo in ("-wal", "-shm"):
                if os.path.exists(ruta_db + sufijo): os.remove(ruta_db + sufijo)
            shutil.copy(ruta_copia, ruta_db)
            log.info("BD restaurada desde %s", ruta_copia)
            messagebox.showinfo("Éxito", "Base de datos restaurada.")
            restaurada = True
        except (sqlite3.Error, OSError) as e:
            log.error("Fallo al restaurar desde %s: %s", ruta_copia, e)
            messagebox.showerror("Error", f"Fallo al restaurar: {e}")
        finally:
            self.db = BaseDatos(ruta_db)
            self.operaciones = ServicioOperaciones(self.db)
            self.reportes = ServicioReportes(self.db)
            self.actualizar_encargadas()
            self.refrescar_contactos()
            self.refrescar_productos()
            self.refrescar_fiados()
            self.refrescar_reportes()
            if self.pantalla_actual == "ajustes":
                self.pantallas["ajustes"].refrescar()
        return restaurada
