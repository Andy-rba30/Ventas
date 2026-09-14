"""Pantalla Inventario en maestro-detalle: tabla de productos a la izquierda, panel de
edición a la derecha; el alta abre un diálogo con el mismo formulario."""
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from agro.config import UMBRAL_BAJO_STOCK, UNIDADES
from agro.servicios.formato import cantidad, moneda
from agro.ui import dialogos
from agro.ui.componentes import Campo, Columna, Encabezado, Tabla, boton_enlace, boton_primario
from agro.ui.tema import COLOR, ESPACIO, fuente


class FormularioProducto(ctk.CTkFrame):
    """Campos verticales de un producto. leer() valida y devuelve un dict."""

    def __init__(self, parent, **kw):
        kw.setdefault("fg_color", "transparent")
        super().__init__(parent, **kw)
        ancho = 260
        self.nombre = Campo(self, "Nombre", ancho=ancho, horizontal=False, obligatorio=True)
        self.nombre.pack(fill="x", pady=(0, ESPACIO["s"]))
        f_unidad = ctk.CTkFrame(self, fg_color="transparent")
        f_unidad.pack(fill="x", pady=(0, ESPACIO["s"]))
        ctk.CTkLabel(f_unidad, text="Unidad", font=fuente("cuerpo")).pack(anchor="w")
        self.unidad = ctk.CTkOptionMenu(f_unidad, values=UNIDADES, width=ancho)
        self.unidad.pack(anchor="w")
        self.precio_venta = Campo(self, "Precio de venta (S/.)", ancho=ancho, tipo="dinero", horizontal=False, obligatorio=True)
        self.precio_venta.pack(fill="x", pady=(0, ESPACIO["s"]))
        self.precio_compra = Campo(self, "Precio de compra / costo (S/.)", ancho=ancho, tipo="dinero", horizontal=False)
        self.precio_compra.pack(fill="x", pady=(0, ESPACIO["s"]))
        self.stock = Campo(self, "Stock (acepta fracciones, ej. 1/2)", ancho=ancho, tipo="cantidad", horizontal=False, obligatorio=True)
        self.stock.pack(fill="x", pady=(0, ESPACIO["s"]))
        self.stock_minimo = Campo(self, "Stock mínimo (aviso de reposición)", ancho=ancho, tipo="cantidad", horizontal=False)
        self.stock_minimo.pack(fill="x", pady=(0, ESPACIO["s"]))
        self.limpiar()

    def cargar(self, p):
        self.nombre.set(p.nombre)
        self.unidad.set(p.unidad if p.unidad in UNIDADES else UNIDADES[0])
        self.precio_venta.set(f"{p.precio_venta:.2f}")
        self.precio_compra.set(f"{p.precio_compra:.2f}")
        self.stock.set(cantidad(p.stock))
        self.stock_minimo.set(cantidad(p.stock_minimo))

    def limpiar(self):
        for c in (self.nombre, self.precio_venta, self.precio_compra, self.stock):
            c.limpiar()
        self.unidad.set(UNIDADES[0])
        self.stock_minimo.set(cantidad(UMBRAL_BAJO_STOCK))

    def leer(self):
        datos = {
            "nombre": self.nombre.valor().upper(),
            "unidad": self.unidad.get(),
            "precio_venta": self.precio_venta.valor(),
            "precio_compra": self.precio_compra.valor() or 0.0,
            "stock": self.stock.valor(),
            "stock_minimo": self.stock_minimo.valor(),
        }
        if datos["stock_minimo"] is None:
            datos["stock_minimo"] = UMBRAL_BAJO_STOCK
        if datos["precio_venta"] <= 0:
            self.precio_venta._marcar(False)
            raise ValueError("El precio de venta debe ser mayor a cero")
        if datos["precio_compra"] < 0 or datos["stock"] < 0 or datos["stock_minimo"] < 0:
            raise ValueError("Los valores no pueden ser negativos")
        return datos

    def enfocar(self):
        self.nombre.focus()


class PantallaInventario(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self.app = app
        self.seleccionado = None      # nombre del producto en el panel de detalle
        self.mostrar_inactivos = tk.BooleanVar(value=False)
        self._construir()

    # ------------------------------------------------------------------ construcción
    def _construir(self):
        s, m, l = ESPACIO["s"], ESPACIO["m"], ESPACIO["l"]
        enc = Encabezado(self, "Inventario", "Precios, stock y mínimos de reposición de cada producto")
        enc.pack(fill="x", padx=l, pady=(l, m))
        self.ent_buscar = ctk.CTkEntry(enc.acciones, placeholder_text="Buscar producto", width=220)
        self.ent_buscar.pack(side="left", padx=(0, s))
        self.ent_buscar.bind("<KeyRelease>", lambda e: self.refrescar_productos())
        boton_primario(enc.acciones, "+ Nuevo producto", self.nuevo_producto, height=36).pack(side="left")

        cuerpo = ctk.CTkFrame(self, fg_color="transparent")
        cuerpo.pack(fill="both", expand=True, padx=l, pady=(0, l))
        cuerpo.grid_columnconfigure(0, weight=13, uniform="col")
        cuerpo.grid_columnconfigure(1, weight=7, uniform="col")
        cuerpo.grid_rowconfigure(0, weight=1)

        # --- izquierda: tabla ---
        f_izq = ctk.CTkFrame(cuerpo)
        f_izq.grid(row=0, column=0, sticky="nsew", padx=(0, s))
        barra = ctk.CTkFrame(f_izq, fg_color="transparent")
        barra.pack(fill="x", padx=m, pady=(m, s))
        self.lbl_resumen = ctk.CTkLabel(barra, text="", font=fuente("cuerpo"), text_color=COLOR["texto_suave"])
        self.lbl_resumen.pack(side="left")
        ctk.CTkCheckBox(barra, text="Mostrar inactivos", variable=self.mostrar_inactivos, command=self.refrescar_productos,
                        font=fuente("cuerpo")).pack(side="right")
        self.tabla_productos = Tabla(f_izq, [
            Columna("producto", "Producto", 190),
            Columna("unidad", "Unidad", 55, "center", estirar=False),
            Columna("stock", "Stock", 70, "e", estirar=False),
            Columna("minimo", "Mínimo", 60, "e", estirar=False),
            Columna("precio_venta", "P. Venta", 80, "e", estirar=False),
            Columna("precio_compra", "P. Compra", 80, "e", estirar=False),
            Columna("margen", "Margen %", 70, "e", estirar=False),
        ], on_select=self._al_seleccionar)
        self.tabla_productos.pack(fill="both", expand=True, padx=m, pady=(0, m))

        # --- derecha: detalle ---
        self.f_der = ctk.CTkFrame(cuerpo)
        self.f_der.grid(row=0, column=1, sticky="nsew", padx=(s, 0))
        self.lbl_vacio = ctk.CTkLabel(self.f_der, text="Selecciona un producto\no crea uno nuevo", font=fuente("cuerpo"),
                                      text_color=COLOR["texto_suave"], justify="center")
        self.panel = ctk.CTkFrame(self.f_der, fg_color="transparent")
        self.lbl_titulo_panel = ctk.CTkLabel(self.panel, text="", font=fuente("subtitulo"), anchor="w")
        self.lbl_titulo_panel.pack(fill="x", pady=(m, s))
        self.lbl_estado = ctk.CTkLabel(self.panel, text="", font=fuente("pequeña"), text_color=COLOR["texto_suave"], anchor="w")
        self.lbl_estado.pack(fill="x", pady=(0, s))
        self.formulario = FormularioProducto(self.panel)
        self.formulario.pack(fill="x")
        self.btn_guardar = boton_primario(self.panel, "Guardar cambios", self.guardar_cambios, height=40)
        self.btn_guardar.pack(fill="x", pady=(s, ESPACIO["xs"]))
        self.btn_estado = boton_enlace(self.panel, "Desactivar producto", self.alternar_activo)
        self.btn_estado.pack(anchor="w")
        self._mostrar_panel(False)

    def _mostrar_panel(self, visible):
        if visible:
            self.lbl_vacio.pack_forget()
            self.panel.pack(fill="both", expand=True, padx=ESPACIO["m"], pady=(0, ESPACIO["m"]))
        else:
            self.panel.pack_forget()
            self.lbl_vacio.pack(expand=True)

    # ------------------------------------------------------------------ protocolo con la app
    def al_mostrar(self):
        self.ent_buscar.focus_set()

    def limpiar_seleccion(self):
        self.tabla_productos.deseleccionar()
        self.seleccionado = None
        self._mostrar_panel(False)

    def refrescar_productos(self):
        filtro = self.ent_buscar.get().strip().lower()
        productos = self.app.db.productos.listar(incluir_inactivos=self.mostrar_inactivos.get())
        filas = []
        for p in productos:
            if filtro and filtro not in p.nombre.lower():
                continue
            margen = p.margen_pct
            filas.append({
                "producto": p.nombre, "unidad": p.unidad, "stock": cantidad(p.stock), "minimo": cantidad(p.stock_minimo),
                "precio_venta": moneda(p.precio_venta), "precio_compra": moneda(p.precio_compra),
                "margen": f"{margen:.0f} %" if margen is not None else "—",
                "_tags": ("inactiva",) if not p.activo else (("alerta",) if p.bajo_stock else ()),
            })
        self.tabla_productos.cargar(filas, tags=lambda f: f["_tags"])
        bajo = sum(1 for p in productos if p.activo and p.bajo_stock)
        activos = sum(1 for p in productos if p.activo)
        self.lbl_resumen.configure(text=f"{activos} productos activos · {bajo} bajo mínimo")
        if self.seleccionado and not self.tabla_productos.seleccionar_por_valor("producto", self.seleccionado):
            self.seleccionado = None
            self._mostrar_panel(False)

    # ------------------------------------------------------------------ detalle
    def _al_seleccionar(self, fila):
        if not fila:
            return
        self.mostrar_detalle(str(fila["producto"]))

    def mostrar_detalle(self, nombre):
        p = self.app.db.productos.obtener(nombre, incluir_inactivos=True)
        if p is None:
            self.seleccionado = None
            self._mostrar_panel(False)
            return
        self.seleccionado = p.nombre
        self.formulario.cargar(p)
        self.lbl_titulo_panel.configure(text=p.nombre)
        if p.activo:
            self.lbl_estado.configure(text="Activo" + (" · bajo el stock mínimo" if p.bajo_stock else ""),
                                      text_color=COLOR["peligro_hover"] if p.bajo_stock else COLOR["texto_suave"])
            self.btn_estado.configure(text="Desactivar producto", text_color=COLOR["peligro"], hover_color=COLOR["peligro_suave"])
        else:
            self.lbl_estado.configure(text="Inactivo: no aparece en Ventas ni Compras; su historial se conserva", text_color=COLOR["texto_suave"])
            self.btn_estado.configure(text="Reactivar producto", text_color=COLOR["exito"], hover_color=COLOR["exito_suave"])
        self._mostrar_panel(True)

    def guardar_cambios(self):
        if not self.seleccionado:
            return False
        try:
            d = self.formulario.leer()
        except ValueError as e:
            messagebox.showerror("Datos inválidos", str(e))
            return False
        ok = self.app.db.productos.modificar(self.seleccionado, d["nombre"], d["precio_venta"], d["precio_compra"],
                                             d["stock"], unidad=d["unidad"], stock_minimo=d["stock_minimo"])
        if not ok:
            messagebox.showerror("Error", f"No se pudo guardar: ¿ya existe otro producto llamado '{d['nombre']}'?")
            return False
        self.seleccionado = d["nombre"]
        self.app.refrescar_productos()
        self.mostrar_detalle(d["nombre"])
        self.app.toast.mostrar(f"Producto '{d['nombre']}' actualizado", "exito")
        return True

    def alternar_activo(self):
        p = self.app.db.productos.obtener(self.seleccionado, incluir_inactivos=True) if self.seleccionado else None
        if p is None:
            return
        if p.activo:
            if not messagebox.askyesno("Desactivar", f"¿Desactivar '{p.nombre}'?\n\nDejará de aparecer en Ventas, Compras e Inventario, "
                                                     "pero su historial de boletas se conserva. Podrás reactivarlo desde 'Mostrar inactivos'."):
                return
            self.app.db.productos.desactivar(p.nombre)
            self.app.toast.mostrar(f"Producto '{p.nombre}' desactivado", "alerta")
        else:
            self.app.db.productos.reactivar(p.nombre)
            self.app.toast.mostrar(f"Producto '{p.nombre}' reactivado", "exito")
        self.app.refrescar_productos()
        self.mostrar_detalle(p.nombre)

    # ------------------------------------------------------------------ alta
    def nuevo_producto(self):
        def al_guardar(d):
            if not self.app.db.productos.agregar(d["nombre"], d["precio_venta"], d["precio_compra"], d["stock"],
                                                 unidad=d["unidad"], stock_minimo=d["stock_minimo"]):
                messagebox.showerror("Error", f"Ya existe un producto activo llamado '{d['nombre']}'.")
                return False
            self.seleccionado = d["nombre"]
            self.app.refrescar_productos()
            self.mostrar_detalle(d["nombre"])
            self.app.toast.mostrar(f"Producto '{d['nombre']}' creado", "exito")
            return True
        return dialogos.DialogoFormulario(self.app, "Nuevo producto", FormularioProducto, al_guardar, texto_guardar="Crear producto")
