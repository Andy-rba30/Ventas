# CLAUDE.md – Sistema Agro-Negocio Familiar

## Qué es
Aplicación de escritorio en Python (CustomTkinter + SQLite) para un negocio
familiar de fertilizantes agrícolas. Gestiona ventas al contado y al fiado,
compras a proveedores, inventario con cantidades fraccionarias (1/2 saco, 0.25 L),
cuentas por cobrar y reportes mensuales. Moneda: soles peruanos (S/.).

## Ejecutar
```bash
pip install -r requirements.txt
python ventas.py
```
La BD `negocio_final_stock.db` y el log `app.log` se crean en la carpeta desde
donde se ejecuta. En Linux hace falta `python3-tk`.

Pruebas (sin tocar la BD real):
- Capa de datos: `python scripts/prueba_bd.py`
- Interfaz headless: `xvfb-run -a python scripts/prueba_carrito.py`

## Convenciones
- Código, comentarios, mensajes de UI y commits en español. Funciones en
  `snake_case` español.
- Nunca `except:` desnudo ni `except Exception: pass`. Captura la excepción
  concreta y regístrala con `logging` (logger `agro`).
- Toda operación de BD que toque más de una fila o más de una tabla va dentro
  de `with self.db.transaccion():` para que se guarde todo o nada.
- La UI no ejecuta SQL: llama a métodos de `BaseDatos`.
- `ventas.py` usa finales de línea CRLF; conservarlos al editar.

## Datos de la usuaria
- Nunca borrar, sobrescribir ni migrar sin respaldo el archivo
  `negocio_final_stock.db` real. Las pruebas usan una BD temporal o `:memory:`.
- Los archivos `*.db`, `*.db-wal`, `*.db-shm` y `*.log` están en `.gitignore`.

## Hoja de ruta
Ver `PLAN_MEJORA.md`. Estado: Fase 0 y Fase 1 completas. Siguiente: Prompt 2.1.
