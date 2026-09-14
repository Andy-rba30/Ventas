# Ventas – Sistema Agro-Negocio Familiar

Aplicación de escritorio (Python + CustomTkinter + SQLite) para administrar un
negocio familiar de fertilizantes agrícolas: ventas, compras, fiados,
inventario, contactos y reportes.

## Instalar en Windows (sin Python)

Descarga el zip `AgroNegocio-vX.Y.Z-windows.zip` de la última
[versión publicada](https://github.com/Andy-rba30/Ventas/releases), descomprímelo en cualquier
carpeta y abre `AgroNegocio.exe`. Los datos se guardan en `%APPDATA%\AgroNegocio` (la ruta exacta
aparece en Ajustes); si tenías una `negocio_final_stock.db` junto al programa de una versión
anterior, la primera vez se traslada allí sola y el programa lo avisa.

## Requisitos (para ejecutar desde el código)

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

- `agro/db/`: SQLite (conexión, esquema versionado y migraciones, repositorios de productos, boletas/pagos, contactos e historial de precios).
- `agro/servicios/`: lógica de negocio sin interfaz (carrito, operaciones, reportes, formato).
- `agro/ui/`: ventana principal, diálogos y una pantalla por archivo.
- `tests/`: pruebas pytest de datos y servicios con SQLite en memoria (`pip install -r requirements-dev.txt && pytest`).
- `scripts/prueba_carrito.py`: prueba de la interfaz sin pantalla (`xvfb-run -a python scripts/prueba_carrito.py`).
- `scripts/generar_datos_prueba.py`: crea una BD de prueba con miles de boletas para medir rendimiento (nunca la real).

Ambas corren en GitHub Actions en cada push (Python 3.11 y 3.12).

La base de datos `negocio_final_stock.db` se crea automáticamente en la carpeta de datos
de la usuaria (`%APPDATA%\AgroNegocio` en Windows, `~/.local/share/agro-negocio` en Linux),
junto con `config.json` (apariencia, tamaño de ventana, último respaldo y datos del negocio)
y `app.log`. La variable de entorno `AGRO_DATOS` permite usar otra carpeta (por ejemplo un USB).

Al cerrar el programa se guarda una copia automática en `backups/negocio_AAAAMMDD_HHMMSS.db`
junto a la base de datos y se conservan las 10 más recientes (las copias previas a una
migración no se borran). Desde Ajustes se puede restaurar cualquiera de ellas; antes de
reemplazar los datos se guarda una copia más de los actuales.

Las boletas imprimibles se generan como PDF tipo ticket (80 mm de ancho) en la carpeta
`boletas/` junto a la base de datos y se abren con el visor de PDF del sistema. Requieren
el paquete `reportlab` (incluido en `requirements.txt`).

Atajos: F1 a F8 cambian de pantalla en el orden del menú, Ctrl+B enfoca el buscador
de la pantalla actual, Esc limpia la selección; en Ventas y Compras, Ctrl+Enter cobra
y Supr quita la línea seleccionada del carrito.

## Módulos

| Pantalla    | Qué hace |
|-------------|----------|
| Ventas      | Buscar producto, doble clic o Enter para elegir cantidad (acepta 1/2), carrito editable, un solo botón Cobrar / Registrar fiado con el monto, e Imprimir última boleta (PDF de 80 mm) |
| Compras     | Misma pantalla que Ventas en modo compra: cantidad y costo unitario por línea, suma stock y recalcula el costo del producto como promedio ponderado |
| Contactos   | Maestro-detalle: tabla a la izquierda, ficha editable a la derecha (documento, teléfono, notas), deuda pendiente y acceso a sus fiados |
| Fiados      | Deudores con días de antigüedad; por cliente, sus boletas con saldo, pagos parciales o totales con fecha, encargada y nota, e historial de pagos |
| Inventario  | Maestro-detalle: tabla con unidad, stock, mínimo, precios y margen; ficha editable con historial de precios de compra y venta; desactivar/reactivar; ver inactivos |
| Reportes    | Selector de mes con filtros plegables (día, cliente, proveedor, tipo); pestaña Resumen (caja, compras, margen bruto calculado con el costo vigente en cada venta, por cobrar, movimiento por producto) y pestaña Movimientos (boletas con líneas, imprimir boleta, exportar Excel, eliminar) |
| Inicio      | Ventas de hoy, fiados pendientes, productos bajo mínimo, listas de reposición y fiados con más de 30 días, accesos a Nueva venta / Ingreso de mercadería |
| Ajustes     | Encargadas, datos del negocio para la boleta (nombre, RUC, dirección), respaldo manual, lista de respaldos automáticos con restauración, apariencia (claro/oscuro/sistema) y versión |

## Migración de datos (v4.1 → v4.2)

Al abrir por primera vez una base de datos de la versión anterior, el programa la
migra solo al nuevo esquema (boletas con líneas y pagos). Antes guarda una copia en
`backups/negocio_pre_migracion_v<versión>_<fecha>.db` junto a la base, y conserva la tabla
antigua como `_legacy_transacciones`. Los detalles quedan en `app.log`.

## Construir el ejecutable y publicar una versión

```bash
pip install pyinstaller
pyinstaller agro.spec --noconfirm      # -> dist/AgroNegocio/
```

Para publicar: sube la versión en `agro/__init__.py`, anota los cambios en
[CHANGELOG.md](CHANGELOG.md) y crea el tag:

```bash
git tag v4.2.0 && git push origin v4.2.0
```

El workflow `Release Windows` construye el ejecutable en Windows, comprueba que arranca y
adjunta el zip al Release de GitHub.

Consulta [PLAN_MEJORA.md](PLAN_MEJORA.md) para el plan de refactorización y
mejora de la interfaz, y [CHANGELOG.md](CHANGELOG.md) para el historial de cambios.
