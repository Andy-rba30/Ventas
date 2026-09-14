"""Ventanas emergentes reutilizables: calendario, alta rápida de contacto, historial de cliente."""
import tkinter as tk

import customtkinter as ctk
from tkcalendar import Calendar

from agro.servicios.formato import cantidad, moneda
from agro.ui.componentes import Columna, Tabla, boton_exito, boton_primario, boton_secundario
from agro.ui.tema import ESPACIO, fuente


def abrir_calendario_popup(parent, entry_widget):
    """Selector de fecha que escribe 'YYYY-MM-DD' en un Entry de solo lectura."""
    top = tk.Toplevel(parent)
    top.title("Seleccionar Fecha")
    top.geometry("300x300")
    top.grab_set()
    cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd')
    cal.pack(pady=ESPACIO["m"] + 4, expand=True, fill="both")

    def seleccionar():
        entry_widget.configure(state='normal')
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, cal.get_date())
        entry_widget.configure(state='readonly')
        top.destroy()

    boton_exito(top, "Confirmar Fecha", seleccionar).pack(pady=ESPACIO["s"] + 2)


def abrir_popup_contacto(parent, db, tipo, al_guardar):
    """Alta rápida de cliente o proveedor desde Ventas/Compras. al_guardar(nombre) se llama tras insertar."""
    top = ctk.CTkToplevel(parent)
    top.title(f"Nuevo {'Cliente' if tipo == 'cliente' else 'Proveedor'}")
    top.geometry("300x250")
    top.grab_set()
    ctk.CTkLabel(top, text="Nombre/Empresa:").pack(pady=(ESPACIO["s"] + 2, 0))
    e_nom = ctk.CTkEntry(top, width=200); e_nom.pack(pady=ESPACIO["xs"] + 1)
    ctk.CTkLabel(top, text="DNI/RUC/Contacto:").pack(pady=(ESPACIO["xs"] + 1, 0))
    e_doc = ctk.CTkEntry(top, width=200); e_doc.pack(pady=ESPACIO["xs"] + 1)

    def guardar():
        n = e_nom.get().strip().upper()
        if not n: return
        if db.contactos.agregar(tipo, n, e_doc.get().strip(), ""):
            al_guardar(n)
            top.destroy()

    boton_primario(top, "Guardar Rápido", guardar).pack(pady=ESPACIO["m"] - 1)
    e_nom.focus_set()


def abrir_historial_cliente(parent, cliente, filas):
    """Desglose de fiados pendientes. filas: (fecha, producto, cantidad, total)."""
    top = ctk.CTkToplevel(parent)
    top.title(f"Historial de Deudas - {cliente}")
    top.geometry("600x400")
    top.grab_set()

    ctk.CTkLabel(top, text=f"Desglose de deuda: {cliente}", font=fuente("subtitulo")).pack(pady=ESPACIO["m"] - 1)
    tabla = Tabla(top, [
        Columna("fecha", "Fecha", 100), Columna("producto", "Producto", 250),
        Columna("cantidad", "Cantidad", 80, "center"), Columna("subtotal", "Subtotal", 100, "e"),
    ])
    tabla.pack(fill="both", expand=True, padx=ESPACIO["m"] - 1, pady=ESPACIO["s"] + 2)
    tabla.cargar([{"fecha": f, "producto": p, "cantidad": cantidad(c), "subtotal": moneda(t)} for f, p, c, t in filas])
    boton_secundario(top, "Cerrar", top.destroy).pack(pady=ESPACIO["s"] + 2)
