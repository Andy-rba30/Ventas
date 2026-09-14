"""Costo promedio ponderado del inventario. Función pura, sin BD."""


def costo_promedio(stock_actual, costo_actual, cantidad_nueva, costo_nuevo):
    """Nuevo costo unitario tras comprar `cantidad_nueva` a `costo_nuevo` teniendo
    `stock_actual` valorado a `costo_actual`:

        (stock_actual * costo_actual + cantidad_nueva * costo_nuevo) / (stock_actual + cantidad_nueva)

    Casos borde: sin stock previo (o negativo por ventas sin stock), sin costo previo conocido
    (0) o sin cantidad nueva, el costo pasa a ser el nuevo. Redondeado a 4 decimales."""
    stock_actual = float(stock_actual or 0)
    costo_actual = float(costo_actual or 0)
    cantidad_nueva = float(cantidad_nueva or 0)
    costo_nuevo = float(costo_nuevo or 0)
    if cantidad_nueva <= 0:
        return round(costo_actual, 4)
    if stock_actual <= 0 or costo_actual <= 0:
        return round(costo_nuevo, 4)
    total = stock_actual + cantidad_nueva
    return round((stock_actual * costo_actual + cantidad_nueva * costo_nuevo) / total, 4)
