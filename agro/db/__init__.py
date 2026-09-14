"""Capa de datos. `BaseDatos` abre la conexión (y migra el esquema si hace falta) y
expone los repositorios:

    db = BaseDatos("negocio.db")
    db.productos.obtener("UREA")
    db.boletas.deudas_pendientes()
    db.contactos.nombres("cliente")
    with db.transaccion(): ...
"""
from agro.config import RUTA_BD
from agro.db.boletas import Boleta, LineaBoleta, Pago, RepositorioBoletas
from agro.db.conexion import Conexion
from agro.db.contactos import RepositorioContactos
from agro.db.productos import Producto, RepositorioProductos

__all__ = ["BaseDatos", "Producto", "Boleta", "LineaBoleta", "Pago"]


class BaseDatos(Conexion):
    def __init__(self, ruta=RUTA_BD):
        super().__init__(ruta)
        self.productos = RepositorioProductos(self)
        self.boletas = RepositorioBoletas(self)
        self.contactos = RepositorioContactos(self)
