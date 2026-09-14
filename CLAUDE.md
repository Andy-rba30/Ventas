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
agro/preferencias.py       config.json junto a la BD: apariencia, geometría, último respaldo,
                           negocio {nombre, ruc, direccion} para la boleta
agro/db/                   SQLite. BaseDatos = Conexion + repositorios
   conexion.py             PRAGMAs, transaccion(), respaldo, introspección; llama a migraciones
   esquema.py              DDL actual (productos, clientes, proveedores, encargadas, boletas,
                           boleta_lineas con costo_unit, pagos, precios_historial) + índices.
                           VERSION_ESQUEMA (=3) en PRAGMA user_version
   migraciones.py          pasos encadenados _PASOS[version]: v0 (tabla plana) -> v1 (boletas),
                           v1 -> v2 (notas en contactos), v2 -> v3 (costo_unit por línea y
                           precios_historial). Copia previa en backups/ con la versión de origen
                           en el nombre; la tabla vieja queda como _legacy_transacciones
   productos.py            db.productos.*  (dataclass Producto; no se borran: se desactivan;
                           agregar/modificar anotan los precios en db.precios)
   precios.py              db.precios.*    (PrecioHistorico; registrar, historial, ultimo)
   boletas.py              db.boletas.*    (Boleta, LineaBoleta con costo_unit, Pago; pagos
                           parciales; eliminar_boleta/linea/pago con reversión de stock)
   contactos.py            db.contactos.*  (dataclass Contacto con notas; obtener/modificar;
                           clientes, proveedores y encargadas con historial se desactivan)
   reportes.py             db.reportes.*   consultas agregadas por Filtro(anio, mes, dia, cliente,
                           proveedor, tipo): totales_por_tipo, total_pagos, costo_vendido,
                           movimiento_por_producto, boletas_periodo, pagos_periodo, meses_con_datos
agro/servicios/            lógica de negocio sin Tk (sin pandas ni matplotlib en todo el paquete)
   formato.py              moneda(), cantidad(), parse_cantidad(), tamano_archivo(), MESES
   carrito.py              Carrito / LineaCarrito
   costos.py               costo_promedio() ponderado (función pura)
   operaciones.py          ServicioOperaciones: venta, fiado, compra, cobro, eliminar.
                           registrar_venta/compra devuelven el id de la boleta; la venta guarda
                           en cada línea el costo promedio vigente y la compra recalcula
                           productos.precio_compra como promedio ponderado
   reportes.py             ServicioReportes: Reporte por periodo sobre db.reportes, resumen_inicio,
                           exportar_excel (delegado a exportar.py)
   exportar.py             Excel con openpyxl (se importa solo al exportar)
   respaldos.py            respaldar_automatico(db) -> backups/negocio_YYYYMMDD_HHMMSS[_N].db junto a la
                           BD, rotación (CONSERVAR=10, solo los automáticos), listar_respaldos, carpeta_de
   sistema.py              abrir_archivo(ruta) con el programa del sistema (startfile / open / xdg-open)
   boleta_pdf.py           generar(boleta, negocio, ruta): ticket PDF de 80 mm con reportlab (importado
                           solo al generar); ruta_para(ruta_db, id) -> boletas/boleta_000012.pdf junto a la BD
agro/ui/tema.py            tokens: COLOR (semánticos), ESPACIO, fuente(nombre),
                           aplicar_estilo_treeview(modo) para claro/oscuro
agro/ui/componentes.py     Tabla (Treeview+scroll, filas dict, arbol=True), Columna,
                           Tarjeta, Encabezado, Campo (validación visual), Toast,
                           boton_primario/info/exito/alerta/fiado/peligro/secundario
agro/ui/app.py             Aplicacion: sidebar (NAVEGACION), encargada activa, atajos
                           F1-F8/Ctrl+B/Esc, apariencia, refrescos cruzados, app.toast. Respaldo:
                           respaldar_bd (manual), respaldo_automatico (al cerrar, nunca bloquea el
                           cierre), restaurar_bd / restaurar_desde(ruta) (confirma y antes guarda
                           una copia automática de los datos actuales). imprimir_boleta(id, abrir=True)
                           genera el PDF y lo abre con el visor del sistema
agro/ui/dialogos.py        calendario, alta rápida de contacto, elegir_opcion, historial de cliente
agro/ui/pantallas/         una pantalla por archivo (inicio, fiados, inventario, contactos,
                           reportes, ajustes). Ventas y Compras son la misma clase
                           movimiento.PantallaMovimiento(modo="venta"|"compra"); agregar al
                           carrito pasa por dialogos.DialogoCantidad (no bloqueante, callback).
                           procesar() guarda ultima_boleta_id y habilita "Imprimir última"; Reportes >
                           Movimientos tiene "Imprimir boleta" para la fila seleccionada (solo claves B:).
                           Inventario y Contactos son maestro-detalle: tabla 65 % + panel 35 %
                           con un Formulario* (cargar/leer/enfocar); el alta reutiliza el mismo
                           formulario dentro de dialogos.DialogoFormulario.
                           Fiados: deudores (db.boletas.resumen_deudores) a la izquierda; a la
                           derecha boletas con saldo, dialogos.DialogoPago (parcial o total) e
                           historial (pagos_de_cliente). seleccionar_cliente(nombre) lo usa
                           Contactos > Ver fiados.
                           Reportes: selector ◀ mes ▶ + Hoy, panel de filtros plegable (día,
                           cliente, proveedor, tipo; cada cambio consulta), pestañas Resumen
                           (tarjetas, barra caja, movimiento por producto) y Movimientos
                           (Tabla arbol con claves B:/L:/P:, exportar filtrado, eliminar).
                           Inicio: ServicioReportes.resumen_inicio (ventas de hoy, por cobrar,
                           bajo mínimo, fiados > 30 días) y accesos rápidos
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
Ver `PLAN_MEJORA.md`. Estado: Fases 0 a 4 completas; 5.1 hecho (reportes en SQL, sin pandas ni
matplotlib; `tests/test_arranque.py` vigila que no vuelvan); 5.2 hecho (costo promedio ponderado e
historial de precios con esquema v3, respaldo automático con rotación, boleta PDF imprimible).
Siguiente: Prompt 6.1 (ejecutable para Windows).

Rendimiento (BD de 20 000 líneas de `scripts/generar_datos_prueba.py`): importar `agro.ui.app`
665 ms -> 152 ms; `ServicioReportes.generar` de un mes 545 ms -> 24 ms; `resumen_inicio` 31 -> 4 ms.

Nota para pruebas de UI headless: una ventana `withdraw()` no recibe teclas sintéticas
(`event_generate` de F-keys, Supr, KeyRelease); para probar atajos hay que `deiconify()` +
`focus_force()` antes, o llamar al manejador directamente.
