"""Carrito de ventas o compras: lógica pura, sin Tkinter."""
from dataclasses import dataclass

from agro.servicios.formato import parse_cantidad, parse_dinero


@dataclass
class LineaCarrito:
    producto: str
    precio_unit: float
    cantidad: float
    subtotal: float


class Carrito:
    CAMPOS_EDITABLES = ("precio_unit", "cantidad", "subtotal")

    def __init__(self):
        self.lineas = []

    def __len__(self):
        return len(self.lineas)

    def __iter__(self):
        return iter(self.lineas)

    def __getitem__(self, idx):
        return self.lineas[idx]

    @property
    def vacio(self):
        return not self.lineas

    @property
    def total(self):
        return sum(l.subtotal for l in self.lineas)

    def agregar(self, producto, precio_unit, cantidad):
        linea = LineaCarrito(producto, float(precio_unit), float(cantidad), float(cantidad) * float(precio_unit))
        self.lineas.append(linea)
        return linea

    def quitar(self, idx):
        if 0 <= idx < len(self.lineas):
            del self.lineas[idx]

    def vaciar(self):
        self.lineas = []

    def cantidad_de(self, producto):
        """Cantidad total de un producto ya presente en el carrito."""
        return sum(l.cantidad for l in self.lineas if l.producto == producto)

    def editar(self, idx, campo, texto):
        """Edita precio_unit, cantidad o subtotal de una línea a partir de texto.
        - precio_unit: recalcula el subtotal.
        - cantidad: acepta fracciones (1/2) y recalcula el subtotal.
        - subtotal: se fija a mano (descuento o ajuste); precio_unit queda como registro original.
        Lanza ValueError si el texto no es válido o el valor no es aceptable."""
        if campo not in self.CAMPOS_EDITABLES:
            raise ValueError(f"Campo no editable: {campo}")
        linea = self.lineas[idx]
        if campo == "precio_unit":
            valor = parse_dinero(texto)
            if valor < 0: raise ValueError("El precio no puede ser negativo")
            linea.precio_unit = valor
            linea.subtotal = valor * linea.cantidad
        elif campo == "cantidad":
            valor = parse_cantidad(texto)
            if valor <= 0: raise ValueError("La cantidad debe ser mayor a cero")
            linea.cantidad = valor
            linea.subtotal = valor * linea.precio_unit
        else:
            valor = parse_dinero(texto)
            if valor < 0: raise ValueError("El subtotal no puede ser negativo")
            linea.subtotal = valor
