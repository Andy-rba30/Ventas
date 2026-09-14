"""Pantalla Compras: ingreso de mercadería por proveedor."""
import sqlite3
from tkinter import messagebox, simpledialog

import customtkinter as ctk

from agro.registro import log
from agro.servicios.formato import cantidad, moneda
from agro.servicios.operaciones import ErrorOperacion
from agro.ui import dialogos
from agro.ui.pantallas.movimiento_base import PantallaMovimiento


class PantallaCompras(PantallaMovimiento):
    TIPO = "compras"
    TITULO_IZQ = "INGRESO DE MERCADERÍA"
    TITULO_DER = "FACTURA / BOLETA COMPRA"
    ETIQUETA_CANT = "Cant (ej. 1.5):"
    COL_PRECIO = "Costo Ref."
    COL_STOCK = "Stock Actual"
    COL_PUNIT_CARRITO = "Costo U."
    PREFIJO_TOTAL = "TOTAL GASTO: S/."
    COLOR_TOTAL = "#2196F3"
    ACTUALIZA_STOCK_CON_CARRITO = False

    def _construir_pie(self, f_acciones):
        ctk.CTkLabel(f_acciones, text="Proveedor:").pack(anchor="w", padx=20, pady=(15, 0))
        f_prov = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_prov.pack(fill="x", padx=20, pady=5)
        self.combo_proveedor = ctk.CTkOptionMenu(f_prov, values=[])
        self.combo_proveedor.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f_prov, text="➕", width=35, command=self._nuevo_proveedor).pack(side="right", padx=(5, 0))

        ctk.CTkButton(f_acciones, text="🚚 PROCESAR ENTRADA", fg_color="#2196F3", hover_color="#1976D2", height=40,
                      font=ctk.CTkFont(weight="bold"), command=self.procesar).pack(fill="x", padx=20, pady=(20, 5))

    def _nuevo_proveedor(self):
        def al_guardar(nombre):
            self.app.refrescar_contactos()
            self.combo_proveedor.set(nombre)
        dialogos.abrir_popup_contacto(self.app, self.app.db, "proveedor", al_guardar)

    def _fila_producto(self, p):
        return (p.nombre, moneda(p.precio_compra), cantidad(p.stock)), ()

    def _precio_para(self, prod, cant):
        costo = simpledialog.askfloat("Costo Compra", f"Precio UNITARIO de compra para {prod.nombre} (S/.):", initialvalue=prod.precio_compra)
        if costo is None or costo <= 0:
            return None
        return costo

    def refrescar_contactos(self, clientes, proveedores):
        if proveedores:
            self.combo_proveedor.configure(values=proveedores)
            self.combo_proveedor.set(proveedores[0])

    def procesar(self):
        try:
            self.app.operaciones.registrar_compra(self.carrito, self.ent_fecha.get(), self.app.encargada_actual(), self.combo_proveedor.get())
        except ErrorOperacion as e:
            return messagebox.showwarning("Atención", str(e))
        except sqlite3.Error as e:
            log.error("Fallo al registrar ENTRADA: %s", e)
            return messagebox.showerror("Error", f"No se guardó el ingreso (ningún stock fue modificado):\n{e}")
        self._limpiar_tras_procesar()
        messagebox.showinfo("Éxito", "Ingreso de mercadería registrado.")
