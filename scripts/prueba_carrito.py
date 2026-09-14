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
app.mostrar_pantalla("ventas")
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
    seleccionar_primero(ventas.tabla_productos.tree)
    poner(ventas.ent_cantidad, "1/2"); ventas.agregar_al_carrito(); app.update()
    # segunda vez: la tabla ya se recargó y perdió la selección; antes fallaba con IndexError
    poner(ventas.ent_cantidad, "2"); ventas.agregar_al_carrito(); app.update()
    assert len(ventas.carrito) == 2
    assert ventas.lbl_total.cget("text") == "TOTAL: S/. 225.00", ventas.lbl_total.cget("text")

def t_agregar_tras_buscar():
    poner(ventas.ent_buscar, "fos"); ventas.ent_buscar.event_generate("<KeyRelease>"); app.update()
    poner(ventas.ent_cantidad, "1"); ventas.agregar_al_carrito(); app.update()
    assert len(ventas.carrito) == 3
    sel = ventas.tabla_productos.tree.selection()
    assert sel and ventas.tabla_productos.tree.item(sel[0])['values'][0] == "FOSFATO", sel

def t_stock_mostrado_descuenta_carrito():
    fila = ventas.tabla_productos.tree.item(ventas.tabla_productos.tree.get_children()[0])['values']
    assert float(fila[2]) == 3 - 3.5 and 'alerta' in ventas.tabla_productos.tree.item(ventas.tabla_productos.tree.get_children()[0])['tags'], fila

def editar(col, texto, cerrar_con):
    tree = ventas.tabla_carrito.tree
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
    ventas.tabla_carrito.tree.selection_set(ventas.tabla_carrito.tree.get_children()[0])
    ventas.quitar_del_carrito()
    assert len(ventas.carrito) == 2

def t_compras_doble():
    seleccionar_primero(compras.tabla_productos.tree)
    poner(compras.ent_cantidad, "5"); compras.agregar_al_carrito(); app.update()
    poner(compras.ent_cantidad, "5"); compras.agregar_al_carrito(); app.update()
    assert len(compras.carrito) == 2 and compras.carrito[0].precio_unit == 70.0

def t_producto_borrado():
    db.productos.desactivar("FOSFATO"); app.refrescar_productos(); app.update()
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
    assert db.productos.obtener("UREA").stock == 7 and len(db.boletas.deudas_pendientes()) == 1
    assert len(fiados.tabla_fiados.tree.get_children()) == 1  # la pantalla Fiados se refrescó sola

def t_cobrar_deuda_ui():
    fiados.tabla_fiados.tree.selection_set(fiados.tabla_fiados.tree.get_children()[0])
    app.set_encargada("Administradora")
    fiados.cobrar_deuda(); app.update()
    assert db.boletas.deudas_pendientes() == [] and fiados.tabla_fiados.tree.get_children() == ()
    cobro = db.cursor.execute("SELECT e.nombre, g.monto, g.boleta_id FROM pagos g JOIN encargadas e ON e.id=g.encargada_id").fetchone()
    assert cobro[0] == "Administradora" and cobro[1] == 120 and cobro[2] is not None, cobro

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
    inv = app.pantallas["productos"].tabla_precios.tree
    assert any(i['values'][0] == "UREA" and float(i['values'][1]) == 17 for i in map(inv.item, inv.get_children()))

def t_borrar_operacion_ui():
    reportes.generar(); app.update()
    assert "17" in reportes.card_stock_total.cget("text")
    def fila_tipo(tipo):
        for iid in reportes.tabla_mensual.tree.get_children():
            if str(reportes.tabla_mensual.tree.item(iid)["values"][2]).startswith(tipo): return iid
        raise AssertionError(f"sin fila {tipo}")
    reportes.tabla_mensual.tree.selection_set(fila_tipo("FIADO")); n = len(avisos); reportes.borrar_operacion(); app.update()
    assert avisos[n:] and "pagos" in avisos[-1][1] and db.cursor.execute("SELECT count(*) FROM boletas WHERE tipo='FIADO'").fetchone()[0] == 1
    reportes.tabla_mensual.tree.selection_set(fila_tipo("COBRO_DEUDA")); reportes.borrar_operacion(); app.update()
    assert len(db.boletas.deudas_pendientes()) == 1
    reportes.tabla_mensual.tree.selection_set(fila_tipo("FIADO")); reportes.borrar_operacion(); app.update()
    assert db.boletas.deudas_pendientes() == [] and db.productos.obtener("UREA").stock == 18

def t_navegacion_y_contactos():
    app.mostrar_pantalla("contactos"); app.update()
    cont = app.pantallas["contactos"]
    assert any(cont.tabla_clientes.tree.item(i)['values'][1] == "JUAN" for i in cont.tabla_clientes.tree.get_children())
    poner(cont.ent_prov_nom, "semillas sur"); cont.guardar("proveedor")
    assert "SEMILLAS SUR" in compras.combo_proveedor.cget("values") and "SEMILLAS SUR" in reportes.combo_prov.cget("values")
    app.mostrar_pantalla("ventas")

def t_navegacion_atajos_y_ajustes():
    from agro.ui.tema import COLOR
    # Los atajos de teclado solo llegan a una ventana mapeada y con foco.
    app.deiconify(); app.focus_force(); app.update()
    app.event_generate("<F4>"); app.update()
    assert app.pantalla_actual == "fiados", app.pantalla_actual
    assert app.botones_nav["fiados"].cget("fg_color") == COLOR["primario"] and app.botones_nav["ventas"].cget("fg_color") == "transparent"
    app.event_generate("<F2>"); app.update(); assert app.pantalla_actual == "ventas"
    app.event_generate("<Control-b>"); app.update()
    assert str(app.focus_get()).startswith(str(ventas.ent_buscar)), app.focus_get()
    ventas.producto_sel = db.productos.obtener("UREA"); ventas.lbl_sel_prod.configure(text="UREA")
    app.event_generate("<Escape>"); app.update()
    assert ventas.producto_sel is None and ventas.lbl_sel_prod.cget("text") == "---"
    app.withdraw(); app.update()
    # Ajustes: agregar y quitar encargada, apariencia persistida en config.json
    app.mostrar_pantalla("ajustes"); app.update()
    aj = app.pantallas["ajustes"]
    aj.campo_encargada.set("rosa"); aj.agregar_encargada(); app.update()
    assert "Rosa" in db.contactos.encargadas() and [aj.tabla_encargadas.valores(i)["nombre"] for i in aj.tabla_encargadas.iids()] == ["Administradora", "Rosa"]
    app.set_encargada("Rosa"); aj.tabla_encargadas.seleccionar_por_valor("nombre", "Rosa"); aj.quitar_encargada(); app.update()
    assert "Rosa" not in db.contactos.encargadas() and app.encargada_actual() == "Administradora"
    assert "Encargada: Administradora" == app.lbl_encargada.cget("text")
    aj._cambiar_apariencia("Oscuro"); app.update()
    from agro.preferencias import Preferencias
    assert Preferencias(db.db_name).get("apariencia") == "Dark"
    aj._cambiar_apariencia("Claro")
    assert "Versión" in aj.lbl_acerca.cget("text") and "todavía" in aj.lbl_ultimo_respaldo.cget("text")
    # Inicio refleja la deuda total y el stock bajo mínimo
    app.mostrar_pantalla("inicio"); app.update()
    ini = app.pantallas["inicio"]
    assert ini.card_por_cobrar.cget("text").endswith(f"S/. {db.boletas.total_por_cobrar():.2f}")
    assert app.wm_minsize() == (1024, 680)  # CTk sobreescribe minsize() solo como setter
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
    ("sidebar activo, atajos F/Ctrl+B/Esc, Ajustes e Inicio", t_navegacion_atajos_y_ajustes),
]:
    caso(nombre, fn)
app.destroy()
print("FALLOS:", fallos or "ninguno")
sys.exit(1 if fallos else 0)
