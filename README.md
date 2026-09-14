# Ventas – Sistema Agro-Negocio Familiar

Aplicación de escritorio (Python + CustomTkinter + SQLite) para administrar un
negocio familiar de fertilizantes agrícolas: ventas, compras, fiados,
inventario, contactos y reportes.

## Requisitos

- Python 3.10+
- Tkinter (viene con Python en Windows/macOS; en Linux `sudo apt install python3-tk`)

```bash
pip install -r requirements.txt
```

## Ejecutar

```bash
python main.py
```

(`ventas.py` se conserva como acceso directo obsoleto: solo llama a `main`.)

## Estructura

- `agro/db/`: SQLite (conexión, esquema versionado y migraciones, repositorios de productos, boletas/pagos y contactos).
- `agro/servicios/`: lógica de negocio sin interfaz (carrito, operaciones, reportes, formato).
- `agro/ui/`: ventana principal, diálogos y una pantalla por archivo.
- `tests/`: pruebas pytest de datos y servicios con SQLite en memoria (`pip install -r requirements-dev.txt && pytest`).
- `scripts/prueba_carrito.py`: prueba de la interfaz sin pantalla (`xvfb-run -a python scripts/prueba_carrito.py`).

Ambas corren en GitHub Actions en cada push (Python 3.11 y 3.12).

La base de datos `negocio_final_stock.db` se crea automáticamente en la carpeta
desde donde se ejecuta el programa, junto con `config.json` (apariencia, tamaño de
ventana y último respaldo) y `app.log`.

Atajos: F1 a F8 cambian de pantalla en el orden del menú, Ctrl+B enfoca el buscador
de la pantalla actual y Esc limpia la selección.

## Módulos

| Pantalla    | Qué hace |
|-------------|----------|
| Ventas      | Carrito de venta con soporte de fracciones (1/2, 0.25), edición de precio/cantidad/subtotal, venta al contado o fiado |
| Compras     | Ingreso de mercadería por proveedor, actualiza stock y costo de compra |
| Contactos   | Alta y baja de clientes y proveedores |
| Fiados      | Cuentas por cobrar, registro de pagos e historial por cliente |
| Inventario  | Crear, editar y borrar productos; lista de precios y stock |
| Reportes    | Filtro por mes/día/cliente/proveedor, tarjetas resumen, gráfico y exportación a Excel |
| Inicio      | Deuda total, productos bajo mínimo y accesos a Nueva venta / Ingreso de mercadería |
| Ajustes     | Encargadas, respaldo y restauración, apariencia (claro/oscuro/sistema) y versión |

## Migración de datos (v4.1 → v4.2)

Al abrir por primera vez una base de datos de la versión anterior, el programa la
migra solo al nuevo esquema (boletas con líneas y pagos). Antes guarda una copia en
`backups/negocio_pre_migracion_<fecha>.db` junto a la base, y conserva la tabla
antigua como `_legacy_transacciones`. Los detalles quedan en `app.log`.

Consulta [PLAN_MEJORA.md](PLAN_MEJORA.md) para el plan de refactorización y
mejora de la interfaz.
