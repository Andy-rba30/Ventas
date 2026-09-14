"""Prueba de la capa BaseDatos sin interfaz (BD temporal). Uso: python scripts/prueba_bd.py"""
import sys, os, sqlite3, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ventas
from ventas import BaseDatos

fallos = []
def caso(nombre, fn):
    try:
        fn(); print(f"  OK   {nombre}")
    except Exception as e:
        fallos.append(nombre); print(f"  FAIL {nombre}: {type(e).__name__}: {e}")

tmp = tempfile.mkdtemp()
ruta = os.path.join(tmp, "prueba.db")
db = BaseDatos(ruta)

def t_pragmas():
    assert db.cursor.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert db.cursor.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert os.path.exists(os.path.join(tmp, "app.log"))

def t_renombrar_colision_sin_cambios_parciales():
    assert db.agregar_producto("UREA", 120, 100, 10)
    assert db.agregar_producto("FOSFATO", 90, 70, 5)
    with db.transaccion():
        db.registrar_transaccion("2026-09-01", "VENTA", "UREA", 1, 120, "Administradora", 9, cliente="PÚBLICO GENERAL", estado="PAGADO")
    assert db.modificar_producto("UREA", "FOSFATO", 1, 1) is False
    # el historial NO debe haber sido renombrado
    assert db.cursor.execute("SELECT count(*) FROM transacciones WHERE producto='UREA'").fetchone()[0] == 1
    assert db.obtener_producto("UREA")["precio"] == 120
    assert not db.conn.in_transaction

def t_renombrar_ok():
    assert db.modificar_producto("FOSFATO", "FOSFATO DIAMONICO", 95, 70, 5)
    assert db.obtener_producto("FOSFATO") is None and db.obtener_producto("FOSFATO DIAMONICO")["precio"] == 95

def t_boleta_atomica():
    stock_ini = db.obtener_producto("UREA")["stock"]
    try:
        with db.transaccion():
            db.actualizar_stock_y_obtener_saldo("UREA", 2, "restar")
            db.registrar_transaccion("2026-09-02", "VENTA", "UREA", 2, 240, "Administradora", stock_ini - 2, estado="PAGADO")
            raise sqlite3.OperationalError("fallo simulado en la segunda línea")
    except sqlite3.OperationalError:
        pass
    assert db.obtener_producto("UREA")["stock"] == stock_ini, "el stock debió revertirse"
    assert db.cursor.execute("SELECT count(*) FROM transacciones WHERE fecha='2026-09-02'").fetchone()[0] == 0
    assert not db.conn.in_transaction

def t_transaccion_anidada():
    with db.transaccion():
        with db.transaccion():
            db.agregar_encargada("Rosa")
        assert db.conn.in_transaction  # la interna no confirmó sola
    assert not db.conn.in_transaction and "Rosa" in db.obtener_encargadas()

def t_fiado_cobro_y_reversion():
    stock = db.actualizar_stock_y_obtener_saldo("UREA", 3, "restar")
    id_fiado = db.registrar_transaccion("2026-09-03", "FIADO", "UREA", 3, 360, "Administradora", stock, cliente="JUAN", estado="PENDIENTE")
    assert len(db.obtener_deudas_pendientes()) == 1
    assert db.pagar_fiado(id_fiado, encargada="Rosa", fecha="2026-09-10")
    cobro = db.cursor.execute("SELECT id, encargada, cantidad, ref_id, fecha, total_dinero FROM transacciones WHERE tipo='COBRO_DEUDA'").fetchone()
    assert cobro[1] == "Rosa" and cobro[2] == 0 and cobro[3] == id_fiado and cobro[4] == "2026-09-10" and cobro[5] == 360, cobro
    assert db.obtener_deudas_pendientes() == []
    # pagar dos veces no debe crear otro cobro
    assert db.pagar_fiado(id_fiado, encargada="Rosa") is False
    # borrar el FIADO pagado se rechaza
    assert db.eliminar_transaccion_y_reversar_stock(id_fiado) == BaseDatos.FIADO_PAGADO
    # borrar el cobro reabre el fiado
    assert db.eliminar_transaccion_y_reversar_stock(cobro[0]) == BaseDatos.OK
    assert len(db.obtener_deudas_pendientes()) == 1
    # ahora sí se puede borrar el fiado y el stock vuelve
    antes = db.obtener_producto("UREA")["stock"]
    assert db.eliminar_transaccion_y_reversar_stock(id_fiado) == BaseDatos.OK
    assert db.obtener_producto("UREA")["stock"] == antes + 3
    assert db.eliminar_transaccion_y_reversar_stock(99999) == BaseDatos.NO_EXISTE

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
    assert vieja.obtener_producto("CAL")["precio_compra"] == 0.0
    assert "Administradora" in vieja.obtener_encargadas()
    vieja.cerrar()
    BaseDatos(ruta_vieja).cerrar()  # segunda apertura: la migración es idempotente

def t_respaldo_consistente_con_wal():
    destino = os.path.join(tmp, "copia.db")
    db.respaldar_a(destino)
    copia = sqlite3.connect(destino)
    assert copia.execute("SELECT count(*) FROM productos").fetchone()[0] == 2
    assert copia.execute("SELECT nombre FROM encargadas WHERE nombre='Rosa'").fetchone()
    copia.close()

def t_eliminar_producto_y_contacto():
    assert db.agregar_contacto("cliente", "PEPE", "123", "999")
    assert db.agregar_contacto("cliente", "PEPE", "1", "1") is False
    assert db.eliminar_contacto("cliente", "PEPE") and db.eliminar_contacto("cliente", "PÚBLICO GENERAL") is False
    assert db.eliminar_encargada("Administradora") is False and db.eliminar_encargada("Rosa")

print("== BaseDatos ==")
for n, f in [
    ("PRAGMAs WAL/foreign_keys y app.log", t_pragmas),
    ("renombrar a nombre existente no deja cambios parciales", t_renombrar_colision_sin_cambios_parciales),
    ("renombrar válido actualiza producto", t_renombrar_ok),
    ("boleta atómica: fallo a mitad revierte stock", t_boleta_atomica),
    ("transacción anidada se une a la externa", t_transaccion_anidada),
    ("fiado: cobro con encargada/ref_id, bloqueo y reversión", t_fiado_cobro_y_reversion),
    ("migración desde esquema viejo con PRAGMA table_info", t_migracion_desde_esquema_viejo),
    ("respaldo consistente con WAL activo", t_respaldo_consistente_con_wal),
    ("contactos y encargadas", t_eliminar_producto_y_contacto),
]:
    caso(n, f)
db.cerrar()
print("FALLOS:", fallos or "ninguno")
sys.exit(1 if fallos else 0)
