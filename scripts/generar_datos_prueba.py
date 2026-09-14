"""Genera una BD de prueba con muchas boletas para medir rendimiento.

Uso: python scripts/generar_datos_prueba.py [ruta.db] [lineas]   (por defecto prueba_rendimiento.db, 20000)

Crea 50 productos, 120 clientes, 10 proveedores y boletas repartidas en los últimos 24 meses
(ventas al contado, fiados con pagos parciales y compras) hasta alcanzar el número de líneas.
Nunca toca la BD real: exige una ruta distinta de negocio_final_stock.db.
"""
import datetime
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agro.config import RUTA_BD  # noqa: E402
from agro.db import BaseDatos  # noqa: E402


def generar(ruta, lineas_objetivo=20000, semilla=7):
    if os.path.basename(ruta) == RUTA_BD:
        raise SystemExit("Esa es la BD real: usa otra ruta.")
    if os.path.exists(ruta):
        os.remove(ruta)
    rnd = random.Random(semilla)
    db = BaseDatos(ruta)

    productos = [f"PRODUCTO {i:02d}" for i in range(50)]
    with db.transaccion():
        for i, nombre in enumerate(productos):
            db.productos.agregar(nombre, 20 + i * 3.5, 12 + i * 2.5, 500, unidad=rnd.choice(["unid", "kg", "L", "saco"]), stock_minimo=10)
        clientes = [f"CLIENTE {i:03d}" for i in range(120)]
        for c in clientes:
            db.contactos.agregar("cliente", c, str(10000000 + rnd.randrange(89999999)), "9" + str(rnd.randrange(10**8)))
        proveedores = [f"PROVEEDOR {i}" for i in range(10)]
        for p in proveedores:
            db.contactos.agregar("proveedor", p, "Contacto", "999")
        for e in ("Rosa", "Carmen"):
            db.contactos.agregar_encargada(e)
    ids_prod = {p.nombre: p for p in db.productos.listar()}
    ids_cli = {c: db.contactos.id_de("cliente", c) for c in clientes}
    ids_prov = {p: db.contactos.id_de("proveedor", p) for p in proveedores}
    ids_enc = [db.contactos.id_encargada(e) for e in ("Administradora", "Rosa", "Carmen")]

    hoy = datetime.date.today()
    inicio = hoy - datetime.timedelta(days=730)
    lineas, boletas, pagos = 0, 0, 0
    with db.transaccion():
        while lineas < lineas_objetivo:
            fecha = (inicio + datetime.timedelta(days=rnd.randrange(731))).isoformat()
            hora = f"{rnd.randrange(8, 19):02d}:{rnd.randrange(60):02d}:{rnd.randrange(60):02d}"
            tipo = rnd.choices(["VENTA", "FIADO", "ENTRADA"], weights=[70, 20, 10])[0]
            n = rnd.randint(1, 5)
            elegidos = rnd.sample(productos, n)
            filas = []
            for nombre in elegidos:
                p = ids_prod[nombre]
                cant = rnd.choice([0.5, 1, 1, 2, 3, 5, 10])
                precio = p.precio_compra if tipo == "ENTRADA" else p.precio_venta
                filas.append((p.id, cant, precio, round(cant * precio, 2), 500))
            if tipo == "ENTRADA":
                bid = db.boletas.crear(fecha, tipo, rnd.choice(ids_enc), filas, proveedor_id=ids_prov[rnd.choice(proveedores)], hora=hora)
            else:
                cliente = "PÚBLICO GENERAL" if tipo == "VENTA" and rnd.random() < 0.6 else rnd.choice(clientes)
                cid = db.contactos.id_de("cliente", cliente)
                bid = db.boletas.crear(fecha, tipo, rnd.choice(ids_enc), filas, cliente_id=cid, hora=hora)
                if tipo == "FIADO" and rnd.random() < 0.7:
                    b = db.boletas.obtener(bid)
                    monto = b.total if rnd.random() < 0.5 else round(b.total * rnd.uniform(0.2, 0.8), 2)
                    f_pago = (datetime.date.fromisoformat(fecha) + datetime.timedelta(days=rnd.randrange(1, 60))).isoformat()
                    db.boletas.registrar_pago(bid, monto, rnd.choice(ids_enc), fecha=f_pago, hora=hora)
                    pagos += 1
            lineas += n
            boletas += 1
    db.cerrar()
    return boletas, lineas, pagos


if __name__ == "__main__":
    ruta = sys.argv[1] if len(sys.argv) > 1 else "prueba_rendimiento.db"
    objetivo = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    b, l, p = generar(ruta, objetivo)
    print(f"{ruta}: {b} boletas, {l} líneas, {p} pagos")
