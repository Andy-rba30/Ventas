"""Ventanas emergentes reutilizables: calendario, alta rápida de contacto, historial de cliente."""
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk
from tkcalendar import Calendar

from agro.servicios.formato import cantidad, moneda


def abrir_calendario_popup(parent, entry_widget):
    """Selector de fecha que escribe 'YYYY-MM-DD' en un Entry de solo lectura."""
    top = tk.Toplevel(parent)
    top.title("Seleccionar Fecha")
    top.geometry("300x300")
    top.grab_set()
    cal = Calendar(top, selectmode='day', date_pattern='yyyy-mm-dd')
    cal.pack(pady=20, expand=True, fill="both")

    def seleccionar():
        entry_widget.configure(state='normal')
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, cal.get_date())
        entry_widget.configure(state='readonly')
        top.destroy()

    ctk.CTkButton(top, text="Confirmar Fecha", fg_color="#4CAF50", hover_color="#388E3C", command=seleccionar).pack(pady=10)


def abrir_popup_contacto(parent, db, tipo, al_guardar):
    """Alta rápida de cliente o proveedor desde Ventas/Compras. al_guardar(nombre) se llama tras insertar."""
    top = ctk.CTkToplevel(parent)
    top.title(f"Nuevo {'Cliente' if tipo == 'cliente' else 'Proveedor'}")
    top.geometry("300x250")
    top.grab_set()
    ctk.CTkLabel(top, text="Nombre/Empresa:").pack(pady=(10, 0))
    e_nom = ctk.CTkEntry(top, width=200); e_nom.pack(pady=5)
    ctk.CTkLabel(top, text="DNI/RUC/Contacto:").pack(pady=(5, 0))
    e_doc = ctk.CTkEntry(top, width=200); e_doc.pack(pady=5)

    def guardar():
        n = e_nom.get().strip().upper()
        if not n: return
        if db.contactos.agregar(tipo, n, e_doc.get().strip(), ""):
            al_guardar(n)
            top.destroy()

    ctk.CTkButton(top, text="Guardar Rápido", command=guardar).pack(pady=15)


def abrir_historial_cliente(parent, cliente, filas):
    """Desglose de fiados pendientes. filas: (fecha, producto, cantidad, total)."""
    top = ctk.CTkToplevel(parent)
    top.title(f"Historial de Deudas - {cliente}")
    top.geometry("600x400")
    top.grab_set()

    ctk.CTkLabel(top, text=f"Desglose de deuda: {cliente}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=15)

    cols = ("Fecha", "Producto", "Cantidad", "Subtotal")
    tree = ttk.Treeview(top, columns=cols, show="headings")
    for col in cols: tree.heading(col, text=col)
    tree.column("Fecha", width=100); tree.column("Producto", width=250)
    tree.column("Cantidad", width=80, anchor="center"); tree.column("Subtotal", width=100, anchor="e")

    scroll = ttk.Scrollbar(top, orient="vertical", command=tree.yview)
    scroll.pack(side="right", fill="y"); tree.pack(side="left", fill="both", expand=True, padx=15, pady=10)
    tree.configure(yscrollcommand=scroll.set)

    for fecha, producto, cant, total in filas:
        tree.insert("", "end", values=(fecha, producto, cantidad(cant), moneda(total)))
    ctk.CTkButton(top, text="Cerrar", command=top.destroy).pack(pady=10)
