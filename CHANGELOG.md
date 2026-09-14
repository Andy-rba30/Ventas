# Historial de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es/1.1.0/). Versión única en
`agro/__init__.py`; los tags `vX.Y.Z` disparan la construcción del ejecutable de Windows.

## [4.2.0] – 2026-09-14

Reescritura completa del programa original (`ventas14.py`, un solo archivo de 1 400 líneas) en el
paquete `agro/` con capas de datos, servicios e interfaz, pruebas automáticas y CI.

### Fase 1 – Bugs críticos
- Agregar al carrito después de recargar la tabla ya no falla (IndexError por índices viejos).
- Editar un producto revierte todo si algo falla; las boletas se guardan completas o no se guardan.
- Las ediciones de cantidad y subtotal ya no se aplican dos veces (Enter + FocusOut).
- Los respaldos incluyen lo pendiente en el archivo WAL (API de respaldo de SQLite).

### Fase 2 – Estructura y pruebas
- Paquete `agro/` (config, registro, db, servicios, ui) con `main.py` como punto de entrada.
- Registro de actividad en `app.log` (rotativo) en lugar de `print`.
- Pruebas con pytest sobre SQLite en memoria y prueba de interfaz sin pantalla (Xvfb); ambas
  corren en GitHub Actions con Python 3.11 y 3.12.

### Fase 3 – Modelo de datos
- Boletas con líneas y pagos (esquema v1) en vez de una tabla plana por línea: una venta con
  varios productos es una sola operación, con encargada, cliente o proveedor y hora.
- Migración automática desde la BD antigua con copia previa en `backups/`; la tabla vieja se
  conserva como `_legacy_transacciones`.
- Productos y contactos se desactivan en vez de borrarse; notas en clientes y proveedores (v2).
- Fiados por cliente con pagos parciales; eliminar una boleta, línea o pago revierte el stock.

### Fase 4 – Interfaz
- Tema con tokens de color, espaciado y tipografía; modo claro, oscuro o del sistema.
- Barra lateral con encargada activa y atajos F1–F8, Ctrl+B, Ctrl+Enter, Esc y Supr.
- Ventas y Compras en una sola pantalla; el carrito se llena con un diálogo de cantidad
  (acepta fracciones como 1/2) y las líneas se editan con doble clic.
- Inventario y Contactos en maestro-detalle; Fiados por deudor con historial de pagos.
- Reportes en dos niveles: Resumen (caja, compras, margen, por cobrar, movimiento por producto)
  y Movimientos (boletas con líneas, exportar a Excel, eliminar). Inicio con lo urgente del día.
- Pantalla Ajustes: encargadas, respaldo y restauración, apariencia.

### Fase 5 – Rendimiento y negocio
- Reportes en SQL puro: sin pandas ni matplotlib; el arranque pasó de 665 ms a 152 ms y el
  reporte mensual de 545 ms a 24 ms con 20 000 líneas.
- Costo promedio ponderado al comprar, historial de precios por producto y margen calculado
  con el costo vigente en cada venta (esquema v3).
- Respaldo automático al cerrar en `backups/` (se conservan 10) con restauración desde Ajustes.
- Boleta imprimible en PDF de 80 mm con los datos del negocio configurables.

### Fase 6 – Distribución
- Los datos viven en la carpeta de datos de la usuaria (`%APPDATA%\AgroNegocio` en Windows,
  `~/.local/share/agro-negocio` en Linux); una BD junto al programa se traslada sola la primera vez.
- `pyproject.toml`, `agro.spec` (PyInstaller, sin consola, con icono) y workflow que publica el
  zip de Windows en cada tag `vX.Y.Z`.

## [4.1] – versión original

`ventas14.py`: ventas al contado y al fiado, compras, inventario, cuentas por cobrar y reporte
mensual en un solo archivo con CustomTkinter, SQLite y pandas.
