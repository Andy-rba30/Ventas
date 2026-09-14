"""Componentes reutilizables de la interfaz. Todas las pantallas construyen su UI con esto
en vez de usar ttk.Treeview, colores hex o CTkFont directamente."""
import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

import customtkinter as ctk

from agro.servicios.formato import parse_cantidad, parse_dinero
from agro.ui.tema import COLOR, ESPACIO, FUENTE_TABLA_NEGRITA, fuente


# ----------------------------------------------------------------------------- Tabla
@dataclass
class Columna:
    clave: str
    titulo: str
    ancho: int = 100
    alineacion: str = "w"      # w | center | e
    oculta: bool = False
    estirar: bool = True


class Tabla(ctk.CTkFrame):
    """Treeview + scrollbar vertical + estilo del tema.

    Las filas se cargan como dicts {clave: valor} (o secuencias en el orden de las
    columnas). Con arbol=True las filas pueden anidarse (padre/hijo).
    on_select(fila | None) y on_doble_clic(event) son opcionales.
    """

    def __init__(self, parent, columnas, on_select=None, on_doble_clic=None, alto=None, arbol=False, **kw):
        kw.setdefault("fg_color", "transparent")
        super().__init__(parent, **kw)
        self.columnas = list(columnas)
        self.claves = [c.clave for c in self.columnas]
        self._on_select = on_select

        opciones = dict(columns=self.claves, show="tree headings" if arbol else "headings")
        if alto:
            opciones["height"] = alto
        self.tree = ttk.Treeview(self, **opciones)
        self.scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scroll.set)
        self.scroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        if arbol:
            self.tree.column("#0", width=40, stretch=tk.NO, anchor="center")
            self.tree.heading("#0", text="Ver")
        for c in self.columnas:
            self.tree.heading(c.clave, text=c.titulo)
            if c.oculta:
                self.tree.column(c.clave, width=0, minwidth=0, stretch=tk.NO)
            else:
                self.tree.column(c.clave, width=c.ancho, anchor=c.alineacion, stretch=c.estirar)

        # Etiquetas de fila con significado fijo en toda la app
        self.tree.tag_configure("alerta", foreground=COLOR["peligro_hover"], font=FUENTE_TABLA_NEGRITA)
        self.tree.tag_configure("resaltada", background=COLOR["resaltado_suave"], font=FUENTE_TABLA_NEGRITA)

        if on_select:
            self.tree.bind("<<TreeviewSelect>>", lambda e: on_select(self.seleccion()))
        if on_doble_clic:
            self.tree.bind("<Double-1>", on_doble_clic)

    # --- carga ---
    def _a_valores(self, fila):
        if isinstance(fila, dict):
            return [fila.get(k, "") for k in self.claves]
        return list(fila)

    def limpiar(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)

    def insertar(self, fila, padre="", tags=(), texto="", abierto=False):
        return self.tree.insert(padre, "end", text=texto, values=self._a_valores(fila), tags=tuple(tags), open=abierto)

    def cargar(self, filas, tags=None):
        """Reemplaza el contenido. tags: callable(fila) -> tupla de etiquetas, opcional."""
        self.limpiar()
        for fila in filas:
            self.insertar(fila, tags=tags(fila) if tags else ())

    # --- lectura ---
    def iids(self, padre=""):
        return self.tree.get_children(padre)

    def hijos(self, iid):
        return self.tree.get_children(iid)

    def padre(self, iid):
        return self.tree.parent(iid)

    def valores(self, iid):
        return dict(zip(self.claves, self.tree.item(iid)["values"]))

    def indice(self, iid):
        return self.tree.index(iid)

    def vacia(self):
        return not self.tree.get_children()

    # --- selección ---
    def iid_seleccionado(self):
        sel = self.tree.selection()
        return sel[0] if sel else None

    def iids_seleccionados(self):
        return self.tree.selection()

    def seleccion(self):
        iid = self.iid_seleccionado()
        return self.valores(iid) if iid else None

    def seleccionar_iid(self, iid):
        self.tree.selection_set(iid)
        self.tree.focus(iid)
        self.tree.see(iid)

    def seleccionar_por_valor(self, clave, valor):
        """Marca la primera fila (de primer nivel) cuyo valor en `clave` coincide. Devuelve True si la encontró."""
        for iid in self.tree.get_children():
            if str(self.valores(iid).get(clave)) == str(valor):
                self.seleccionar_iid(iid)
                return True
        return False

    def deseleccionar(self):
        self.tree.selection_remove(*self.tree.selection())


# ----------------------------------------------------------------------------- Tarjeta
class Tarjeta(ctk.CTkLabel):
    """Indicador con título y valor, sobre un fondo suave."""

    def __init__(self, parent, titulo, valor="", color="neutro", ancho=200, alto=60, **kw):
        self.titulo = titulo
        super().__init__(parent, text=f"{titulo}\n{valor}", font=fuente("destacado"), fg_color=COLOR[color],
                         text_color=COLOR["texto_oscuro"], width=ancho, height=alto, corner_radius=ESPACIO["s"], **kw)

    def set_valor(self, valor, color=None):
        self.configure(text=f"{self.titulo}\n{valor}")
        if color:
            self.configure(fg_color=COLOR[color])


# ----------------------------------------------------------------------------- Encabezado
class Encabezado(ctk.CTkFrame):
    """Título de sección (con subtítulo opcional) y una zona de acciones a la derecha."""

    def __init__(self, parent, titulo, subtitulo=None, color=None, **kw):
        kw.setdefault("fg_color", "transparent")
        super().__init__(parent, **kw)
        textos = ctk.CTkFrame(self, fg_color="transparent")
        textos.pack(side="left", fill="x", expand=True)
        self.lbl_titulo = ctk.CTkLabel(textos, text=titulo, font=fuente("titulo"), text_color=COLOR[color] if color else None, anchor="w")
        self.lbl_titulo.pack(anchor="w")
        self.lbl_subtitulo = None
        if subtitulo:
            self.lbl_subtitulo = ctk.CTkLabel(textos, text=subtitulo, font=fuente("cuerpo"), text_color=COLOR["texto_suave"], anchor="w")
            self.lbl_subtitulo.pack(anchor="w")
        self.acciones = ctk.CTkFrame(self, fg_color="transparent")
        self.acciones.pack(side="right")

    def set_titulo(self, texto):
        self.lbl_titulo.configure(text=texto)


# ----------------------------------------------------------------------------- Campo
class Campo(ctk.CTkFrame):
    """Etiqueta + entrada con validación visual.
    tipo: 'texto' | 'numero' | 'cantidad' (acepta 1/2) | 'dinero' (acepta 'S/. 12.50')."""

    _PARSERS = {"texto": lambda t: t, "numero": float, "cantidad": parse_cantidad, "dinero": parse_dinero}

    def __init__(self, parent, etiqueta, ancho=120, tipo="texto", horizontal=True, obligatorio=False, **kw):
        kw.setdefault("fg_color", "transparent")
        super().__init__(parent, **kw)
        self.tipo = tipo
        self.obligatorio = obligatorio
        self.lbl = ctk.CTkLabel(self, text=etiqueta, font=fuente("cuerpo"))
        self.entry = ctk.CTkEntry(self, width=ancho)
        self._borde_normal = self.entry.cget("border_color")
        if horizontal:
            self.lbl.pack(side="left", padx=(0, ESPACIO["xs"]))
            self.entry.pack(side="left")
        else:
            self.lbl.pack(anchor="w")
            self.entry.pack(fill="x")
        self.entry.bind("<FocusOut>", lambda e: self.validar())
        self.entry.bind("<KeyRelease>", lambda e: self._marcar(True))

    def get(self):
        return self.entry.get().strip()

    def set(self, valor):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, "" if valor is None else str(valor))
        self._marcar(True)

    def limpiar(self):
        self.set("")

    def valor(self):
        """Valor convertido según el tipo. Lanza ValueError (y marca el campo) si no es válido.
        Un campo no obligatorio vacío devuelve None."""
        texto = self.get()
        if not texto:
            if self.obligatorio:
                self._marcar(False)
                raise ValueError(f"{self.lbl.cget('text')} es obligatorio")
            return None
        try:
            v = self._PARSERS[self.tipo](texto)
        except ValueError:
            self._marcar(False)
            raise
        self._marcar(True)
        return v

    def validar(self):
        try:
            self.valor()
            return True
        except ValueError:
            return False

    def _marcar(self, ok):
        self.entry.configure(border_color=self._borde_normal if ok else COLOR["peligro"])

    def focus(self):
        self.entry.focus_set()


# ----------------------------------------------------------------------------- Botones
def _boton(parent, texto, command, color, hover, text_color=None, **kw):
    opciones = dict(text=texto, command=command, fg_color=COLOR[color], hover_color=COLOR[hover])
    if text_color:
        opciones["text_color"] = text_color
    opciones.update(kw)
    return ctk.CTkButton(parent, **opciones)


def boton_primario(parent, texto, command, **kw):
    return _boton(parent, texto, command, "primario", "primario_hover", **kw)


def boton_info(parent, texto, command, **kw):
    return _boton(parent, texto, command, "info", "info_hover", **kw)


def boton_exito(parent, texto, command, **kw):
    return _boton(parent, texto, command, "exito", "exito_hover", **kw)


def boton_alerta(parent, texto, command, **kw):
    return _boton(parent, texto, command, "alerta", "alerta_hover", **kw)


def boton_fiado(parent, texto, command, **kw):
    return _boton(parent, texto, command, "fiado", "fiado_hover", text_color=COLOR["texto_oscuro"], **kw)


def boton_peligro(parent, texto, command, **kw):
    return _boton(parent, texto, command, "peligro", "peligro_hover", **kw)


def boton_secundario(parent, texto, command, **kw):
    kw.setdefault("fg_color", "transparent")
    kw.setdefault("border_width", 1)
    kw.setdefault("border_color", COLOR["primario"])
    kw.setdefault("text_color", (COLOR["primario"], "#FFFFFF"))
    kw.setdefault("hover_color", COLOR["neutro"])
    return ctk.CTkButton(parent, text=texto, command=command, **kw)


# ----------------------------------------------------------------------------- Toast
class Toast:
    """Aviso no bloqueante en la esquina inferior derecha de una ventana."""

    _COLORES = {"info": "info", "exito": "exito", "alerta": "alerta", "error": "peligro"}

    def __init__(self, ventana):
        self.ventana = ventana
        self._label = None
        self._timer = None

    def mostrar(self, texto, tipo="info", duracion_ms=2500):
        self.ocultar()
        self._label = ctk.CTkLabel(self.ventana, text=texto, font=fuente("cuerpo_negrita"),
                                   fg_color=COLOR[self._COLORES.get(tipo, "info")], text_color="#FFFFFF",
                                   corner_radius=ESPACIO["s"], padx=ESPACIO["m"], pady=ESPACIO["s"])
        self._label.place(relx=1.0, rely=1.0, anchor="se", x=-ESPACIO["m"], y=-ESPACIO["m"])
        self._timer = self.ventana.after(duracion_ms, self.ocultar)

    def ocultar(self):
        if self._timer:
            try: self.ventana.after_cancel(self._timer)
            except (ValueError, tk.TclError): pass
            self._timer = None
        if self._label is not None:
            try: self._label.destroy()
            except tk.TclError: pass
            self._label = None
