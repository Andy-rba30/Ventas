"""Capa de datos. `BaseDatos` abre la conexión y expone los repositorios:

    db = BaseDatos("negocio.db")
    db.productos.obtener("UREA")
    db.transacciones.deudas_pendientes()
    db.contactos.nombres("cliente")
    with db.transaccion(): ...
"""
from agro.config import RUTA_BD
from agro.db.conexion import Conexion
from agro.db.contactos import RepositorioContactos
from agro.db.productos import Producto, RepositorioProductos
from agro.db.transacciones import RepositorioTransacciones

__all__ = ["BaseDatos", "Producto"]


class BaseDatos(Conexion):
    def __init__(self, ruta=RUTA_BD):
        super().__init__(ruta)
        self.productos = RepositorioProductos(self)
        self.transacciones = RepositorioTransacciones(self)
        self.contactos = RepositorioContactos(self)
