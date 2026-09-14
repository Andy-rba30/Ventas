"""Ventanas emergentes reutilizables: calendario, alta rápida de contacto, historial de cliente."""
import tkinter as tk

import customtkinter as ctk
from tkcalendar import Calendar

from agro.servicios.formato import cantidad, moneda
from agro.ui.componentes import Campo, Columna, Tabla, boton_exito, boton_primario, boton_secundario
from agro.ui.tema import COLOR, ESPACIO, fuente


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


def elegir_opcion(parent, titulo, etiqueta, opciones, actual=None):
    """Diálogo modal con un desplegable. Devuelve la opción elegida o None si se cancela."""
    top = ctk.CTkToplevel(parent)
    top.title(titulo)
    top.geometry("320x180")
    top.grab_set()
    resultado = {"valor": None}
    ctk.CTkLabel(top, text=etiqueta, font=fuente("cuerpo_negrita")).pack(pady=(ESPACIO["m"], ESPACIO["xs"]))
    combo = ctk.CTkOptionMenu(top, values=list(opciones) or ["—"], width=240)
    if actual in opciones:
        combo.set(actual)
    combo.pack(pady=ESPACIO["xs"])
    botones = ctk.CTkFrame(top, fg_color="transparent")
    botones.pack(pady=ESPACIO["m"])

    def aceptar():
        resultado["valor"] = combo.get() if opciones else None
        top.destroy()

    boton_primario(botones, "Aceptar", aceptar, width=110).pack(side="left", padx=ESPACIO["xs"])
    boton_secundario(botones, "Cancelar", top.destroy, width=110).pack(side="left", padx=ESPACIO["xs"])
    top.bind("<Return>", lambda e: aceptar())
    top.bind("<Escape>", lambda e: top.destroy())
    parent.wait_window(top)
    return resultado["valor"]


class DialogoCantidad(ctk.CTkToplevel):
    """Pide la cantidad (y el precio unitario, si es editable) para agregar un producto al carrito.
    No bloquea: al confirmar llama a al_confirmar(cantidad, precio) y se cierra."""

    def __init__(self, parent, producto, precio, unidad, stock_disp, precio_editable, al_confirmar):
        super().__init__(parent)
        self.al_confirmar = al_confirmar
        self.title("Agregar al carrito")
        self.geometry("340x300")
        self.resizable(False, False)
        self.grab_set()

        ctk.CTkLabel(self, text=producto, font=fuente("subtitulo")).pack(pady=(ESPACIO["m"], 0), padx=ESPACIO["m"])
        color = "peligro_hover" if stock_disp <= 0 else "texto_suave"
        ctk.CTkLabel(self, text=f"Stock disponible: {cantidad(stock_disp)} {unidad}", font=fuente("cuerpo"),
                     text_color=COLOR[color]).pack(pady=(0, ESPACIO["s"]))

        self.campo_cantidad = Campo(self, f"Cantidad ({unidad}), acepta fracciones como 1/2:", ancho=280, tipo="cantidad",
                                    horizontal=False, obligatorio=True)
        self.campo_cantidad.pack(padx=ESPACIO["m"], pady=(0, ESPACIO["s"]), fill="x")
        self.campo_precio = Campo(self, "Precio unitario (S/.):", ancho=280, tipo="dinero", horizontal=False, obligatorio=True)
        self.campo_precio.pack(padx=ESPACIO["m"], pady=(0, ESPACIO["s"]), fill="x")
        self.campo_precio.set(f"{precio:.2f}")
        if not precio_editable:
            self.campo_precio.entry.configure(state="disabled")

        botones = ctk.CTkFrame(self, fg_color="transparent")
        botones.pack(pady=ESPACIO["m"])
        boton_primario(botones, "Agregar", self.confirmar, width=130).pack(side="left", padx=ESPACIO["xs"])
        boton_secundario(botones, "Cancelar", self.destroy, width=130).pack(side="left", padx=ESPACIO["xs"])
        self.bind("<Return>", lambda e: self.confirmar())
        self.bind("<Escape>", lambda e: self.destroy())
        self.after(50, self.campo_cantidad.focus)

    def confirmar(self):
        try:
            cant = self.campo_cantidad.valor()
            precio = self.campo_precio.valor()
        except ValueError:
            return
        if cant <= 0:
            self.campo_cantidad._marcar(False)
            return
        if precio < 0:
            self.campo_precio._marcar(False)
            return
        self.destroy()
        self.al_confirmar(cant, precio)


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
