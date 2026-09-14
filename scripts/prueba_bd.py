"""Prueba de la capa de datos y servicios sin interfaz (BD temporal). Uso: python scripts/prueba_bd.py"""
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agro.db import BaseDatos
from agro.db.transacciones import FIADO_PAGADO, NO_EXISTE, OK
from agro.servicios.carrito import Carrito
from agro.servicios.formato import parse_cantidad
from agro.servicios.operaciones import ErrorOperacion, ServicioOperaciones
from agro.servicios.reportes import ServicioReportes

fallos = []
def caso(nombre, fn):
    try:
        fn(); print(f"  OK   {nombre}")
    except Exception as e:
        fallos.append(nombre); print(f"  FAIL {nombre}: {type(e).__name__}: {e}")

tmp = tempfile.mkdtemp()
ruta = os.path.join(tmp, "prueba.db")
db = BaseDatos(ruta)
ops = ServicioOperaciones(db)
reportes = ServicioReportes(db)

def t_pragmas():
    assert db.cursor.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert db.cursor.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert os.path.exists(os.path.join(tmp, "app.log"))

def t_parse_cantidad():
    assert parse_cantidad("1/2") == 0.5 and parse_cantidad("0,5") == 0.5 and parse_cantidad(" 3 ") == 3
    for malo in ("1/0", "abc", ""):
        try: parse_cantidad(malo); raise AssertionError(f"{malo!r} no lanzó ValueError")
        except ValueError: pass

def t_carrito():
    c = Carrito()
    assert c.vacio and c.total == 0
    c.agregar("UREA", 120, 0.5); c.agregar("UREA", 120, 2)
    assert len(c) == 2 and c.total == 300 and c.cantidad_de("UREA") == 2.5
    c.editar(0, "cantidad", "1/4"); assert c[0].subtotal == 30
    c.editar(1, "subtotal", "S/. 200"); assert c[1].subtotal == 200 and c[1].precio_unit == 120
    c.editar(1, "precio_unit", "100"); assert c[1].subtotal == 200
    for campo, texto in (("cantidad", "0"), ("cantidad", "abc"), ("precio_unit", "-1"), ("subtotal", "x")):
        try: c.editar(0, campo, texto); raise AssertionError(f"{campo}={texto!r} debió fallar")
        except ValueError: pass
    c.quitar(0); assert len(c) == 1
    c.vaciar(); assert c.vacio

def t_renombrar_colision_sin_cambios_parciales():
    assert db.productos.agregar("UREA", 120, 100, 10)
    assert db.productos.agregar("FOSFATO", 90, 70, 5)
    assert db.productos.agregar("UREA", 1, 1, 1) is False
    with db.transaccion():
        db.transacciones.registrar("2026-09-01", "VENTA", "UREA", 1, 120, "Administradora", 9, cliente="PÚBLICO GENERAL", estado="PAGADO")
    assert db.productos.modificar("UREA", "FOSFATO", 1, 1) is False
    assert db.cursor.execute("SELECT count(*) FROM transacciones WHERE producto='UREA'").fetchone()[0] == 1
    assert db.productos.obtener("UREA").precio == 120
    assert not db.conn.in_transaction

def t_renombrar_ok():
    assert db.productos.modificar("FOSFATO", "FOSFATO DIAMONICO", 95, 70, 5)
    assert db.productos.obtener("FOSFATO") is None and db.productos.obtener("FOSFATO DIAMONICO").precio == 95

def t_venta_atomica_y_validaciones():
    c = Carrito(); c.agregar("UREA", 120, 2); c.agregar("PRODUCTO INEXISTENTE", 5, 1)
    stock_ini = db.productos.obtener("UREA").stock
    try: ops.registrar_venta(Carrito(), "2026-09-02", "Administradora", "PÚBLICO GENERAL"); raise AssertionError
    except ErrorOperacion: pass
    try: ops.registrar_venta(c, "2026-09-02", "Administradora", "PÚBLICO GENERAL", fiado=True); raise AssertionError
    except ErrorOperacion: pass
    assert ops.registrar_venta(c, "2026-09-02", "Administradora", "PÚBLICO GENERAL") == "VENTA"
    assert db.productos.obtener("UREA").stock == stock_ini - 2
    # la línea de un producto inexistente se omite (comportamiento heredado)
    assert db.cursor.execute("SELECT count(*) FROM transacciones WHERE fecha='2026-09-02'").fetchone()[0] == 1
    # fallo simulado a mitad: nada queda guardado
    try:
        with db.transaccion():
            db.productos.ajustar_stock("UREA", 2, "restar")
            raise sqlite3.OperationalError("fallo simulado")
    except sqlite3.OperationalError: pass
    assert db.productos.obtener("UREA").stock == stock_ini - 2 and not db.conn.in_transaction

def t_transaccion_anidada():
    with db.transaccion():
        with db.transaccion():
            db.contactos.agregar_encargada("Rosa")
        assert db.conn.in_transaction
    assert not db.conn.in_transaction and "Rosa" in db.contactos.encargadas()

def t_compra():
    assert db.contactos.agregar("proveedor", "AGROSUR", "", "")
    c = Carrito(); c.agregar("UREA", 95, 20)
    try: ops.registrar_compra(c, "2026-09-04", "Rosa", ""); raise AssertionError
    except ErrorOperacion: pass
    antes = db.productos.obtener("UREA").stock
    ops.registrar_compra(c, "2026-09-04", "Rosa", "AGROSUR")
    p = db.productos.obtener("UREA")
    assert p.stock == antes + 20 and p.precio_compra == 95

def t_fiado_cobro_y_reversion():
    db.contactos.agregar("cliente", "JUAN", "", "")
    c = Carrito(); c.agregar("UREA", 120, 3)
    assert ops.registrar_venta(c, "2026-09-03", "Administradora", "JUAN", fiado=True) == "FIADO"
    deudas = db.transacciones.deudas_pendientes(); assert len(deudas) == 1
    id_fiado = deudas[0][0]
    assert db.transacciones.fiados_pendientes_de("JUAN")[0][1] == "UREA"
    assert ops.cobrar_fiado(id_fiado, "Rosa", "2026-09-10")
    cobro = db.cursor.execute("SELECT id, encargada, cantidad, ref_id, fecha, total_dinero FROM transacciones WHERE tipo='COBRO_DEUDA'").fetchone()
    assert cobro[1] == "Rosa" and cobro[2] == 0 and cobro[3] == id_fiado and cobro[4] == "2026-09-10" and cobro[5] == 360, cobro
    assert db.transacciones.deudas_pendientes() == []
    assert ops.cobrar_fiado(id_fiado, "Rosa") is False              # no se cobra dos veces
    assert ops.eliminar_operaciones([id_fiado]) == ([id_fiado], []) # fiado pagado bloqueado
    assert ops.eliminar_operaciones([cobro[0]]) == ([], [])         # borrar cobro reabre
    assert len(db.transacciones.deudas_pendientes()) == 1
    antes = db.productos.obtener("UREA").stock
    assert db.transacciones.eliminar_y_reversar(id_fiado) == OK
    assert db.productos.obtener("UREA").stock == antes + 3
    assert db.transacciones.eliminar_y_reversar(99999) == NO_EXISTE

def t_reporte():
    rep = reportes.generar(2026, "Septiembre")
    assert not rep.vacio and rep.ingresos == 360 and rep.gastos == 1900 and rep.por_cobrar == 0, rep
    assert rep.balance == rep.ingresos - rep.gastos and rep.stock_total == db.productos.stock_total()
    tipos = sorted(b.tipo for b in rep.boletas); assert tipos == ["ENTRADA", "VENTA", "VENTA"], tipos
    mov = {m.producto: m for m in rep.movimientos}["UREA"]; assert mov.salidas == 3 and mov.entradas == 20
    assert reportes.generar(2026, "Septiembre", dia=4).gastos == 1900 and reportes.generar(2026, "Septiembre", dia=4).ingresos == 0
    assert reportes.generar(2026, "Septiembre", proveedor="AGROSUR").ingresos == 0
    assert reportes.generar(2025, 1).vacio
    assert reportes.exportar_excel(os.path.join(tmp, "salida.xlsx")) and os.path.exists(os.path.join(tmp, "salida.xlsx"))

def t_migracion_desde_esquema_viejo():
    ruta_vieja = os.path.join(tmp, "vieja.db")
    c = sqlite3.connect(ruta_vieja)
    c.execute("CREATE TABLE productos (id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT UNIQUE, precio REAL, stock REAL)")
    c.execute("CREATE TABLE transacciones (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, hora TEXT, tipo TEXT, producto TEXT, cantidad REAL, total_dinero REAL, encargada TEXT, stock_resultante REAL)")
    c.execute("INSERT INTO productos (nombre, precio, stock) VALUES ('CAL', 10, 4)")
    c.commit(); c.close()
    vieja = BaseDatos(ruta_vieja)
    assert {"cliente", "estado", "proveedor", "ref_id"} <= vieja.columnas_de("transacciones")
    assert "precio_compra" in vieja.columnas_de("productos")
    assert vieja.productos.obtener("CAL").precio_compra == 0.0
    assert "Administradora" in vieja.contactos.encargadas()
    vieja.cerrar()
    BaseDatos(ruta_vieja).cerrar()  # segunda apertura: la migración es idempotente

def t_respaldo_consistente_con_wal():
    destino = os.path.join(tmp, "copia.db")
    db.respaldar_a(destino)
    copia = sqlite3.connect(destino)
    assert copia.execute("SELECT count(*) FROM productos").fetchone()[0] == 2
    assert copia.execute("SELECT nombre FROM encargadas WHERE nombre='Rosa'").fetchone()
    copia.close()

def t_contactos_y_encargadas():
    assert db.contactos.agregar("cliente", "PEPE", "123", "999")
    assert db.contactos.agregar("cliente", "PEPE", "1", "1") is False
    assert "PEPE" in db.contactos.nombres("cliente") and any(r[1] == "PEPE" for r in db.contactos.listar("cliente"))
    assert db.contactos.eliminar("cliente", "PEPE") and db.contactos.eliminar("cliente", "PÚBLICO GENERAL") is False
    assert db.contactos.eliminar_encargada("Administradora") is False and db.contactos.eliminar_encargada("Rosa")

print("== BaseDatos + servicios ==")
for n, f in [
    ("PRAGMAs WAL/foreign_keys y app.log", t_pragmas),
    ("parse_cantidad", t_parse_cantidad),
    ("Carrito: agregar, editar, quitar, total", t_carrito),
    ("renombrar a nombre existente no deja cambios parciales", t_renombrar_colision_sin_cambios_parciales),
    ("renombrar válido actualiza producto", t_renombrar_ok),
    ("venta: validaciones y atomicidad", t_venta_atomica_y_validaciones),
    ("transacción anidada se une a la externa", t_transaccion_anidada),
    ("compra: suma stock y actualiza costo", t_compra),
    ("fiado: cobro con encargada/ref_id, bloqueo y reversión", t_fiado_cobro_y_reversion),
    ("reporte mensual: tarjetas, boletas, filtros, excel", t_reporte),
    ("migración desde esquema viejo con PRAGMA table_info", t_migracion_desde_esquema_viejo),
    ("respaldo consistente con WAL activo", t_respaldo_consistente_con_wal),
    ("contactos y encargadas", t_contactos_y_encargadas),
]:
    caso(n, f)
db.cerrar()
print("FALLOS:", fallos or "ninguno")
sys.exit(1 if fallos else 0)
