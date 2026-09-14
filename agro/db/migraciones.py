"""Migraciones de esquema.

v0 -> v1: la tabla plana `transacciones` (una fila por producto vendido, comprado o
cobrado) se convierte en `boletas` + `boleta_lineas` + `pagos`, con productos y
contactos referenciados por id. Antes de tocar nada se guarda una copia en
backups/negocio_pre_migracion_<fecha>.db. La tabla vieja se conserva como
`_legacy_transacciones` durante dos versiones.
"""
import datetime
import os

from agro.db.esquema import VERSION_ESQUEMA, crear_esquema
from agro.registro import log

# Columnas que versiones intermedias del esquema v0 pudieron no tener.
_COLUMNAS_LEGACY = [
    ("transacciones", "cliente", "TEXT"),
    ("transacciones", "estado", "TEXT"),
    ("transacciones", "proveedor", "TEXT"),
    ("transacciones", "ref_id", "INTEGER"),
    ("productos", "precio_compra", "REAL DEFAULT 0.0"),
]


def aplicar(cx):
    """Lleva la BD a VERSION_ESQUEMA paso a paso. Idempotente."""
    version = cx.cursor.execute("PRAGMA user_version").fetchone()[0]
    if version >= VERSION_ESQUEMA:
        return
    if version == 0 and not cx.tabla_existe("transacciones"):
        # BD nueva (o vacía): se crea directamente en la última versión.
        with cx.transaccion():
            crear_esquema(cx.cursor)
        cx.cursor.execute(f"PRAGMA user_version={VERSION_ESQUEMA}")
        return
    _respaldar_antes_de_migrar(cx, version)
    while version < VERSION_ESQUEMA:
        paso = _PASOS[version]
        with cx.transaccion():
            paso(cx)
        version += 1
        cx.cursor.execute(f"PRAGMA user_version={version}")
        log.info("Migración a esquema v%d completada", version)


def _migrar_v1_a_v2(cx):
    """v2: columna `notas` en clientes y proveedores."""
    for tabla in ("clientes", "proveedores"):
        if "notas" not in cx.columnas_de(tabla):
            cx.cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN notas TEXT NOT NULL DEFAULT ''")


def _migrar_v2_a_v3(cx):
    """v3: costo unitario al momento de la venta en cada línea (NULL en las antiguas: el
    reporte usa entonces el precio_compra actual) y tabla precios_historial."""
    if "costo_unit" not in cx.columnas_de("boleta_lineas"):
        cx.cursor.execute("ALTER TABLE boleta_lineas ADD COLUMN costo_unit REAL")
    crear_esquema(cx.cursor)  # crea precios_historial y su índice si faltan


def _respaldar_antes_de_migrar(cx, version_origen):
    if cx.db_name == ":memory:":
        return None
    carpeta = os.path.join(os.path.dirname(os.path.abspath(cx.db_name)), "backups")
    os.makedirs(carpeta, exist_ok=True)
    marca = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # La versión de origen va en el nombre: dos migraciones en el mismo segundo no se pisan.
    ruta = os.path.join(carpeta, f"negocio_pre_migracion_v{version_origen}_{marca}.db")
    cx.respaldar_a(ruta)
    log.info("Copia previa a la migración: %s", ruta)
    return ruta


def _migrar_v0_a_v1(cx):
    cur = cx.cursor

    # 0. Asegurar columnas de versiones intermedias del esquema viejo.
    for tabla, col, tipo in _COLUMNAS_LEGACY:
        if cx.tabla_existe(tabla) and col not in cx.columnas_de(tabla):
            cur.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}")

    # 1. Productos: nueva tabla con unidad, stock_minimo y activo; se conservan los ids.
    cur.execute("ALTER TABLE productos RENAME TO _legacy_productos")
    for tabla in ("clientes", "proveedores", "encargadas"):
        if cx.tabla_existe(tabla) and "activo" not in cx.columnas_de(tabla):
            cur.execute(f"ALTER TABLE {tabla} ADD COLUMN activo INTEGER NOT NULL DEFAULT 1")
    crear_esquema(cur)
    cur.execute("""
        INSERT INTO productos (id, nombre, precio_venta, precio_compra, stock)
        SELECT id, nombre, COALESCE(precio, 0), COALESCE(precio_compra, 0), COALESCE(stock, 0)
        FROM _legacy_productos
    """)
    cur.execute("DROP TABLE _legacy_productos")

    # 2. Resolución de nombres a ids, creando lo que falte como inactivo.
    cache = {}

    def id_producto(nombre):
        clave = ("producto", nombre)
        if clave not in cache:
            row = cur.execute("SELECT id FROM productos WHERE nombre=?", (nombre,)).fetchone()
            if row is None:
                cur.execute("INSERT INTO productos (nombre, activo) VALUES (?, 0)", (nombre,))
                row = (cur.lastrowid,)
                log.warning("Migración: producto '%s' no existía; creado inactivo", nombre)
            cache[clave] = row[0]
        return cache[clave]

    def id_contacto(tabla, nombre):
        if not nombre:
            return None
        clave = (tabla, nombre)
        if clave not in cache:
            row = cur.execute(f"SELECT id FROM {tabla} WHERE nombre=?", (nombre,)).fetchone()
            if row is None:
                cur.execute(f"INSERT INTO {tabla} (nombre, activo) VALUES (?, 0)", (nombre,))
                row = (cur.lastrowid,)
                log.warning("Migración: %s '%s' no existía; creado inactivo", tabla[:-1], nombre)
            cache[clave] = row[0]
        return cache[clave]

    def id_encargada(nombre):
        return id_contacto("encargadas", nombre or "Administradora")

    # 3. Boletas y líneas: una boleta = misma fecha + hora + tipo + cliente + proveedor + encargada.
    filas = cur.execute("""
        SELECT id, fecha, hora, tipo, producto, cantidad, total_dinero, encargada, stock_resultante,
               cliente, proveedor, estado, ref_id
        FROM transacciones ORDER BY fecha, hora, id
    """).fetchall()

    boletas = {}            # clave de agrupación -> boleta_id
    linea_legacy = {}       # id legacy de línea -> (boleta_id, cliente, monto, estado, fecha)
    cobros = []
    for (lid, fecha, hora, tipo, producto, cantidad, total, encargada, stock_res, cliente, proveedor, estado, ref_id) in filas:
        if tipo == "COBRO_DEUDA":
            cobros.append((lid, fecha, hora, total, encargada, cliente, ref_id))
            continue
        if tipo not in ("VENTA", "FIADO", "ENTRADA"):
            log.warning("Migración: transacción %s de tipo desconocido '%s' omitida", lid, tipo)
            continue
        clave = (fecha, hora or "", tipo, cliente or "", proveedor or "", encargada or "")
        if clave not in boletas:
            cur.execute("""
                INSERT INTO boletas (fecha, hora, tipo, cliente_id, proveedor_id, encargada_id, total, estado)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """, (fecha, hora or "00:00:00", tipo, id_contacto("clientes", cliente), id_contacto("proveedores", proveedor),
                  id_encargada(encargada), "PENDIENTE" if tipo == "FIADO" else "PAGADO"))
            boletas[clave] = cur.lastrowid
        boleta_id = boletas[clave]
        cantidad = float(cantidad or 0)
        total = float(total or 0)
        precio_unit = total / cantidad if cantidad else 0.0
        cur.execute("""
            INSERT INTO boleta_lineas (boleta_id, producto_id, cantidad, precio_unit, subtotal, stock_resultante)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (boleta_id, id_producto(producto), cantidad, precio_unit, total, stock_res))
        linea_legacy[lid] = (boleta_id, cliente or "", total, estado, fecha)

    cur.execute("UPDATE boletas SET total = (SELECT COALESCE(SUM(subtotal), 0) FROM boleta_lineas WHERE boleta_id = boletas.id)")

    # 4. Cobros -> pagos. Por ref_id si existe; si no, por cliente + monto + fecha más cercana.
    usadas = set()
    sin_vincular = 0
    for (lid, fecha, hora, monto, encargada, cliente, ref_id) in cobros:
        destino = None
        if ref_id is not None and ref_id in linea_legacy:
            destino = linea_legacy[ref_id][0]
        else:
            candidatas = [
                (f_linea, lid_linea, b_id) for lid_linea, (b_id, cli, tot, est, f_linea) in linea_legacy.items()
                if lid_linea not in usadas and cli == (cliente or "") and est == "PAGADO"
                and abs(float(tot) - float(monto or 0)) < 0.005 and f_linea <= fecha
            ]
            if candidatas:
                f_linea, lid_linea, b_id = max(candidatas)
                usadas.add(lid_linea)
                destino = b_id
        if destino is None:
            sin_vincular += 1
            log.warning("Migración: cobro legacy %s (cliente '%s', S/. %.2f, %s) sin fiado vinculable; queda solo en _legacy_transacciones",
                        lid, cliente, float(monto or 0), fecha)
            continue
        cur.execute("INSERT INTO pagos (boleta_id, fecha, hora, monto, encargada_id) VALUES (?, ?, ?, ?, ?)",
                    (destino, fecha, hora or "00:00:00", float(monto or 0), id_encargada(encargada)))

    # 5. Estado de cada fiado según lo pagado.
    for boleta_id, total in cur.execute("SELECT id, total FROM boletas WHERE tipo='FIADO'").fetchall():
        pagado = cur.execute("SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE boleta_id=?", (boleta_id,)).fetchone()[0]
        estado = "PAGADO" if pagado >= total - 0.005 else ("PARCIAL" if pagado > 0 else "PENDIENTE")
        cur.execute("UPDATE boletas SET estado=? WHERE id=?", (estado, boleta_id))

    # 6. Conservar la tabla vieja.
    cur.execute("ALTER TABLE transacciones RENAME TO _legacy_transacciones")
    log.info("Migración: %d boletas, %d líneas, %d cobros (%d sin vincular)",
             len(boletas), len(linea_legacy), len(cobros), sin_vincular)


# Versión de origen -> función que la lleva a la siguiente.
_PASOS = {0: _migrar_v0_a_v1, 1: _migrar_v1_a_v2, 2: _migrar_v2_a_v3}
