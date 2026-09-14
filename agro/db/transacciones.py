"""Repositorio de transacciones: líneas de boleta, fiados, cobros y reversión."""
import datetime
import sqlite3

import pandas as pd

from agro.registro import log

# Códigos que devuelve eliminar_y_reversar
OK, NO_EXISTE, FIADO_PAGADO, ERROR = "OK", "NO_EXISTE", "FIADO_PAGADO", "ERROR"


class RepositorioTransacciones:
    OK, NO_EXISTE, FIADO_PAGADO, ERROR = OK, NO_EXISTE, FIADO_PAGADO, ERROR

    def __init__(self, cx):
        self.cx = cx

    def registrar(self, fecha, tipo, producto, cantidad, total, encargada, stock_final,
                  cliente="", proveedor="", estado="", hora=None, ref_id=None):
        hora = hora if hora else datetime.datetime.now().strftime("%H:%M:%S")
        self.cx.cursor.execute("""
            INSERT INTO transacciones (fecha, hora, tipo, producto, cantidad, total_dinero, encargada, stock_resultante, cliente, proveedor, estado, ref_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(fecha), hora, tipo, producto, cantidad, total, encargada, stock_final, cliente, proveedor, estado, ref_id))
        return self.cx.cursor.lastrowid

    def pagar_fiado(self, id_fiado, encargada, fecha=None):
        """Marca el FIADO como PAGADO y registra el COBRO_DEUDA enlazado por ref_id."""
        row = self.cx.cursor.execute("SELECT producto, total_dinero, cliente, estado FROM transacciones WHERE id=? AND tipo='FIADO'", (id_fiado,)).fetchone()
        if not row:
            return False
        prod, monto, cliente, estado = row
        if estado == "PAGADO":
            return False
        fecha = fecha or datetime.date.today().strftime("%Y-%m-%d")
        try:
            with self.cx.transaccion():
                self.cx.cursor.execute("UPDATE transacciones SET estado='PAGADO' WHERE id=?", (id_fiado,))
                res = self.cx.cursor.execute("SELECT stock FROM productos WHERE nombre=?", (prod,)).fetchone()
                stock_actual = float(res[0]) if res else 0
                self.registrar(fecha, "COBRO_DEUDA", prod, 0, monto, encargada, stock_actual, cliente=cliente, estado="COMPLETADO", ref_id=id_fiado)
            log.info("Fiado %s de %s cobrado (S/. %.2f) por %s", id_fiado, cliente, monto, encargada)
            return True
        except sqlite3.Error as e:
            log.error("Error al cobrar fiado %s: %s", id_fiado, e)
            return False

    def eliminar_y_reversar(self, id_transaccion):
        """Borra una transacción deshaciendo su efecto. Devuelve OK, NO_EXISTE, FIADO_PAGADO o ERROR."""
        row = self.cx.cursor.execute("SELECT tipo, producto, cantidad, estado, ref_id FROM transacciones WHERE id=?", (id_transaccion,)).fetchone()
        if not row:
            return NO_EXISTE
        tipo_orig, prod, cant, estado, ref_id = row
        if tipo_orig == "FIADO" and estado == "PAGADO":
            return FIADO_PAGADO  # primero hay que eliminar el cobro asociado
        try:
            with self.cx.transaccion():
                if tipo_orig in ("VENTA", "FIADO"):
                    self.cx.cursor.execute("UPDATE productos SET stock = stock + ? WHERE nombre = ?", (cant, prod))
                elif tipo_orig == "ENTRADA":
                    self.cx.cursor.execute("UPDATE productos SET stock = stock - ? WHERE nombre = ?", (cant, prod))
                elif tipo_orig == "COBRO_DEUDA":
                    if ref_id is not None:
                        self.cx.cursor.execute("UPDATE transacciones SET estado='PENDIENTE' WHERE id=? AND tipo='FIADO'", (ref_id,))
                    else:
                        log.warning("Cobro %s sin ref_id (registro antiguo): el fiado original no se reabre", id_transaccion)
                self.cx.cursor.execute("DELETE FROM transacciones WHERE id=?", (id_transaccion,))
            log.info("Transacción %s (%s %s) eliminada", id_transaccion, tipo_orig, prod)
            return OK
        except sqlite3.Error as e:
            log.error("Error al eliminar transacción %s: %s", id_transaccion, e)
            return ERROR

    def deudas_pendientes(self):
        """(id, fecha, cliente, producto, cantidad, total) de cada FIADO pendiente."""
        return self.cx.cursor.execute(
            "SELECT id, fecha, cliente, producto, cantidad, total_dinero FROM transacciones WHERE tipo='FIADO' AND estado='PENDIENTE'"
        ).fetchall()

    def fiados_pendientes_de(self, cliente):
        """(fecha, producto, cantidad, total) de los fiados pendientes de un cliente."""
        return self.cx.cursor.execute(
            "SELECT fecha, producto, cantidad, total_dinero FROM transacciones WHERE tipo='FIADO' AND estado='PENDIENTE' AND cliente=? ORDER BY fecha, hora",
            (cliente,),
        ).fetchall()

    def como_dataframe(self):
        return pd.read_sql_query("SELECT * FROM transacciones", self.cx.conn)
