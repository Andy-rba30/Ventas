"""Pantalla Ventas: despacho de productos al contado o al fiado."""
import sqlite3
from tkinter import messagebox

import customtkinter as ctk

from agro.config import CLIENTE_GENERAL
from agro.registro import log
from agro.servicios.formato import cantidad, moneda
from agro.servicios.operaciones import ErrorOperacion
from agro.ui import dialogos
from agro.ui.componentes import boton_exito, boton_fiado, boton_primario
from agro.ui.pantallas.movimiento_base import PantallaMovimiento
from agro.ui.tema import ESPACIO, fuente


class PantallaVentas(PantallaMovimiento):
    TIPO = "ventas"
    TITULO_IZQ = "INVENTARIO (DESPACHO)"
    TITULO_DER = "CARRITO DE VENTAS"
    ETIQUETA_CANT = "Cant (ej. 1/2):"
    COL_PRECIO = "P. Venta"
    COL_STOCK = "Stock Disp."
    COL_PUNIT_CARRITO = "P.Unit"
    PREFIJO_TOTAL = "TOTAL: S/."
    COLOR_TOTAL = "peligro_hover"
    ACTUALIZA_STOCK_CON_CARRITO = True

    def _construir_pie(self, f_acciones):
        m = ESPACIO["m"]
        ctk.CTkLabel(f_acciones, text="Cliente:").pack(anchor="w", padx=m + 4, pady=(ESPACIO["xs"] + 1, 0))
        f_cli = ctk.CTkFrame(f_acciones, fg_color="transparent")
        f_cli.pack(fill="x", padx=m + 4, pady=ESPACIO["xs"] + 1)
        self.combo_cliente = ctk.CTkOptionMenu(f_cli, values=[CLIENTE_GENERAL])
        self.combo_cliente.pack(side="left", fill="x", expand=True)
        boton_primario(f_cli, "➕", self._nuevo_cliente, width=35).pack(side="right", padx=(ESPACIO["xs"] + 1, 0))

        boton_exito(f_acciones, "💰 FINALIZAR VENTA", lambda: self.procesar(fiado=False), height=40,
                    font=fuente("cuerpo_negrita")).pack(fill="x", padx=m + 4, pady=(m - 1, ESPACIO["xs"] + 1))
        boton_fiado(f_acciones, "📒 FINALIZAR FIADO", lambda: self.procesar(fiado=True), height=40,
                    font=fuente("cuerpo_negrita")).pack(fill="x", padx=m + 4, pady=ESPACIO["xs"] + 1)

    def _nuevo_cliente(self):
        def al_guardar(nombre):
            self.app.refrescar_contactos()
            self.combo_cliente.set(nombre)
        dialogos.abrir_popup_contacto(self.app, self.app.db, "cliente", al_guardar)

    # --- productos: el stock mostrado descuenta lo que ya está en el carrito ---
    def _fila_producto(self, p):
        stock_disp = p.stock - self.carrito.cantidad_de(p.nombre)
        tags = ("alerta",) if stock_disp <= p.stock_minimo else ()
        return {"producto": p.nombre, "precio": moneda(p.precio_venta), "stock": cantidad(stock_disp)}, tags

    def _precio_para(self, prod, cant):
        stock_disp = prod.stock - self.carrito.cantidad_de(prod.nombre)
        if stock_disp < cant:
            if not messagebox.askyesno("Advertencia de Stock",
                                       f"Intenta vender más del stock disponible ({cantidad(stock_disp)}). Quedará negativo.\n\n¿Continuar de todos modos?"):
                return None
        return prod.precio_venta

    def refrescar_contactos(self, clientes, proveedores):
        if clientes:
            self.combo_cliente.configure(values=clientes)
            self.combo_cliente.set(CLIENTE_GENERAL if CLIENTE_GENERAL in clientes else clientes[0])

    # --- finalizar ---
    def procesar(self, fiado):
        try:
            tipo = self.app.operaciones.registrar_venta(self.carrito, self.ent_fecha.get(), self.app.encargada_actual(),
                                                        self.combo_cliente.get(), fiado=fiado)
        except ErrorOperacion as e:
            return messagebox.showwarning("Atención", str(e))
        except sqlite3.Error as e:
            log.error("Fallo al registrar venta/fiado: %s", e)
            return messagebox.showerror("Error", f"No se guardó la operación (ningún producto fue descontado):\n{e}")
        self._limpiar_tras_procesar()
        if fiado: self.app.refrescar_fiados()
        messagebox.showinfo("Éxito", f"Operación de {tipo} registrada.")
