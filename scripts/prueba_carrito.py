"""Prueba headless de la interfaz (Ventas/Compras unificadas, Fiados, Reportes, Ajustes, atajos).

Uso: xvfb-run -a python scripts/prueba_carrito.py        (Linux sin pantalla)
     python scripts/prueba_carrito.py                   (Windows/macOS, la ventana se muestra un instante)

Crea una BD temporal y simula el flujo completo. No toca la BD real. Sale con código 1 si algo falla.
"""
import os
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
workdir = tempfile.mkdtemp()
os.chdir(workdir)  # la BD se crea aquí, no en el repo

avisos = []
messagebox.showwarning = lambda t, m, **k: avisos.append(("warn", m))
messagebox.showerror = lambda t, m, **k: avisos.append(("error", m))
messagebox.showinfo = lambda t, m, **k: avisos.append(("info", m))
messagebox.askyesno = lambda t, m, **k: True

from agro.ui.app import Aplicacion  # noqa: E402
from agro.ui.tema import COLOR  # noqa: E402

app = Aplicacion(os.path.join(workdir, "prueba.db"))
toasts = []
app.toast.mostrar = lambda texto, tipo="info", duracion_ms=0: toasts.append((tipo, texto))
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

def poner(entry, texto):
    entry.delete(0, tk.END); entry.insert(0, texto)

def agregar_por_dialogo(pantalla, producto, cant, precio=None):
    """Simula el flujo real: seleccionar en la tabla, abrir el diálogo, escribir y confirmar."""
    assert pantalla.tabla_productos.seleccionar_por_valor("producto", producto), f"{producto} no está en la tabla"
    dlg = pantalla.abrir_dialogo_cantidad(); app.update()
    assert dlg is not None and dlg.winfo_exists()
    dlg.campo_cantidad.set(cant)
    if precio is not None:
        dlg.campo_precio.set(precio)
    dlg.confirmar(); app.update()

# Datos: FOSFATO es el primero por orden alfabético
assert db.productos.agregar("UREA", 120.0, 100.0, 10, unidad="saco")
assert db.productos.agregar("FOSFATO", 90.0, 70.0, 3)
app.refrescar_productos(); app.update()

def t_columnas_y_estado_inicial():
    fila = ventas.tabla_productos.valores(ventas.tabla_productos.iids()[0])
    assert (fila["producto"], fila["unidad"], fila["precio"], float(fila["stock"])) == ("FOSFATO", "unid", "S/. 90.00", 3)
    assert ventas.btn_procesar.cget("state") == "disabled" and "Agrega productos" in ventas.lbl_aviso.cget("text")
    assert ventas.procesar() is False  # deshabilitado: no hace nada

def t_doble_agregado_por_dialogo():
    agregar_por_dialogo(ventas, "FOSFATO", "1/2")
    # tras agregar, la tabla se recarga y FOSFATO sigue marcado: se puede repetir sin volver a buscar
    assert ventas.tabla_productos.seleccion()["producto"] == "FOSFATO"
    dlg = ventas.abrir_dialogo_cantidad(); dlg.campo_cantidad.set("2"); dlg.confirmar(); app.update()
    assert len(ventas.carrito) == 2 and ventas.lbl_total.cget("text").endswith("S/. 225.00"), ventas.lbl_total.cget("text")
    assert ventas.btn_procesar.cget("text") == "Cobrar  S/. 225.00" and ventas.btn_procesar.cget("state") == "normal"
    assert ventas.lbl_items.cget("text") == "2 líneas"

def t_dialogo_valida_cantidad():
    ventas.tabla_productos.seleccionar_por_valor("producto", "UREA")
    dlg = ventas.abrir_dialogo_cantidad(); dlg.campo_cantidad.set("abc"); dlg.confirmar(); app.update()
    assert dlg.winfo_exists() and dlg.campo_cantidad.entry.cget("border_color") == COLOR["peligro"]
    dlg.campo_cantidad.set("0"); dlg.confirmar(); app.update(); assert dlg.winfo_exists()
    assert dlg.campo_precio.entry.cget("state") == "disabled"  # en venta el precio no se edita
    dlg.destroy(); app.update()
    assert len(ventas.carrito) == 2

def t_buscar_enter_selecciona_primero():
    poner(ventas.ent_buscar, "ur")
    ev = tk.Event(); ev.keysym = "r"; ventas._al_escribir_busqueda(ev); app.update()  # una ventana oculta no recibe teclas sintéticas
    assert [ventas.tabla_productos.valores(i)["producto"] for i in ventas.tabla_productos.iids()] == ["UREA"]
    ventas._seleccionar_primero(); app.update()
    assert ventas.tabla_productos.seleccion()["producto"] == "UREA"
    agregar_por_dialogo(ventas, "UREA", "1")
    assert len(ventas.carrito) == 3
    poner(ventas.ent_buscar, ""); ventas.refrescar_productos(); app.update()

def t_stock_mostrado_descuenta_carrito():
    fila = ventas.tabla_productos.valores(ventas.tabla_productos.iids()[0])
    assert float(fila["stock"]) == 3 - 2.5 and "alerta" in ventas.tabla_productos.tree.item(ventas.tabla_productos.iids()[0])["tags"]

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
    editar('#2', "4", "return")
    assert ventas.carrito[0].cantidad == 4 and ventas.carrito[0].subtotal == 360.0, ventas.carrito[0]

def t_editar_subtotal_focusout():
    editar('#4', "450", "focusout")
    assert ventas.carrito[0].subtotal == 450.0 and ventas.carrito[0].precio_unit == 90.0

def t_editar_invalido():
    n = len(avisos); editar('#2', "abc", "return")
    assert avisos[n:] and avisos[-1][0] == "error", avisos[n:]

def t_quitar_y_supr():
    n = len(avisos); ventas.tabla_carrito.deseleccionar(); ventas.quitar_linea(); assert avisos[n:] and avisos[-1][0] == "warn"
    ventas.tabla_carrito.seleccionar_iid(ventas.tabla_carrito.iids()[0]); ventas.quitar_linea()
    assert len(ventas.carrito) == 2
    # Supr: las teclas sintéticas solo llegan a una ventana mapeada y con foco
    app.deiconify(); app.focus_force(); app.update()
    ventas.tabla_carrito.seleccionar_iid(ventas.tabla_carrito.iids()[-1])
    ventas.tabla_carrito.tree.focus_set(); app.update(); ventas.tabla_carrito.tree.event_generate("<Delete>"); app.update()
    app.withdraw(); app.update()
    assert len(ventas.carrito) == 1, len(ventas.carrito)

def t_fiado_bloqueado_con_publico_general():
    ventas.seg_tipo.set("Fiado"); ventas._actualizar_pie()
    assert ventas.btn_procesar.cget("state") == "disabled" and "PÚBLICO GENERAL" in ventas.lbl_aviso.cget("text")
    assert ventas.btn_procesar.cget("text").startswith("Registrar fiado")
    ventas.seg_tipo.set("Contado"); ventas._actualizar_pie()
    assert ventas.btn_procesar.cget("state") == "normal" and ventas.lbl_aviso.cget("text") == ""

def t_producto_borrado():
    db.productos.desactivar("FOSFATO"); app.refrescar_productos(); app.update()
    n = len(avisos); assert ventas.agregar_producto("FOSFATO", 1) is False
    assert avisos[n:] and "ya no existe" in avisos[-1][1]

def t_finalizar_venta_y_fiado():
    ventas.vaciar_carrito(); poner(ventas.ent_buscar, "")
    agregar_por_dialogo(ventas, "UREA", "2")
    n = len(toasts); assert ventas.procesar() is True; app.update()
    assert ventas.carrito.vacio and db.productos.obtener("UREA").stock == 8
    assert toasts[n:] and toasts[-1][0] == "exito" and "S/. 240.00" in toasts[-1][1]
    # fiado a un cliente real
    agregar_por_dialogo(ventas, "UREA", "1")
    db.contactos.agregar("cliente", "JUAN", "", ""); app.refrescar_contactos(); ventas.combo_persona.set("JUAN")
    ventas.seg_tipo.set("Fiado"); ventas._actualizar_pie()
    assert ventas.btn_procesar.cget("state") == "normal"
    assert ventas.procesar() is True; app.update()
    assert db.productos.obtener("UREA").stock == 7 and len(db.boletas.deudas_pendientes()) == 1
    assert "JUAN" in toasts[-1][1] and ventas.seg_tipo.get() == "Contado"
    assert [fiados.tabla_deudores.valores(i)["cliente"] for i in fiados.tabla_deudores.iids()] == ["JUAN"]  # Fiados se refrescó sola

def t_cobrar_deuda_ui():
    app.mostrar_pantalla("fiados"); app.update()
    assert fiados.cliente_sel is None and fiados.card_total.cget("text").endswith("S/. 120.00")
    assert fiados.seleccionar_cliente("JUAN") is True; app.update()
    assert fiados.lbl_cliente.cget("text") == "JUAN" and len(fiados.tabla_boletas.iids()) == 1
    assert fiados.tabla_boletas.seleccion()["saldo"] == "S/. 120.00"  # la boleta queda preseleccionada
    app.set_encargada("Administradora")
    # pago parcial: el diálogo rechaza montos mayores al saldo y acepta uno menor
    dlg = fiados.abrir_dialogo_pago(); app.update()
    assert dlg.campo_monto.get() == "120.00" and dlg.combo_encargada.get() == "Administradora"
    dlg.campo_monto.set("500"); assert dlg.confirmar() is False and dlg.winfo_exists()
    dlg.campo_monto.set("20"); dlg.campo_nota.set("adelanto"); assert dlg.confirmar() is True; app.update()
    b = db.boletas.deudas_pendientes("JUAN")[0]
    assert (b.estado, b.pagado, b.saldo) == ("PARCIAL", 20, 100)
    assert fiados.cliente_sel == "JUAN" and fiados.tabla_boletas.seleccion()["saldo"] == "S/. 100.00"
    assert [fiados.tabla_pagos.valores(i)["nota"] for i in fiados.tabla_pagos.iids()] == ["adelanto"]
    # pago del resto: el cliente desaparece de los deudores y el panel se oculta
    dlg = fiados.abrir_dialogo_pago(); assert dlg.campo_monto.get() == "100.00"; assert dlg.confirmar() is True; app.update()
    assert db.boletas.deudas_pendientes() == [] and fiados.tabla_deudores.iids() == () and fiados.cliente_sel is None
    pagos = db.cursor.execute("SELECT e.nombre, g.monto FROM pagos g JOIN encargadas e ON e.id=g.encargada_id ORDER BY g.id").fetchall()
    assert pagos == [("Administradora", 20), ("Administradora", 100)], pagos
    assert fiados.seleccionar_cliente("JUAN") is False  # sin deuda: aviso, no panel
    app.mostrar_pantalla("ventas")

def t_compra_ui():
    db.contactos.agregar("proveedor", "AGROSUR", "", ""); app.refrescar_contactos()
    app.mostrar_pantalla("compras"); app.update()
    assert compras.combo_persona.get() == "AGROSUR" and compras.btn_procesar.cget("text").startswith("Registrar ingreso")
    fila = compras.tabla_productos.valores(compras.tabla_productos.iids()[0])
    assert fila["producto"] == "UREA" and fila["precio"] == "S/. 100.00"  # costo de referencia
    compras.tabla_productos.seleccionar_por_valor("producto", "UREA")
    dlg = compras.abrir_dialogo_cantidad(); app.update()
    assert dlg.campo_precio.entry.cget("state") == "normal" and dlg.campo_precio.get() == "100.00"
    dlg.campo_cantidad.set("10"); dlg.campo_precio.set("110"); dlg.confirmar(); app.update()
    assert compras.carrito[0].precio_unit == 110 and compras.btn_procesar.cget("text").endswith("S/. 1100.00")
    n = len(toasts); assert compras.procesar() is True; app.update()
    p = db.productos.obtener("UREA")
    assert compras.carrito.vacio and p.stock == 17 and p.precio_compra == 110.0, p
    assert toasts[n:] and "AGROSUR" in toasts[-1][1]
    inv = app.pantallas["productos"].tabla_productos
    assert any(inv.valores(i)["producto"] == "UREA" and float(inv.valores(i)["stock"]) == 17 for i in inv.iids())
    app.mostrar_pantalla("ventas"); app.update()

def t_borrar_operacion_ui():
    app.mostrar_pantalla("reportes"); app.update()
    assert reportes.lbl_periodo.cget("text").split()[-1].isdigit() and reportes.f_filtros.winfo_manager() == ""  # filtros plegados
    # tarjetas: margen = vendido - costo actual; por cobrar total con subtexto del periodo
    assert reportes.card_margen.cget("text").startswith("MARGEN BRUTO") and "de este periodo" in reportes.card_por_cobrar.cget("text")
    mov = {reportes.tabla_resumen.valores(i)["producto"]: reportes.tabla_resumen.valores(i) for i in reportes.tabla_resumen.iids()}
    assert float(mov["UREA"]["stock"]) == 17 and mov["UREA"]["unidad"] == "saco"
    # filtros colapsables: al abrirlos y filtrar por tipo la consulta se ejecuta sola
    reportes.alternar_filtros(); app.update(); assert reportes.f_filtros.winfo_manager() == "pack" and reportes.btn_filtros.cget("text") == "Filtros ▴"
    reportes.combo_tipo.set("ENTRADA"); reportes.generar(); app.update()
    assert [reportes.tabla_mensual.valores(i)["tipo"] for i in reportes.tabla_mensual.iids()] == ["ENTRADA"] and "tipo" in reportes.lbl_filtros_activos.cget("text")
    reportes.limpiar_filtros(); app.update(); assert reportes.lbl_filtros_activos.cget("text") == ""
    reportes.alternar_filtros(); app.update()
    # navegación de periodo: mes anterior vacío y vuelta a hoy
    reportes.cambiar_mes(-1); app.update(); assert "Sin movimientos" in reportes.lbl_movimientos.cget("text")
    reportes.ir_a_hoy(); app.update(); assert reportes.lbl_movimientos.cget("text").startswith("5 movimiento")  # venta, fiado, 2 pagos, compra
    # exportar el periodo filtrado a dos hojas
    import pandas as pd
    ruta = os.path.join(workdir, "export.xlsx")
    assert app.reportes.exportar_excel(ruta, reportes.anio, reportes.mes, **reportes.filtros())
    assert list(pd.read_excel(ruta, sheet_name=None)) == ["Boletas", "Lineas"]
    def fila_tipo(tipo):
        for iid in reportes.tabla_mensual.iids():
            if str(reportes.tabla_mensual.valores(iid)["tipo"]).startswith(tipo): return iid
        raise AssertionError(f"sin fila {tipo}")
    reportes.tabla_mensual.seleccionar_iid(fila_tipo("FIADO")); n = len(avisos); reportes.borrar_operacion(); app.update()
    assert avisos[n:] and "pagos" in avisos[-1][1] and db.cursor.execute("SELECT count(*) FROM boletas WHERE tipo='FIADO'").fetchone()[0] == 1
    for _ in range(2):  # dos pagos: al borrar ambos el fiado vuelve a PENDIENTE
        reportes.tabla_mensual.seleccionar_iid(fila_tipo("COBRO_DEUDA")); reportes.borrar_operacion(); app.update()
    assert len(db.boletas.deudas_pendientes()) == 1 and db.boletas.deudas_pendientes()[0].estado == "PENDIENTE"
    reportes.tabla_mensual.seleccionar_iid(fila_tipo("FIADO")); reportes.borrar_operacion(); app.update()
    assert db.boletas.deudas_pendientes() == [] and db.productos.obtener("UREA").stock == 18

def carrito_de(*lineas):
    from agro.servicios.carrito import Carrito
    c = Carrito()
    for prod, precio, cant in lineas: c.agregar(prod, precio, cant)
    return c

def t_navegacion_y_contactos():
    app.mostrar_pantalla("contactos"); app.update()
    cont = app.pantallas["contactos"]
    sec_cli, sec_prov = cont.secciones["cliente"], cont.secciones["proveedor"]
    assert any(sec_cli.tabla.valores(i)["nombre"] == "JUAN" for i in sec_cli.tabla.iids())
    # alta de proveedor por diálogo
    dlg = cont.nuevo("proveedor"); app.update()
    dlg.formulario.nombre.set("semillas sur"); dlg.formulario.documento.set("Luis"); dlg.formulario.notas.insert("1.0", "entrega los lunes")
    assert dlg.guardar() is True; app.update()
    assert db.contactos.obtener("proveedor", "SEMILLAS SUR").notas == "entrega los lunes"
    assert "SEMILLAS SUR" in compras.combo_persona.cget("values") and "SEMILLAS SUR" in reportes.combo_prov.cget("values")
    assert compras.combo_persona.get() == "AGROSUR"  # el proveedor elegido se conserva al refrescar
    assert sec_prov.seleccionado == "SEMILLAS SUR" and sec_prov.lbl_titulo.cget("text") == "SEMILLAS SUR"
    # nombre duplicado: el diálogo no se cierra
    dlg2 = cont.nuevo("cliente"); dlg2.formulario.nombre.set("juan"); n = len(avisos)
    assert dlg2.guardar() is False and avisos[n:] and dlg2.winfo_exists(); dlg2.destroy(); app.update()
    # detalle del cliente: deuda, notas y Ver fiados con filtro
    db.contactos.agregar("cliente", "ANA", "", "")
    app.operaciones.registrar_venta(carrito_de(("UREA", 120, 2)), "2026-09-08", "Administradora", "ANA", fiado=True)
    app.refrescar_contactos(); app.refrescar_fiados(); app.update()
    sec_cli.tabla.seleccionar_por_valor("nombre", "ANA"); app.update()
    assert sec_cli.seleccionado == "ANA" and sec_cli.lbl_deuda.cget("text") == "Deuda pendiente: S/. 240.00"
    sec_cli.formulario.telefono.set("555"); sec_cli.formulario.notas.insert("1.0", "vecina"); assert sec_cli.guardar_cambios() is True
    c = db.contactos.obtener("cliente", "ANA"); assert (c.telefono, c.notas) == ("555", "vecina")
    sec_cli.ver_fiados(); app.update()
    assert app.pantalla_actual == "fiados" and fiados.cliente_sel == "ANA" and fiados.lbl_cliente.cget("text") == "ANA"
    assert fiados.tabla_deudores.seleccion()["cliente"] == "ANA"
    fiados.ver_detalle_boleta(); app.update()  # doble clic: detalle de la boleta
    fiados.limpiar_seleccion(); assert fiados.cliente_sel is None
    # PÚBLICO GENERAL no se puede eliminar
    app.mostrar_pantalla("contactos"); sec_cli.tabla.seleccionar_por_valor("nombre", "PÚBLICO GENERAL"); app.update()
    assert sec_cli.btn_eliminar.cget("state") == "disabled"
    # limpiar el fiado de ANA para no alterar los casos siguientes
    b = db.boletas.deudas_pendientes("ANA")[0]; app.operaciones.eliminar_operaciones([f"B:{b.id}"]); app.refrescar_fiados(); app.refrescar_productos()
    app.mostrar_pantalla("ventas")

def t_inventario_maestro_detalle():
    app.mostrar_pantalla("productos"); app.update()
    inv = app.pantallas["productos"]
    assert inv.seleccionado is None and not inv.panel.winfo_ismapped()
    fila = inv.tabla_productos.valores(inv.tabla_productos.iids()[0])
    assert fila["producto"] == "UREA" and fila["unidad"] == "saco" and fila["margen"] == "8 %"  # (120-110)/120
    # alta por diálogo con validación
    dlg = inv.nuevo_producto(); app.update()
    dlg.formulario.nombre.set("guano"); dlg.formulario.precio_venta.set("0"); dlg.formulario.stock.set("100")
    n = len(avisos); assert dlg.guardar() is False and dlg.winfo_exists()  # precio 0 no pasa
    dlg.formulario.precio_venta.set("25"); dlg.formulario.precio_compra.set("15"); dlg.formulario.unidad.set("kg"); dlg.formulario.stock_minimo.set("20")
    assert dlg.guardar() is True; app.update()
    g = db.productos.obtener("GUANO"); assert (g.unidad, g.precio_venta, g.precio_compra, g.stock, g.stock_minimo) == ("kg", 25, 15, 100, 20)
    assert inv.seleccionado == "GUANO" and inv.lbl_titulo_panel.cget("text") == "GUANO"
    # edición desde el panel
    inv.formulario.stock.set("15"); inv.formulario.nombre.set("guano de isla")
    assert inv.guardar_cambios() is True; app.update()
    g = db.productos.obtener("GUANO DE ISLA"); assert g.stock == 15 and g.bajo_stock and db.productos.obtener("GUANO") is None
    assert "bajo el stock mínimo" in inv.lbl_estado.cget("text")
    # renombrar a un nombre existente falla sin cambios
    inv.formulario.nombre.set("UREA"); n = len(avisos); assert inv.guardar_cambios() is False and avisos[n:]
    # desactivar, mostrar inactivos, reactivar
    inv.alternar_activo(); app.update()
    # desaparece de la tabla (inactivos ocultos) pero el panel lo conserva para poder deshacer
    assert db.productos.obtener("GUANO DE ISLA") is None
    assert "GUANO DE ISLA" not in [inv.tabla_productos.valores(i)["producto"] for i in inv.tabla_productos.iids()]
    assert inv.seleccionado == "GUANO DE ISLA" and inv.btn_estado.cget("text") == "Reactivar producto"
    inv.mostrar_inactivos.set(True); inv.refrescar_productos(); app.update()
    iid = [i for i in inv.tabla_productos.iids() if inv.tabla_productos.valores(i)["producto"] == "GUANO DE ISLA"][0]
    assert "inactiva" in inv.tabla_productos.tree.item(iid)["tags"]
    inv.tabla_productos.seleccionar_iid(iid); app.update()
    assert inv.btn_estado.cget("text") == "Reactivar producto"
    inv.alternar_activo(); app.update()
    assert db.productos.obtener("GUANO DE ISLA").activo and inv.btn_estado.cget("text") == "Desactivar producto"
    inv.mostrar_inactivos.set(False); inv.refrescar_productos()
    # buscador filtra
    poner(inv.ent_buscar, "ure"); inv.refrescar_productos(); app.update()
    assert [inv.tabla_productos.valores(i)["producto"] for i in inv.tabla_productos.iids()] == ["UREA"]
    poner(inv.ent_buscar, ""); inv.refrescar_productos()
    db.productos.desactivar("GUANO DE ISLA"); app.refrescar_productos()
    app.mostrar_pantalla("ventas")

def t_navegacion_atajos_y_ajustes():
    # Los atajos de teclado solo llegan a una ventana mapeada y con foco.
    app.deiconify(); app.focus_force(); app.update()
    app.event_generate("<F4>"); app.update()
    assert app.pantalla_actual == "fiados", app.pantalla_actual
    assert app.botones_nav["fiados"].cget("fg_color") == COLOR["primario"] and app.botones_nav["ventas"].cget("fg_color") == "transparent"
    app.event_generate("<F2>"); app.update(); assert app.pantalla_actual == "ventas"
    app.event_generate("<Control-b>"); app.update()
    assert str(app.focus_get()).startswith(str(ventas.ent_buscar)), app.focus_get()
    # Ctrl+Enter cobra el carrito actual
    agregar_por_dialogo(ventas, "UREA", "1"); n = len(toasts)
    app.event_generate("<Control-Return>"); app.update()
    assert ventas.carrito.vacio and toasts[n:] and db.productos.obtener("UREA").stock == 17
    ventas.tabla_productos.seleccionar_por_valor("producto", "UREA")
    app.event_generate("<Escape>"); app.update()
    assert ventas.tabla_productos.seleccion() is None
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
    app.mostrar_pantalla("inicio"); app.update()
    ini = app.pantallas["inicio"]
    assert ini.card_por_cobrar.cget("text").endswith(f"S/. {db.boletas.total_por_cobrar():.2f}")
    assert ini.card_ventas_hoy.cget("text").startswith("VENTAS DE HOY") and "boleta" in ini.card_ventas_hoy.cget("text")
    assert ini.encabezado.lbl_subtitulo.cget("text") == "Encargada: Administradora"
    # producto bajo mínimo aparece en 'por reponer'; fiado viejo aparece en la lista de antiguos
    db.productos.modificar("UREA", "UREA", 120, 110, 2, stock_minimo=5)
    db.contactos.agregar("cliente", "LUIS", "", "")
    app.operaciones.registrar_venta(carrito_de(("UREA", 120, 1)), "2026-01-05", "Administradora", "LUIS", fiado=True)
    ini.refrescar(); app.update()
    assert [ini.tabla_reponer.valores(i)["producto"] for i in ini.tabla_reponer.iids()] == ["UREA"] and ini.card_bajo_minimo.cget("text").endswith("1")
    assert [ini.tabla_fiados_antiguos.valores(i)["cliente"] for i in ini.tabla_fiados_antiguos.iids()] == ["LUIS"]
    b = db.boletas.deudas_pendientes("LUIS")[0]; app.operaciones.eliminar_operaciones([f"B:{b.id}"]); app.refrescar_fiados(); app.refrescar_productos()
    assert app.wm_minsize() == (1024, 680)  # CTk sobreescribe minsize() solo como setter
    app.mostrar_pantalla("ventas")

print("== interfaz ==")
for nombre, fn in [
    ("columnas de productos y botón deshabilitado con carrito vacío", t_columnas_y_estado_inicial),
    ("agregar dos veces el mismo producto por diálogo", t_doble_agregado_por_dialogo),
    ("el diálogo valida cantidad y bloquea el precio en venta", t_dialogo_valida_cantidad),
    ("buscar + Enter selecciona el primero", t_buscar_enter_selecciona_primero),
    ("stock mostrado descuenta el carrito y marca bajo stock", t_stock_mostrado_descuenta_carrito),
    ("editar cantidad con Enter (+FocusOut)", t_editar_cantidad_enter),
    ("editar subtotal con FocusOut", t_editar_subtotal_focusout),
    ("edición inválida muestra error", t_editar_invalido),
    ("quitar línea con botón y con Supr", t_quitar_y_supr),
    ("fiado bloqueado con PÚBLICO GENERAL", t_fiado_bloqueado_con_publico_general),
    ("producto desactivado avisa en vez de fallar", t_producto_borrado),
    ("cobrar al contado y fiar a un cliente (Toast, refresco de Fiados)", t_finalizar_venta_y_fiado),
    ("fiados por cliente: pago parcial y total por diálogo", t_cobrar_deuda_ui),
    ("ingreso de mercadería con precio editable en el diálogo", t_compra_ui),
    ("eliminar operaciones: bloqueo de fiado pagado y reapertura", t_borrar_operacion_ui),
    ("contactos maestro-detalle: alta, duplicado, notas, deuda y Ver fiados", t_navegacion_y_contactos),
    ("inventario maestro-detalle: alta, edición, desactivar, inactivos, filtro", t_inventario_maestro_detalle),
    ("sidebar activo, atajos F/Ctrl+B/Ctrl+Enter/Esc, Ajustes e Inicio", t_navegacion_atajos_y_ajustes),
]:
    caso(nombre, fn)
app.destroy()
print("FALLOS:", fallos or "ninguno")
sys.exit(1 if fallos else 0)
