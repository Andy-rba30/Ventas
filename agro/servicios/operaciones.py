"""Registro de ventas, fiados, compras, cobros y eliminación de operaciones.

La UI solo llama a estos métodos; toda la BD se toca aquí o en los repositorios.
Los errores de validación se comunican con `ErrorOperacion` (mensaje listo para mostrar);
los errores de SQLite se propagan para que la UI avise que no se guardó nada.
"""
from agro.config import CLIENTE_GENERAL
from agro.db.transacciones import ERROR, FIADO_PAGADO
from agro.registro import log
from agro.servicios.formato import hora_actual


class ErrorOperacion(Exception):
    """Validación de negocio fallida. str(e) es el mensaje para la usuaria."""


class ServicioOperaciones:
    def __init__(self, db):
        self.db = db

    def registrar_venta(self, carrito, fecha, encargada, cliente, fiado=False):
        """Descuenta stock y registra cada línea del carrito. Todo o nada.
        Devuelve el tipo registrado ('VENTA' o 'FIADO')."""
        if carrito.vacio:
            raise ErrorOperacion("Carrito vacío.")
        if fiado and cliente == CLIENTE_GENERAL:
            raise ErrorOperacion("Debe seleccionar un cliente específico para el fiado.")
        tipo = "FIADO" if fiado else "VENTA"
        estado = "PENDIENTE" if fiado else "PAGADO"
        hora = hora_actual()
        with self.db.transaccion():
            for linea in carrito:
                nuevo_stock = self.db.productos.ajustar_stock(linea.producto, linea.cantidad, "restar")
                if nuevo_stock is not None:
                    self.db.transacciones.registrar(fecha, tipo, linea.producto, linea.cantidad, linea.subtotal,
                                                    encargada, nuevo_stock, cliente=cliente, estado=estado, hora=hora)
        log.info("%s registrada: %d líneas, cliente %s, encargada %s", tipo, len(carrito), cliente, encargada)
        return tipo

    def registrar_compra(self, carrito, fecha, encargada, proveedor):
        """Suma stock, registra cada ENTRADA y actualiza el costo de compra. Todo o nada."""
        if carrito.vacio:
            raise ErrorOperacion("La lista de ingreso está vacía.")
        if not proveedor:
            raise ErrorOperacion("Seleccione un proveedor.")
        hora = hora_actual()
        with self.db.transaccion():
            for linea in carrito:
                nuevo_stock = self.db.productos.ajustar_stock(linea.producto, linea.cantidad, "sumar")
                if nuevo_stock is not None:
                    self.db.transacciones.registrar(fecha, "ENTRADA", linea.producto, linea.cantidad, linea.subtotal,
                                                    encargada, nuevo_stock, proveedor=proveedor, estado="PAGADO", hora=hora)
                    self.db.productos.actualizar_precio_compra(linea.producto, linea.precio_unit)
        log.info("ENTRADA registrada: %d líneas, proveedor %s, encargada %s", len(carrito), proveedor, encargada)

    def cobrar_fiado(self, id_fiado, encargada, fecha=None):
        return self.db.transacciones.pagar_fiado(id_fiado, encargada, fecha)

    def eliminar_operaciones(self, ids):
        """Elimina transacciones revirtiendo su efecto. Devuelve (ids_bloqueados, ids_con_error):
        bloqueados son fiados ya pagados (hay que borrar antes el cobro)."""
        bloqueados, errores = [], []
        for id_tx in ids:
            res = self.db.transacciones.eliminar_y_reversar(id_tx)
            if res == FIADO_PAGADO:
                bloqueados.append(id_tx)
            elif res == ERROR:
                errores.append(id_tx)
        return bloqueados, errores
