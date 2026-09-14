"""Registro de ventas, fiados, compras, pagos y eliminación de operaciones.

La UI solo llama a estos métodos; toda la BD se toca aquí o en los repositorios.
Los errores de validación se comunican con `ErrorOperacion` (mensaje listo para mostrar);
los errores de SQLite se propagan para que la UI avise que no se guardó nada.

Claves de operación (para eliminar desde el reporte): "B:<id>" boleta completa,
"L:<id>" una línea, "P:<id>" un pago.
"""
from agro.config import CLIENTE_GENERAL
from agro.db.boletas import ERROR, TIENE_PAGOS
from agro.registro import log
from agro.servicios.formato import hora_actual


class ErrorOperacion(Exception):
    """Validación de negocio fallida. str(e) es el mensaje para la usuaria."""


def clave_boleta(id_): return f"B:{id_}"
def clave_linea(id_): return f"L:{id_}"
def clave_pago(id_): return f"P:{id_}"


class ServicioOperaciones:
    def __init__(self, db):
        self.db = db

    def _lineas_con_stock(self, carrito, operacion):
        """Ajusta el stock de cada línea y devuelve las tuplas para RepositorioBoletas.crear.
        Las líneas de productos que ya no existen (o están inactivos) se omiten."""
        lineas = []
        for linea in carrito:
            p = self.db.productos.obtener(linea.producto)
            if p is None:
                log.warning("Línea omitida: el producto '%s' no existe o está inactivo", linea.producto)
                continue
            nuevo_stock = self.db.productos.ajustar_stock(p.nombre, linea.cantidad, operacion)
            lineas.append((p.id, linea.cantidad, linea.precio_unit, linea.subtotal, nuevo_stock))
        if not lineas:
            raise ErrorOperacion("Ninguno de los productos del carrito existe en el inventario.")
        return lineas

    def registrar_venta(self, carrito, fecha, encargada, cliente, fiado=False):
        """Descuenta stock y crea la boleta con todas las líneas. Todo o nada.
        Devuelve el tipo registrado ('VENTA' o 'FIADO')."""
        if carrito.vacio:
            raise ErrorOperacion("Carrito vacío.")
        if fiado and cliente == CLIENTE_GENERAL:
            raise ErrorOperacion("Debe seleccionar un cliente específico para el fiado.")
        cliente_id = self.db.contactos.id_de("cliente", cliente)
        if cliente_id is None:
            raise ErrorOperacion(f"El cliente '{cliente}' no existe.")
        tipo = "FIADO" if fiado else "VENTA"
        with self.db.transaccion():
            lineas = self._lineas_con_stock(carrito, "restar")
            encargada_id = self.db.contactos.id_encargada(encargada, crear=True)
            boleta_id = self.db.boletas.crear(fecha, tipo, encargada_id, lineas, cliente_id=cliente_id, hora=hora_actual())
        log.info("%s #%s registrada: %d líneas, cliente %s, encargada %s", tipo, boleta_id, len(lineas), cliente, encargada)
        return tipo

    def registrar_compra(self, carrito, fecha, encargada, proveedor):
        """Suma stock, crea la boleta ENTRADA y actualiza el costo de compra. Todo o nada."""
        if carrito.vacio:
            raise ErrorOperacion("La lista de ingreso está vacía.")
        if not proveedor:
            raise ErrorOperacion("Seleccione un proveedor.")
        proveedor_id = self.db.contactos.id_de("proveedor", proveedor)
        if proveedor_id is None:
            raise ErrorOperacion(f"El proveedor '{proveedor}' no existe.")
        with self.db.transaccion():
            lineas = self._lineas_con_stock(carrito, "sumar")
            for linea in carrito:
                self.db.productos.actualizar_precio_compra(linea.producto, linea.precio_unit)
            encargada_id = self.db.contactos.id_encargada(encargada, crear=True)
            boleta_id = self.db.boletas.crear(fecha, "ENTRADA", encargada_id, lineas, proveedor_id=proveedor_id, hora=hora_actual())
        log.info("ENTRADA #%s registrada: %d líneas, proveedor %s, encargada %s", boleta_id, len(lineas), proveedor, encargada)
        return boleta_id

    def cobrar_fiado(self, boleta_id, encargada, monto=None, fecha=None, notas=""):
        """Registra un pago del fiado. Sin monto paga el saldo completo. Devuelve el id del pago."""
        b = self.db.boletas.obtener(boleta_id)
        if b is None or b.tipo != "FIADO":
            raise ErrorOperacion("La operación seleccionada no es un fiado.")
        if b.saldo <= 0:
            raise ErrorOperacion("Este fiado ya está pagado.")
        monto = b.saldo if monto is None else monto
        try:
            with self.db.transaccion():
                encargada_id = self.db.contactos.id_encargada(encargada, crear=True)
                return self.db.boletas.registrar_pago(boleta_id, monto, encargada_id, fecha=fecha, notas=notas)
        except ValueError as e:
            raise ErrorOperacion(str(e)) from e

    def eliminar_operaciones(self, claves):
        """Elimina boletas ('B:id'), líneas ('L:id') o pagos ('P:id') revirtiendo su efecto.
        Devuelve (claves_bloqueadas, claves_con_error): bloqueadas son fiados con pagos
        (hay que borrar antes los pagos)."""
        bloqueadas, errores = [], []
        for clave in claves:
            tipo, _, id_ = str(clave).partition(":")
            if not id_:  # un entero suelto se trata como boleta
                tipo, id_ = "B", tipo
            id_ = int(id_)
            if tipo == "B":
                res = self.db.boletas.eliminar_boleta(id_)
            elif tipo == "L":
                res = self.db.boletas.eliminar_linea(id_)
            elif tipo == "P":
                res = self.db.boletas.eliminar_pago(id_)
            else:
                res = ERROR
            if res == TIENE_PAGOS:
                bloqueadas.append(clave)
            elif res == ERROR:
                errores.append(clave)
        return bloqueadas, errores
