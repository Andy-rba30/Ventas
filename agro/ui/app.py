"""Ventana principal: sidebar, navegación entre pantallas, encargadas y respaldo."""
import os
import shutil
import sqlite3
from tkinter import filedialog, messagebox, simpledialog, ttk

import customtkinter as ctk

from agro import __version__
from agro.config import ENCARGADA_DEFAULT, GEOMETRIA_INICIAL, NOMBRE_APP, RUTA_BD
from agro.db import BaseDatos
from agro.registro import log
from agro.servicios.operaciones import ServicioOperaciones
from agro.servicios.reportes import ServicioReportes
from agro.ui.pantallas.compras import PantallaCompras
from agro.ui.pantallas.contactos import PantallaContactos
from agro.ui.pantallas.fiados import PantallaFiados
from agro.ui.pantallas.inventario import PantallaInventario
from agro.ui.pantallas.reportes import PantallaReportes
from agro.ui.pantallas.ventas import PantallaVentas


class Aplicacion(ctk.CTk):
    def __init__(self, ruta_db=RUTA_BD):
        super().__init__()
        self.title(f"{NOMBRE_APP} v{__version__}")
        self.geometry(GEOMETRIA_INICIAL)
        self.db = BaseDatos(ruta_db)
        self.operaciones = ServicioOperaciones(self.db)
        self.reportes = ServicioReportes(self.db)
        # Los errores dentro de callbacks de Tk no llegan a la consola en el .exe: van al log y a un aviso.
        self.report_callback_exception = self._error_no_controlado

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", font=("Segoe UI", 10), rowheight=30, background="#FFFFFF", fieldbackground="#FFFFFF")
        style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"), background="#E0E0E0")

        self._crear_sidebar()
        self._crear_pantallas()
        self.refrescar_contactos()
        self.refrescar_productos()
        self.refrescar_fiados()
        self.mostrar_pantalla("ventas")

    def _error_no_controlado(self, exc_type, exc_value, exc_tb):
        log.exception("Error no controlado en la interfaz", exc_info=(exc_type, exc_value, exc_tb))
        messagebox.showerror("Error inesperado", f"{exc_type.__name__}: {exc_value}\n\nEl detalle quedó en app.log.")

    # ------------------------------------------------------------------ sidebar
    def _crear_sidebar(self):
        sb = ctk.CTkFrame(self, width=220, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_rowconfigure(8, weight=1)
        self.sidebar_frame = sb

        ctk.CTkLabel(sb, text="Agro-Negocio", font=ctk.CTkFont(size=22, weight="bold"), text_color="#1F6AA5").grid(row=0, column=0, padx=20, pady=(30, 20))

        ctk.CTkLabel(sb, text="Encargada:", font=ctk.CTkFont(size=12, weight="bold")).grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        self.combo_encargada = ctk.CTkOptionMenu(sb, values=[ENCARGADA_DEFAULT])
        self.combo_encargada.grid(row=2, column=0, padx=20, pady=(5, 10))
        self.actualizar_lista_encargadas()

        f_enc = ctk.CTkFrame(sb, fg_color="transparent")
        f_enc.grid(row=3, column=0, padx=20, pady=(0, 15))
        ctk.CTkButton(f_enc, text="+", width=40, command=self.nueva_encargada).pack(side="left", padx=5)
        ctk.CTkButton(f_enc, text="🗑", width=40, fg_color="#F44336", hover_color="#D32F2F", command=self.borrar_encargada).pack(side="left", padx=5)

        nav = [("🛒 Ventas", "ventas"), ("🚚 Compras", "compras"), ("👥 Contactos", "contactos"),
               ("📒 Fiados", "fiados"), ("📝 Inventario", "productos"), ("📊 Reportes", "reportes")]
        self.botones_nav = {}
        for i, (texto, nombre) in enumerate(nav):
            btn = ctk.CTkButton(sb, text=texto, font=ctk.CTkFont(size=14), height=40, command=lambda n=nombre: self.mostrar_pantalla(n))
            btn.grid(row=4 + i, column=0, padx=20, pady=8, sticky="n" if nombre == "productos" else "")
            self.botones_nav[nombre] = btn

        ctk.CTkButton(sb, text="💾 Respaldar BD", fg_color="#4CAF50", hover_color="#388E3C", command=self.respaldar_bd).grid(row=10, column=0, padx=20, pady=(20, 5))
        ctk.CTkButton(sb, text="📂 Restaurar BD", fg_color="#FF9800", hover_color="#F57C00", command=self.restaurar_bd).grid(row=11, column=0, padx=20, pady=(5, 20))

    # ------------------------------------------------------------------ pantallas
    def _crear_pantallas(self):
        self.pantallas = {
            "ventas": PantallaVentas(self, self),
            "compras": PantallaCompras(self, self),
            "contactos": PantallaContactos(self, self),
            "fiados": PantallaFiados(self, self),
            "productos": PantallaInventario(self, self),
            "reportes": PantallaReportes(self, self),
        }
        for p in self.pantallas.values():
            p.grid(row=0, column=1, sticky="nsew")

    def mostrar_pantalla(self, nombre):
        for p in self.pantallas.values():
            p.grid_remove()
        pantalla = self.pantallas[nombre]
        pantalla.grid()
        if hasattr(pantalla, "al_mostrar"):
            pantalla.al_mostrar()

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
        self.pantallas["fiados"].refrescar()

    def refrescar_reportes(self):
        self.pantallas["reportes"].generar()

    # ------------------------------------------------------------------ encargadas
    def encargada_actual(self):
        return self.combo_encargada.get()

    def actualizar_lista_encargadas(self):
        lista = self.db.contactos.encargadas()
        self.combo_encargada.configure(values=lista)
        if lista: self.combo_encargada.set(lista[0])

    def nueva_encargada(self):
        nom = simpledialog.askstring("Nuevo", "Nombre:")
        if nom and self.db.contactos.agregar_encargada(nom.title()):
            self.actualizar_lista_encargadas()

    def borrar_encargada(self):
        nombre = self.combo_encargada.get()
        if messagebox.askyesno("Borrar", f"¿Borrar a {nombre}?"):
            if self.db.contactos.eliminar_encargada(nombre):
                self.actualizar_lista_encargadas()
            else:
                messagebox.showerror("Error", f"No se puede borrar {ENCARGADA_DEFAULT}.")

    # ------------------------------------------------------------------ respaldo
    def respaldar_bd(self):
        fp = filedialog.asksaveasfilename(defaultextension=".db", filetypes=[("SQLite DB", "*.db")], initialfile="Copia_AgroNegocio.db")
        if not fp: return
        try:
            self.db.respaldar_a(fp)
            messagebox.showinfo("Éxito", "Copia guardada en:\n" + fp)
        except (sqlite3.Error, OSError) as e:
            log.error("Fallo al respaldar en %s: %s", fp, e)
            messagebox.showerror("Error", f"Fallo al respaldar: {e}")

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
            self.actualizar_lista_encargadas()
            self.refrescar_contactos()
            self.refrescar_productos()
            self.refrescar_fiados()
