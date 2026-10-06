"""Capa de datos. `BaseDatos` abre la conexión (y migra el esquema si hace falta) y
expone los repositorios:

    db = BaseDatos("negocio.db")
    db.productos.obtener("UREA")
    db.boletas.deudas_pendientes()
    db.contactos.nombres("cliente")
    with db.transaccion(): ...
"""
from agro.db.boletas import Boleta, LineaBoleta, Pago, RepositorioBoletas
from agro.db.conexion import Conexion
from agro.db.contactos import RepositorioContactos
from agro.db.precios import PrecioHistorico, RepositorioPrecios
from agro.db.productos import Producto, RepositorioProductos
from agro.db.reportes import Filtro, RepositorioReportes

__all__ = ["BaseDatos", "Producto", "Boleta", "LineaBoleta", "Pago", "Filtro", "PrecioHistorico"]


class BaseDatos(Conexion):
    def __init__(self, ruta=None):
        if ruta is None:
            from agro.rutas import ruta_bd  # import tardío: rutas no depende de db
            ruta = ruta_bd()
        super().__init__(ruta)
        self.productos = RepositorioProductos(self)
        self.boletas = RepositorioBoletas(self)
        self.contactos = RepositorioContactos(self)
        self.reportes = RepositorioReportes(self)
        self.precios = RepositorioPrecios(self)
