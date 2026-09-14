# CLAUDE.md – Sistema Agro-Negocio Familiar

## Qué es
Aplicación de escritorio en Python (CustomTkinter + SQLite) para un negocio
familiar de fertilizantes agrícolas. Gestiona ventas al contado y al fiado,
compras a proveedores, inventario con cantidades fraccionarias (1/2 saco, 0.25 L),
cuentas por cobrar y reportes mensuales. Moneda: soles peruanos (S/.).

## Ejecutar
```bash
pip install -r requirements.txt
python main.py          # (ventas.py es un stub obsoleto que llama a main)
```
La BD `negocio_final_stock.db` y el log `app.log` se crean en la carpeta desde
donde se ejecuta. En Linux hace falta `python3-tk`.

Pruebas (sin tocar la BD real):
- Capa de datos y servicios: `python scripts/prueba_bd.py`
- Interfaz headless: `xvfb-run -a python scripts/prueba_carrito.py`

## Estructura
```
main.py                    punto de entrada
agro/config.py             constantes (ruta BD, CLIENTE_GENERAL, umbral de stock...)
agro/registro.py           logger 'agro' -> app.log
agro/db/                   SQLite. BaseDatos = Conexion + repositorios
   conexion.py             PRAGMAs, esquema, migraciones, transaccion(), respaldo
   productos.py            db.productos.*   (dataclass Producto)
   transacciones.py        db.transacciones.* (fiados, cobros, reversión)
   contactos.py            db.contactos.*   (clientes, proveedores, encargadas)
agro/servicios/            lógica de negocio sin Tk
   formato.py              moneda(), cantidad(), parse_cantidad(), MESES
   carrito.py              Carrito / LineaCarrito
   operaciones.py          ServicioOperaciones: venta, fiado, compra, cobro, eliminar
   reportes.py             ServicioReportes: Reporte por periodo (pandas por ahora)
agro/ui/app.py             Aplicacion: sidebar, navegación, refrescos cruzados
agro/ui/dialogos.py        calendario, alta rápida de contacto, historial de cliente
agro/ui/pantallas/         una pantalla por archivo; Ventas y Compras heredan de
                           movimiento_base.PantallaMovimiento
```
Refrescos cruzados: una pantalla nunca toca widgets de otra. Llama a
`app.refrescar_productos()`, `app.refrescar_contactos()`, `app.refrescar_fiados()`
o `app.refrescar_reportes()`, y cada pantalla implementa el método que necesite.

## Convenciones
- Código, comentarios, mensajes de UI y commits en español. Funciones en
  `snake_case` español.
- Nunca `except:` desnudo ni `except Exception: pass`. Captura la excepción
  concreta y regístrala con `logging` (logger `agro`).
- Toda operación de BD que toque más de una fila o más de una tabla va dentro
  de `with db.transaccion():` para que se guarde todo o nada.
- La UI no ejecuta SQL ni contiene reglas de negocio: llama a `agro.servicios`
  o a los repositorios de `agro.db`. Las validaciones de negocio lanzan
  `ErrorOperacion` con el mensaje listo para mostrar.
- Formato de dinero y cantidades solo con `formato.moneda()` y `formato.cantidad()`.
- Finales de línea LF en todo el paquete.

## Datos de la usuaria
- Nunca borrar, sobrescribir ni migrar sin respaldo el archivo
  `negocio_final_stock.db` real. Las pruebas usan una BD temporal o `:memory:`.
- Los archivos `*.db`, `*.db-wal`, `*.db-shm` y `*.log` están en `.gitignore`.

## Hoja de ruta
Ver `PLAN_MEJORA.md`. Estado: Fases 0 y 1 completas; 2.1 hecho. Siguiente: Prompt 2.2.
