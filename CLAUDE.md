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

Pruebas (sin tocar la BD real; CI en `.github/workflows/tests.yml`, Python 3.11 y 3.12):
- Datos y servicios: `pip install -r requirements-dev.txt && pytest` (carpeta `tests/`,
  SQLite en memoria; `db_archivo` para WAL/respaldo/migración). Toda función nueva en
  `agro/db` o `agro/servicios` lleva su prueba aquí.
- Interfaz headless: `xvfb-run -a python scripts/prueba_carrito.py` (no es pytest).

## Estructura
```
main.py                    punto de entrada
agro/config.py             constantes (ruta BD, CLIENTE_GENERAL, umbral de stock...)
agro/registro.py           logger 'agro' -> app.log
agro/preferencias.py       config.json junto a la BD: apariencia, geometría, último respaldo
agro/db/                   SQLite. BaseDatos = Conexion + repositorios
   conexion.py             PRAGMAs, transaccion(), respaldo, introspección; llama a migraciones
   esquema.py              DDL actual (productos, clientes, proveedores, encargadas, boletas,
                           boleta_lineas, pagos) + índices. VERSION_ESQUEMA (=2) en PRAGMA user_version
   migraciones.py          pasos encadenados _PASOS[version]: v0 (tabla plana) -> v1 (boletas),
                           v1 -> v2 (notas en contactos). Copia previa en backups/ con la versión
                           de origen en el nombre; la tabla vieja queda como _legacy_transacciones
   productos.py            db.productos.*  (dataclass Producto; no se borran: se desactivan)
   boletas.py              db.boletas.*    (Boleta, LineaBoleta, Pago; pagos parciales;
                           eliminar_boleta/linea/pago con reversión de stock)
   contactos.py            db.contactos.*  (dataclass Contacto con notas; obtener/modificar;
                           clientes, proveedores y encargadas con historial se desactivan)
agro/servicios/            lógica de negocio sin Tk
   formato.py              moneda(), cantidad(), parse_cantidad(), MESES
   carrito.py              Carrito / LineaCarrito
   operaciones.py          ServicioOperaciones: venta, fiado, compra, cobro, eliminar
   reportes.py             ServicioReportes: Reporte por periodo (pandas por ahora)
agro/ui/tema.py            tokens: COLOR (semánticos), ESPACIO, fuente(nombre),
                           aplicar_estilo_treeview(modo) para claro/oscuro
agro/ui/componentes.py     Tabla (Treeview+scroll, filas dict, arbol=True), Columna,
                           Tarjeta, Encabezado, Campo (validación visual), Toast,
                           boton_primario/info/exito/alerta/fiado/peligro/secundario
agro/ui/app.py             Aplicacion: sidebar (NAVEGACION), encargada activa, atajos
                           F1-F8/Ctrl+B/Esc, apariencia, respaldo, refrescos cruzados, app.toast
agro/ui/dialogos.py        calendario, alta rápida de contacto, elegir_opcion, historial de cliente
agro/ui/pantallas/         una pantalla por archivo (inicio, fiados, inventario, contactos,
                           reportes, ajustes). Ventas y Compras son la misma clase
                           movimiento.PantallaMovimiento(modo="venta"|"compra"); agregar al
                           carrito pasa por dialogos.DialogoCantidad (no bloqueante, callback).
                           Inventario y Contactos son maestro-detalle: tabla 65 % + panel 35 %
                           con un Formulario* (cargar/leer/enfocar); el alta reutiliza el mismo
                           formulario dentro de dialogos.DialogoFormulario
```
Protocolo opcional de una pantalla (la app llama lo que exista): `al_mostrar()`,
`refrescar_productos()`, `refrescar_contactos(clientes, proveedores)`, `refrescar_fiados()`,
`limpiar_seleccion()` (Esc) y el atributo `ent_buscar` (Ctrl+B). Para añadir una pantalla
basta con sumar una entrada a `NAVEGACION` en app.py.

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
- UI: ningún literal hex, `ttk.Treeview`, `ttk.Style` ni `CTkFont(...)` fuera de
  `agro/ui/tema.py` y `agro/ui/componentes.py`. Colores por token (`COLOR["exito"]`),
  fuentes con `fuente("subtitulo")`, tablas con `Tabla`, botones con las fábricas
  `boton_*`. Etiquetas de fila con significado fijo: `"alerta"` (stock bajo, deuda)
  y `"resaltada"` (cabecera de boleta).
- Finales de línea LF en todo el paquete.
- Cambios de esquema: nueva versión en `esquema.VERSION_ESQUEMA` + función de migración
  en `migraciones.py` con copia previa; nunca ALTER a mano sobre la BD real.
- Para eliminar desde el reporte se usan claves `"B:<id>"` (boleta), `"L:<id>"` (línea)
  y `"P:<id>"` (pago); `ServicioOperaciones.eliminar_operaciones` las interpreta.

## Datos de la usuaria
- Nunca borrar, sobrescribir ni migrar sin respaldo el archivo
  `negocio_final_stock.db` real. Las pruebas usan una BD temporal o `:memory:`.
- Los archivos `*.db`, `*.db-wal`, `*.db-shm` y `*.log` están en `.gitignore`.

## Hoja de ruta
Ver `PLAN_MEJORA.md`. Estado: Fases 0 a 3 completas; 4.1 a 4.4 hechos (tokens, componentes,
sidebar, Ajustes, Inicio básico, atajos, Ventas/Compras unificadas, Inventario y Contactos en
maestro-detalle, esquema v2). Siguiente: Prompt 4.5 (Fiados por cliente y pagos parciales).

Nota para pruebas de UI headless: una ventana `withdraw()` no recibe teclas sintéticas
(`event_generate` de F-keys, Supr, KeyRelease); para probar atajos hay que `deiconify()` +
`focus_force()` antes, o llamar al manejador directamente.
