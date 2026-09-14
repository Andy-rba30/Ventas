"""Prueba headless de la interfaz (Ventas, Compras, Fiados, Reportes).

Uso: xvfb-run -a python scripts/prueba_carrito.py        (Linux sin pantalla)
     python scripts/prueba_carrito.py                   (Windows/macOS, la ventana queda oculta)

Crea una BD temporal, simula selección, agregado, edición de celdas, quitado de ítems,
venta, fiado, cobro, compra y eliminación de operaciones. No toca la BD real.
Sale con código 1 si algo falla.
"""
import os
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox, simpledialog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
workdir = tempfile.mkdtemp()
os.chdir(workdir)  # la BD se crea aquí, no en el repo

avisos = []
messagebox.showwarning = lambda t, m, **k: avisos.append(("warn", m))
messagebox.showerror = lambda t, m, **k: avisos.append(("error", m))
messagebox.showinfo = lambda t, m, **k: avisos.append(("info", m))
messagebox.askyesno = lambda t, m, **k: True
simpledialog.askfloat = lambda *a, **k: k.get("initialvalue", 1.0)

from agro.ui.app import Aplicacion  # noqa: E402

app = Aplicacion(os.path.join(workdir, "prueba.db"))
# Tk solo calcula la geometría de las tablas (bbox) si la ventana se mostró al menos una vez.
app.update(); app.deiconify(); app.update(); app.withdraw(); app.update()
ventas = app.pantallas["ventas"]
compras = app.pantallas["compras"]
fiados = app.pantallas["fiados"]
reportes = app.pantallas["reportes"]
db = app.db

fallos = []
def caso(nombre, fn):
    try:
        fn(); print(f"  OK   {nombre}")
    except Exception as e:
        fallos.append(nombre); print(f"  FAIL {nombre}: {type(e).__name__}: {e}")

def seleccionar_primero(tree):
    hijos = tree.get_children()
    assert hijos, "tabla vacía"
    tree.selection_set(hijos[0]); tree.focus(hijos[0]); app.update()

def poner(entry, texto):
    entry.delete(0, tk.END); entry.insert(0, texto)

# Datos: FOSFATO es el primero por orden alfabético
assert db.productos.agregar("UREA", 120.0, 100.0, 10)
assert db.productos.agregar("FOSFATO", 90.0, 70.0, 3)
app.refrescar_productos(); app.update()

def t_doble_agregado():
    seleccionar_primero(ventas.tree_productos)
    poner(ventas.ent_cantidad, "1/2"); ventas.agregar_al_carrito(); app.update()
    # segunda vez: la tabla ya se recargó y perdió la selección; antes fallaba con IndexError
    poner(ventas.ent_cantidad, "2"); ventas.agregar_al_carrito(); app.update()
    assert len(ventas.carrito) == 2
    assert ventas.lbl_total.cget("text") == "TOTAL: S/. 225.00", ventas.lbl_total.cget("text")

def t_agregar_tras_buscar():
    poner(ventas.ent_buscar, "fos"); ventas.ent_buscar.event_generate("<KeyRelease>"); app.update()
    poner(ventas.ent_cantidad, "1"); ventas.agregar_al_carrito(); app.update()
    assert len(ventas.carrito) == 3
    sel = ventas.tree_productos.selection()
    assert sel and ventas.tree_productos.item(sel[0])['values'][0] == "FOSFATO", sel

def t_stock_mostrado_descuenta_carrito():
    fila = ventas.tree_productos.item(ventas.tree_productos.get_children()[0])['values']
    assert float(fila[2]) == 3 - 3.5 and 'bajo_stock' in ventas.tree_productos.item(ventas.tree_productos.get_children()[0])['tags'], fila

def editar(col, texto, cerrar_con):
    tree = ventas.tree_carrito
    iid = tree.get_children()[0]
    x, y, w, h = tree.bbox(iid, col)
    ev = tk.Event(); ev.x = x + w // 2; ev.y = y + h // 2
    ventas._editar_celda(ev); app.update()
    entry = [c for c in tree.winfo_children() if c.winfo_class() == "TEntry"][-1]
    poner(entry, texto)
    if cerrar_con == "return":
        entry.event_generate("<Return>"); app.update()
        entry.event_generate("<FocusOut>"); app.update()   # el doble disparo
    else:
        entry.event_generate("<FocusOut>"); app.update()

def t_editar_cantidad_enter():
    editar('#3', "4", "return")
    assert ventas.carrito[0].cantidad == 4 and ventas.carrito[0].subtotal == 360.0, ventas.carrito[0]

def t_editar_subtotal_focusout():
    editar('#4', "450", "focusout")
    assert ventas.carrito[0].subtotal == 450.0 and ventas.carrito[0].precio_unit == 90.0

def t_editar_invalido():
    n = len(avisos); editar('#3', "abc", "return")
    assert avisos[n:] and avisos[-1][0] == "error", avisos[n:]

def t_quitar():
    n = len(avisos); ventas.quitar_del_carrito(); assert avisos[n:] and avisos[-1][0] == "warn"
    ventas.tree_carrito.selection_set(ventas.tree_carrito.get_children()[0])
    ventas.quitar_del_carrito()
    assert len(ventas.carrito) == 2

def t_compras_doble():
    seleccionar_primero(compras.tree_productos)
    poner(compras.ent_cantidad, "5"); compras.agregar_al_carrito(); app.update()
    poner(compras.ent_cantidad, "5"); compras.agregar_al_carrito(); app.update()
    assert len(compras.carrito) == 2 and compras.carrito[0].precio_unit == 70.0

def t_producto_borrado():
    db.productos.eliminar("FOSFATO"); app.refrescar_productos(); app.update()
    n = len(avisos); poner(ventas.ent_cantidad, "1"); ventas.agregar_al_carrito()
    assert avisos[n:] and "ya no existe" in avisos[-1][1] and ventas.producto_sel is None

def t_finalizar_venta_y_fiado():
    ventas.vaciar_carrito(); poner(ventas.ent_buscar, "")
    ventas.producto_sel = db.productos.obtener("UREA")
    poner(ventas.ent_cantidad, "2"); ventas.agregar_al_carrito()
    ventas.procesar(fiado=False); app.update()
    assert ventas.carrito.vacio and db.productos.obtener("UREA").stock == 8 and avisos[-1][0] == "info"
    n = len(avisos); ventas.procesar(fiado=False); assert avisos[n:] and "vacío" in avisos[-1][1]
    poner(ventas.ent_cantidad, "1"); ventas.agregar_al_carrito()
    n = len(avisos); ventas.procesar(fiado=True)
    assert avisos[n:] and "cliente" in avisos[-1][1] and len(ventas.carrito) == 1 and db.productos.obtener("UREA").stock == 8
    db.contactos.agregar("cliente", "JUAN", "", ""); app.refrescar_contactos(); ventas.combo_cliente.set("JUAN")
    ventas.procesar(fiado=True); app.update()
    assert db.productos.obtener("UREA").stock == 7 and len(db.transacciones.deudas_pendientes()) == 1
    assert len(fiados.tree_fiados.get_children()) == 1  # la pantalla Fiados se refrescó sola

def t_cobrar_deuda_ui():
    fiados.tree_fiados.selection_set(fiados.tree_fiados.get_children()[0])
    app.combo_encargada.set("Administradora")
    fiados.cobrar_deuda(); app.update()
    assert db.transacciones.deudas_pendientes() == [] and fiados.tree_fiados.get_children() == ()
    cobro = db.cursor.execute("SELECT encargada, cantidad, ref_id FROM transacciones WHERE tipo='COBRO_DEUDA'").fetchone()
    assert cobro[0] == "Administradora" and cobro[1] == 0 and cobro[2] is not None, cobro

def t_compra_ui():
    db.contactos.agregar("proveedor", "AGROSUR", "", ""); app.refrescar_contactos()
    simpledialog.askfloat = lambda *a, **k: 110.0
    compras.vaciar_carrito()
    compras.producto_sel = db.productos.obtener("UREA")
    poner(compras.ent_cantidad, "10"); compras.agregar_al_carrito()
    compras.procesar(); app.update()
    p = db.productos.obtener("UREA")
    assert compras.carrito.vacio and p.stock == 17 and p.precio_compra == 110.0, p
    # inventario refrescado: la fila de UREA muestra el nuevo stock
    inv = app.pantallas["productos"].tree_precios
    assert any(i['values'][0] == "UREA" and float(i['values'][1]) == 17 for i in map(inv.item, inv.get_children()))

def t_borrar_operacion_ui():
    reportes.generar(); app.update()
    assert "17" in reportes.card_stock_total.cget("text")
    def fila_tipo(tipo):
        for iid in reportes.tree_mensual.get_children():
            if reportes.tree_mensual.item(iid)["values"][2] == tipo: return iid
        raise AssertionError(f"sin fila {tipo}")
    reportes.tree_mensual.selection_set(fila_tipo("FIADO")); n = len(avisos); reportes.borrar_operacion(); app.update()
    assert avisos[n:] and "pagados" in avisos[-1][1] and db.cursor.execute("SELECT count(*) FROM transacciones WHERE tipo='FIADO'").fetchone()[0] == 1
    reportes.tree_mensual.selection_set(fila_tipo("COBRO_DEUDA")); reportes.borrar_operacion(); app.update()
    assert len(db.transacciones.deudas_pendientes()) == 1
    reportes.tree_mensual.selection_set(fila_tipo("FIADO")); reportes.borrar_operacion(); app.update()
    assert db.transacciones.deudas_pendientes() == [] and db.productos.obtener("UREA").stock == 18

def t_navegacion_y_contactos():
    app.mostrar_pantalla("contactos"); app.update()
    cont = app.pantallas["contactos"]
    assert any(cont.tree_clientes.item(i)['values'][1] == "JUAN" for i in cont.tree_clientes.get_children())
    poner(cont.ent_prov_nom, "semillas sur"); cont.guardar("proveedor")
    assert "SEMILLAS SUR" in compras.combo_proveedor.cget("values") and "SEMILLAS SUR" in reportes.combo_prov.cget("values")
    app.mostrar_pantalla("ventas")

print("== interfaz ==")
for nombre, fn in [
    ("doble agregado del mismo producto", t_doble_agregado),
    ("agregar tras escribir en el buscador", t_agregar_tras_buscar),
    ("stock mostrado descuenta el carrito y marca bajo stock", t_stock_mostrado_descuenta_carrito),
    ("editar cantidad con Enter (+FocusOut)", t_editar_cantidad_enter),
    ("editar subtotal con FocusOut", t_editar_subtotal_focusout),
    ("edición inválida muestra error", t_editar_invalido),
    ("quitar ítem", t_quitar),
    ("compras: doble agregado", t_compras_doble),
    ("producto borrado avisa en vez de fallar", t_producto_borrado),
    ("finalizar venta y fiado (atómico, cliente obligatorio)", t_finalizar_venta_y_fiado),
    ("cobrar deuda desde la UI con encargada actual", t_cobrar_deuda_ui),
    ("ingreso de mercadería actualiza stock, costo e inventario", t_compra_ui),
    ("eliminar operaciones: bloqueo de fiado pagado y reapertura", t_borrar_operacion_ui),
    ("navegación y refresco cruzado de contactos", t_navegacion_y_contactos),
]:
    caso(nombre, fn)
app.destroy()
print("FALLOS:", fallos or "ninguno")
sys.exit(1 if fallos else 0)
