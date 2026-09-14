"""Prueba headless del flujo de carrito (Ventas y Compras).

Uso: xvfb-run -a python scripts/prueba_carrito.py        (Linux sin pantalla)
     python scripts/prueba_carrito.py                   (Windows/macOS, la ventana queda oculta)

Crea una BD temporal, simula selección, agregado, edición de celdas y quitado de ítems.
No toca la BD real. Sale con código 1 si algo falla.
"""
import sys, os, importlib, tempfile, traceback
import tkinter as tk
from tkinter import messagebox, simpledialog

mod_name = "ventas"
workdir = tempfile.mkdtemp()
os.chdir(workdir)  # la BD negocio_final_stock.db se crea aquí, no en el repo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

avisos = []
messagebox.showwarning = lambda t, m, **k: avisos.append(("warn", m))
messagebox.showerror = lambda t, m, **k: avisos.append(("error", m))
messagebox.showinfo = lambda t, m, **k: avisos.append(("info", m))
messagebox.askyesno = lambda t, m, **k: True
simpledialog.askfloat = lambda *a, **k: k.get("initialvalue", 1.0)

mod = importlib.import_module(mod_name)
app = mod.Aplicacion()
app.withdraw()
app.update()

def seleccionar_primero(tree):
    hijos = tree.get_children()
    assert hijos, "tabla vacía"
    tree.selection_set(hijos[0]); tree.focus(hijos[0]); app.update()

fallos = []
def caso(nombre, fn):
    try:
        fn(); print(f"  OK   {nombre}")
    except Exception as e:
        fallos.append(nombre); print(f"  FAIL {nombre}: {type(e).__name__}: {e}")

# Datos
assert app.db.agregar_producto("UREA", 120.0, 100.0, 10)
assert app.db.agregar_producto("FOSFATO", 90.0, 70.0, 3)
app.cargar_tabla_productos(); app.update()

def t_doble_agregado():
    seleccionar_primero(app.tree_ventas)
    app.ent_cantidad_ventas.insert(0, "1/2"); app.agregar_al_carrito_ventas(); app.update()
    # segunda vez: la tabla ya se recargó y perdió la selección → aquí fallaba con IndexError
    app.ent_cantidad_ventas.insert(0, "2"); app.agregar_al_carrito_ventas(); app.update()
    assert len(app.carrito_ventas) == 2, app.carrito_ventas
    assert app.lbl_total_ventas.cget("text") == "TOTAL: S/. 225.00", app.lbl_total_ventas.cget("text")

def t_agregar_tras_buscar():
    app.ent_buscar_ventas.insert(0, "fos"); app.ent_buscar_ventas.event_generate("<KeyRelease>"); app.update()
    app.ent_cantidad_ventas.insert(0, "1"); app.agregar_al_carrito_ventas(); app.update()
    assert len(app.carrito_ventas) == 3
    # el producto sigue marcado en la tabla tras la recarga
    sel = app.tree_ventas.selection()
    assert sel and app.tree_ventas.item(sel[0])['values'][0] == "FOSFATO", sel

def t_stock_mostrado_descuenta_carrito():
    fila = app.tree_ventas.item(app.tree_ventas.get_children()[0])['values']
    assert float(fila[2]) == 3 - 3.5, fila

def editar(col, texto, cerrar_con):
    tree = app.tree_cart_ventas
    iid = tree.get_children()[0]
    x, y, w, h = tree.bbox(iid, col)
    ev = tk.Event(); ev.x = x + w // 2; ev.y = y + h // 2
    fn = getattr(app, "editar_celda_carrito", None)
    if fn: fn(ev, "ventas")
    else: app.editar_celda_carrito_ventas(ev)
    app.update()
    entry = [c for c in tree.winfo_children() if isinstance(c, tk.Entry) or c.winfo_class() == "TEntry"][-1]
    entry.delete(0, tk.END); entry.insert(0, texto)
    if cerrar_con == "return":
        entry.event_generate("<Return>"); app.update()
        entry.event_generate("<FocusOut>"); app.update()   # el doble disparo
    else:
        entry.event_generate("<FocusOut>"); app.update()

def t_editar_cantidad_enter():
    editar('#3', "4", "return")
    assert app.carrito_ventas[0]['cantidad'] == 4 and app.carrito_ventas[0]['subtotal'] == 360.0, app.carrito_ventas[0]

def t_editar_subtotal_focusout():
    editar('#4', "450", "focusout")
    assert app.carrito_ventas[0]['subtotal'] == 450.0 and app.carrito_ventas[0]['precio_unit'] == 90.0

def t_editar_invalido():
    n = len(avisos); editar('#3', "abc", "return")
    assert avisos[n:] and avisos[-1][0] == "error", avisos[n:]

def t_quitar():
    app.tree_cart_ventas.selection_set(app.tree_cart_ventas.get_children()[0])
    (app.quitar_del_carrito("ventas") if hasattr(app, "quitar_del_carrito") else app.quitar_del_carrito_ventas())
    assert len(app.carrito_ventas) == 2

def t_parse_div_cero():
    try: app.parse_cantidad("1/0")
    except ValueError: return
    raise AssertionError("no lanzó ValueError")

def t_compras_doble():
    seleccionar_primero(app.tree_compras)
    app.ent_cantidad_compras.insert(0, "5"); app.agregar_al_carrito_compras(); app.update()
    app.ent_cantidad_compras.insert(0, "5"); app.agregar_al_carrito_compras(); app.update()
    assert len(app.carrito_compras) == 2 and app.carrito_compras[0]['precio_unit'] == 70.0

def t_producto_borrado():
    app.db.eliminar_producto("FOSFATO"); app.cargar_tabla_productos(); app.update()
    # seleccionar FOSFATO antes de borrarlo no es posible ya; forzamos el estado
    if hasattr(app, "producto_sel"):
        app.producto_sel["ventas"] = {"nombre": "FOSFATO", "precio": 90.0, "precio_compra": 70.0, "stock": 3.0}
        n = len(avisos); app.ent_cantidad_ventas.insert(0, "1"); app.agregar_al_carrito_ventas()
        assert avisos[n:] and "ya no existe" in avisos[-1][1]

def t_finalizar_venta():
    app.procesar_boleta("VENTA"); app.update()
    assert app.carrito_ventas == [] and app.db.obtener_producto("UREA")["stock"] == 10 - 4 - 1 + 4 - 4  # ver detalle abajo

def t_finalizar_venta_y_fiado():
    app.vaciar_carrito("ventas")
    app.producto_sel["ventas"] = app.db.obtener_producto("UREA")
    app.ent_cantidad_ventas.delete(0, tk.END); app.ent_cantidad_ventas.insert(0, "2"); app.agregar_al_carrito_ventas()
    app.procesar_boleta("VENTA"); app.update()
    assert app.carrito_ventas == [] and app.db.obtener_producto("UREA")["stock"] == 8
    # fiado a PÚBLICO GENERAL se rechaza y el carrito se conserva
    app.ent_cantidad_ventas.insert(0, "1"); app.agregar_al_carrito_ventas()
    n = len(avisos); app.procesar_boleta("FIADO")
    assert avisos[n:] and len(app.carrito_ventas) == 1 and app.db.obtener_producto("UREA")["stock"] == 8
    app.db.agregar_contacto("cliente", "JUAN", "", ""); app.actualizar_combos_personas(); app.combo_cliente_venta.set("JUAN")
    app.procesar_boleta("FIADO"); app.update()
    assert app.db.obtener_producto("UREA")["stock"] == 7 and len(app.db.obtener_deudas_pendientes()) == 1

def t_cobrar_deuda_ui():
    app.cargar_fiados(); app.update()
    app.tree_fiados.selection_set(app.tree_fiados.get_children()[0])
    app.combo_encargada.set("Administradora")
    app.cobrar_deuda(); app.update()
    assert app.db.obtener_deudas_pendientes() == []
    cobro = app.db.cursor.execute("SELECT encargada, cantidad, ref_id FROM transacciones WHERE tipo='COBRO_DEUDA'").fetchone()
    assert cobro[0] == "Administradora" and cobro[1] == 0 and cobro[2] is not None, cobro

def t_compra_ui():
    app.db.agregar_contacto("proveedor", "AGROSUR", "", ""); app.actualizar_combos_personas()
    simpledialog.askfloat = lambda *a, **k: 110.0
    app.vaciar_carrito("compras")
    app.producto_sel["compras"] = app.db.obtener_producto("UREA")
    app.ent_cantidad_compras.delete(0, tk.END); app.ent_cantidad_compras.insert(0, "10"); app.agregar_al_carrito_compras()
    app.procesar_boleta_compra(); app.update()
    p = app.db.obtener_producto("UREA")
    assert app.carrito_compras == [] and p["stock"] == 17 and p["precio_compra"] == 110.0, p

def t_borrar_operacion_ui():
    app.generar_reporte_mensual(); app.update()
    def fila_tipo(tipo):
        for iid in app.tree_mensual.get_children():
            if app.tree_mensual.item(iid)["values"][2] == tipo: return iid
        raise AssertionError(f"sin fila {tipo}")
    # borrar el FIADO ya pagado se bloquea con aviso
    app.tree_mensual.selection_set(fila_tipo("FIADO")); n = len(avisos); app.borrar_operacion(); app.update()
    assert avisos[n:] and "pagados" in avisos[-1][1] and app.db.cursor.execute("SELECT count(*) FROM transacciones WHERE tipo='FIADO'").fetchone()[0] == 1
    # borrar el COBRO reabre el fiado
    app.tree_mensual.selection_set(fila_tipo("COBRO_DEUDA")); app.borrar_operacion(); app.update()
    assert len(app.db.obtener_deudas_pendientes()) == 1
    # y ahora el FIADO sí se borra devolviendo stock
    app.tree_mensual.selection_set(fila_tipo("FIADO")); app.borrar_operacion(); app.update()
    assert app.db.obtener_deudas_pendientes() == [] and app.db.obtener_producto("UREA")["stock"] == 18

print(f"== {mod_name} ==")
for nombre, fn in [
    ("doble agregado del mismo producto", t_doble_agregado),
    ("agregar tras escribir en el buscador", t_agregar_tras_buscar),
    ("stock mostrado descuenta el carrito", t_stock_mostrado_descuenta_carrito),
    ("editar cantidad con Enter (+FocusOut)", t_editar_cantidad_enter),
    ("editar subtotal con FocusOut", t_editar_subtotal_focusout),
    ("edición inválida muestra error", t_editar_invalido),
    ("quitar ítem", t_quitar),
    ("parse_cantidad 1/0 -> ValueError", t_parse_div_cero),
    ("compras: doble agregado", t_compras_doble),
    ("producto borrado avisa en vez de fallar", t_producto_borrado),
    ("finalizar venta y fiado (atómico, cliente obligatorio)", t_finalizar_venta_y_fiado),
    ("cobrar deuda desde la UI con encargada actual", t_cobrar_deuda_ui),
    ("ingreso de mercadería actualiza stock y costo", t_compra_ui),
    ("eliminar operaciones: bloqueo de fiado pagado y reapertura", t_borrar_operacion_ui),
]:
    caso(nombre, fn)
app.destroy()
print("FALLOS:", fallos or "ninguno")
sys.exit(1 if fallos else 0)
