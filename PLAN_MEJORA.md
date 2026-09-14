# Plan de mejora – Sistema Agro-Negocio Familiar

Análisis de `ventas.py` (1 419 líneas) y plan de acción en fases. Cada fase
tiene uno o más **prompts listos para pegar en Claude Code**. Están ordenados
para que cada uno construya sobre el anterior: ejecútalos en orden, uno por
sesión, y revisa el resultado antes de pasar al siguiente.

---

## 1. Diagnóstico

### 1.1 Arquitectura

| Aspecto | Estado actual | Problema |
|---|---|---|
| Estructura | Un solo archivo, dos clases: `BaseDatos` (230 líneas) y `Aplicacion` (1 160 líneas) | La clase de UI construye 6 pantallas, contiene la lógica de negocio y hace SQL directo (`ventas.py:1165`, `ventas.py:1360`). Imposible de probar sin abrir la ventana. |
| Duplicación | Ventas y Compras son copias casi idénticas: pantalla (`389` vs `477`), edición de celda (`848` vs `913`, 65 líneas cada una), quitar del carrito (`825` vs `837`), agregar al carrito (`1063` vs `1086`). Formularios de Clientes y Proveedores también duplicados. | Cada corrección hay que hacerla dos veces. ~250 líneas redundantes. |
| Estilo | 26 literales hex de color repartidos por el código, 14 repeticiones de `f"S/. {x:.2f}"`, el diccionario de meses definido 3 veces. | Sin tokens de diseño ni utilidades; cambiar un color o el formato de moneda toca decenas de líneas. |
| Errores | 8 `except:` desnudos o `except Exception` que devuelven `False`/`pass` (`101`, `134`, `210`, `241`, `249`, `986`, `1069`, `1092`). | Los fallos se tragan en silencio. No hay logging. |
| Dependencias | `pandas` y `matplotlib` se usan para filtrar una tabla y dibujar un gráfico de 2 barras. | Arranque lento y un ejecutable de ~150 MB si se empaqueta. SQL puede hacer todo el filtrado. |
| Pruebas | Ninguna. | Cualquier refactor es a ciegas. |

### 1.2 Bugs confirmados (por prioridad)

1. **Crash al agregar al carrito** (`ventas.py:1071` y `1094`). Cada vez que se recarga la tabla de inventario (al escribir en el buscador o tras agregar un ítem) el `Treeview` pierde la selección, pero la etiqueta del producto sigue mostrando el nombre. El siguiente clic en "Agregar" ejecuta `selection()[0]` sobre una lista vacía y lanza `IndexError`. Escenario típico: vender el mismo producto dos veces seguidas.
2. **Corrupción al renombrar producto** (`ventas.py:113-127`). `modificar_producto` primero renombra el producto en `transacciones` y después en `productos`. Si el nuevo nombre ya existe, el segundo `UPDATE` falla con `IntegrityError`, se devuelve `False` **sin rollback**, y el `commit()` de la siguiente operación persiste el historial renombrado hacia un producto que no se renombró.
3. **Ventas sin transacción atómica** (`ventas.py:1140-1145`). Cada línea del carrito se descuenta y confirma por separado. Si el programa falla a mitad de una boleta de 4 productos, quedan 2 registrados y 2 no.
4. **Eliminar un cobro no revierte el fiado** (`ventas.py:176-191`). `eliminar_transaccion_y_reversar_stock` solo trata `VENTA`, `FIADO` y `ENTRADA`. Borrar un `COBRO_DEUDA` deja el fiado como `PAGADO`; borrar un `FIADO` ya pagado devuelve el stock pero conserva el cobro, así que el dinero queda contado sin producto.
5. **Cobro de deuda con datos falsos** (`ventas.py:173`). El pago se registra con `encargada="Admin"` (no existe en la tabla `encargadas`), `cantidad=1` y siempre fecha de hoy. No hay pagos parciales.
6. **Doble disparo al editar celdas** (`ventas.py:908-909`, `971-972`). `<Return>` y `<FocusOut>` llaman a la misma función; `Return` destruye el `Entry`, el `FocusOut` posterior llama `entry.get()` sobre un widget destruido y lanza `TclError` (no capturado, solo `ValueError`).
7. **Ruta de BD hardcodeada** (`ventas.py:354`, `364`). Respaldar y restaurar usan el literal `"negocio_final_stock.db"` en vez de `self.db.db_name`. Restaurar tampoco refresca el combo de encargadas ni el de edición de productos.
8. **Agrupación de boletas frágil** (`ventas.py:1230`). Las boletas del reporte se reconstruyen concatenando `fecha + hora + tipo`. Dos ventas en el mismo segundo se fusionan; no existe una entidad "boleta" en la BD.
9. **Stock de cierre incorrecto en fechas pasadas**. `stock_resultante` guarda el stock actual aunque la venta se registre con fecha anterior, así que el "Stock Cierre" del reporte de meses pasados es falso.
10. **Tarjeta "Por cobrar" engañosa** (`ventas.py:1209`). Suma solo los fiados *creados* en el mes filtrado, no la deuda total pendiente.
11. **`parse_cantidad("1/0")`** lanza `ZeroDivisionError`; `crear_producto` solo captura `ValueError`.
12. **`obtener_total_stock_actual`** devuelve un `str` o el entero `0` según el caso.

### 1.3 Por qué la interfaz se siente saturada

| Pantalla | Causa concreta |
|---|---|
| **Sidebar** | Mezcla navegación con administración de encargadas (combo + botones `+`/`🗑`) y con respaldo/restauración. Son tres responsabilidades en 220 px. El botón activo no se resalta. |
| **Ventas / Compras** | El panel derecho de 350 px apila 13 elementos: fecha, producto, cantidad, tabla, texto de ayuda en cursiva, total, 2 botones de quitar, etiqueta cliente, combo, botón `➕`, y 2 botones grandes de finalizar. El texto "(Doble clic en Precio, Cantidad o Subtotal para editar)" ocupa espacio permanente para algo que se aprende una vez. |
| **Inventario** | Dos formularios horizontales: crear (9 widgets en una fila) y editar (12 widgets en una fila, `ventas.py:696-720`). A 1 200 px ya se recortan; a menos, desaparecen botones. El combo "Seleccione" duplica lo que ya hace el clic en la tabla. |
| **Contactos** | Formulario de 8 widgets en una fila horizontal encima de la tabla. Botón "Borrar" al lado de "Guardar" con el mismo peso visual. |
| **Reportes** | En 800 px de alto: barra de 7 filtros, 5 tarjetas, tabla resumen y gráfico a 180 px fijos, toolbar, tabla cronológica y botón de exportar. Nada tiene aire. El gráfico de 2 barras aporta poco a ese costo. |
| **Global** | Ventana fija 1200×800 sin `minsize`; mezcla `ttk.Treeview` estilo *clam* con CustomTkinter; emojis como iconos (se renderizan distinto en cada sistema); `messagebox.showinfo("Éxito")` interrumpe el flujo tras cada venta; sin atajos de teclado ni `Enter` para agregar al carrito. |

---

## 2. Plan de acción por fases

```
Fase 0  Preparar el repo (CLAUDE.md, entorno)              ~1 sesión
Fase 1  Corregir bugs críticos sin rediseñar                ~1-2 sesiones
Fase 2  Separar en paquete + pruebas de la capa de datos    ~2 sesiones
Fase 3  Modelo de datos: boletas, pagos, IDs, migración     ~2 sesiones
Fase 4  Rediseño de interfaz (la saturación)                ~3-4 sesiones
Fase 5  Optimización funcional (reportes SQL, fiados, etc.) ~2-3 sesiones
Fase 6  Empaquetado y distribución                          ~1 sesión
```

Regla general para todos los prompts: **una fase por rama**, con commits
pequeños. Antes de la Fase 3 haz una copia manual de tu `negocio_final_stock.db`
real y guárdala fuera del repo.

---

## Fase 0 – Preparación

### Prompt 0.1 – Crear CLAUDE.md y verificar entorno

```
Estamos en el repo Ventas, una app de escritorio Python (CustomTkinter + SQLite)
para un negocio familiar de fertilizantes agrícolas. Lee README.md, PLAN_MEJORA.md
y ventas.py completo.

Crea un archivo CLAUDE.md en la raíz con:
- Descripción del proyecto en 3 líneas y el dominio (ventas, compras, fiados,
  inventario con fracciones como 1/2 saco, reportes mensuales, moneda S/.).
- Cómo instalar y ejecutar (pip install -r requirements.txt, python ventas.py).
- Convenciones: código y comentarios en español, nombres de funciones en
  snake_case español, commits en español, no usar except desnudos, toda
  operación de BD multi-fila debe ir dentro de una transacción.
- Regla: nunca borrar ni modificar el archivo negocio_final_stock.db del usuario;
  las pruebas usan SQLite en memoria.
- Referencia a PLAN_MEJORA.md como hoja de ruta y la fase actual.

Después crea un entorno virtual, instala dependencias y verifica que
`python -c "import ventas"` no falle (sin abrir la ventana: protege la
creación de Aplicacion() bajo if __name__ == "__main__" si no lo está ya).
No cambies ninguna otra línea de ventas.py.
```

---

## Fase 1 – Bugs críticos (sin tocar el diseño)

> **Estado:** Prompt 0.1 ✅ · 1.1 ✅ · 1.2 ✅ · 2.1 ✅ · 2.2 ✅ · 3.1 ✅ · 4.1 ✅ · 4.2 ✅ · 4.3 ✅ · 4.4 ✅ · 4.5 ✅ · 4.6 ✅ · 5.1 ✅ · 5.2 ⏳ (mejora 1 de 3 hecha).
> **Fases 0 a 4 completas; Fase 5 en curso.** Siguiente: 5.2 (respaldo automático y boleta imprimible).
>
> Resultado del 5.1 (BD de 20 000 líneas, 6 694 boletas, generada con
> `scripts/generar_datos_prueba.py`): importar la app pasó de 665 ms a 152 ms (pandas
> solo pesaba 466 ms); el reporte de un mes pasó de 545 ms a 24 ms (mediana de 5
> corridas) y el resumen de Inicio de 31 ms a 4 ms, con resultados idénticos. pandas y
> matplotlib salieron de `requirements.txt`; Excel se escribe con openpyxl en
> `servicios/exportar.py`. Las consultas viven en `agro/db/reportes.py`
> (`RepositorioReportes` + `Filtro`); el servicio solo arma dataclasses. El 4.6 dejó Reportes con selector de mes,
> botón Hoy y filtros plegables (día, cliente, proveedor, tipo) que consultan al cambiar;
> pestaña Resumen (ingresos, compras, margen bruto = vendido − cantidad × precio_compra
> actual, por cobrar total con subtexto del periodo, barra caja y movimiento por producto
> con stock actual) y pestaña Movimientos (boletas con líneas, exportar Excel filtrado a
> hojas Boletas y Líneas con cabeceras en negrita, eliminar). Se eliminó el gráfico y la
> dependencia matplotlib. Inicio completo: ventas de hoy, fiados pendientes, bajo mínimo,
> listas de reposición y fiados > 30 días, accesos rápidos. Nota para 5.2: el margen usa el
> precio_compra actual del producto; `costo_unit` por línea llega con ese prompt.
> Pruebas: 149 pytest + 18 de UI. El 4.5 dejó Fiados con la
> tabla de deudores (cliente, boletas, deuda, más antigua, días; en rojo pasados 30 días),
> tarjeta de total por cobrar, panel del cliente con sus boletas con saldo (doble clic =
> detalle), diálogo de pago con monto parcial, fecha, encargada y nota, e historial de
> pagos. Sin botón "Actualizar". Pruebas: 143 pytest + 18 de UI. El 4.4 dejó Inventario y
> Contactos en maestro-detalle (tabla 65 % + panel 35 %, alta en diálogo con el mismo
> formulario, desactivar/reactivar productos, "Mostrar inactivos", deuda por cliente y
> "Ver fiados" que filtra la pantalla Fiados). Para el campo Notas de contactos se añadió
> el esquema v2 (migración v1→v2 encadenada, copia previa con la versión en el nombre).
> Pruebas: 139 pytest + 18 de UI. El 4.3 dejó una sola
> `PantallaMovimiento(modo)` para Ventas y Compras: encabezado con fecha y
> cliente/proveedor, buscador con Enter, diálogo de cantidad (precio editable solo en
> compra), carrito 60/40 con tooltip, un solo botón con el monto (Cobrar / Registrar
> fiado / Registrar ingreso) deshabilitado con carrito vacío o fiado a PÚBLICO GENERAL,
> Toast de éxito, y atajos Ctrl+Enter y Supr. Desvío: el botón dice "Registrar fiado"
> (no "Cobrar") cuando el selector está en Fiado. Pruebas: 130 pytest + 17 de UI. Tras el 4.1 no queda
> ningún hex, `ttk.Treeview` ni `CTkFont` fuera de `agro/ui/tema.py` y
> `agro/ui/componentes.py`. El 4.2 dejó el sidebar solo con navegación (Inicio,
> Ventas, Compras, Fiados, Inventario, Contactos, Reportes, Ajustes), la pantalla
> Ajustes, `config.json` (apariencia, geometría, último respaldo), minsize 1024x680
> y atajos F1-F8, Ctrl+B y Esc. Iconos: se quitaron los emojis del menú (texto
> corto). Inicio existe ya con tarjetas y accesos rápidos; el 4.6 la completa.
> Pruebas: 130 pytest + 15 de UI. Paquete `agro/`, entrada `main.py`, `ventas.py` es un stub. Esquema v1
> (boletas + líneas + pagos, productos/contactos por id, PRAGMA user_version) con
> migración automática desde la tabla plana y copia previa en `backups/`.
> Pruebas: `pytest` (123 casos en `tests/`) y `scripts/prueba_carrito.py` (UI con
> Xvfb, 14 casos); ambas corren en GitHub Actions con Python 3.11 y 3.12.
> Siguiente: Prompt 4.1.
>
> Notas del 3.1: el modelo ya soporta pagos parciales (`cobrar_fiado(monto=...)`),
> pero la pantalla Fiados sigue cobrando el saldo completo hasta el 4.5. El reporte
> ya expone `por_cobrar_total` (deuda global) además de `por_cobrar` del periodo,
> listo para el 4.6. Las claves `B:`/`L:`/`P:` permiten borrar boletas, líneas o
> pagos desde el detalle cronológico.
>
> Desvíos respecto al prompt 2.1: el servicio de venta/compra se llama
> `servicios/operaciones.py` (no `servicios/ventas.py`) para no confundirlo con
> `ui/pantallas/ventas.py`; y Ventas/Compras comparten
> `ui/pantallas/movimiento_base.py`, lo que adelanta parte del 4.3.
>
> Nota para 2.2: los dos scripts ya cubren gran parte de los casos pedidos; el
> prompt debe convertirlos a pytest, no reescribirlos.

### Prompt 1.1 – Crash al agregar al carrito y edición de celdas

```
En ventas.py hay dos bugs de interfaz que debes corregir sin rediseñar nada:

1. En agregar_al_carrito_ventas (línea ~1071) y agregar_al_carrito_compras
   (~1094) se usa self.tree_ventas.selection()[0]. Cuando la tabla se recarga
   (al buscar o después de agregar un ítem) la selección se pierde y esto lanza
   IndexError. Solución: guarda el producto seleccionado como estado
   (self.producto_sel_ventas / self.producto_sel_compras con nombre, precio y
   stock leídos de la BD, no del texto del Treeview) en al_seleccionar_producto,
   y usa ese estado en lugar de la selección del árbol. Si no hay producto
   seleccionado muestra el aviso existente. Conserva la selección visual tras
   recargar la tabla cuando el producto siga presente.

2. En editar_celda_carrito_ventas y editar_celda_carrito_compras, <Return> y
   <FocusOut> llaman ambos a guardar_edicion; tras destruir el Entry el segundo
   evento lanza TclError. Añade una bandera para que guardar_edicion solo se
   ejecute una vez y captura TclError. Ya que vas a tocar ambas funciones,
   unifícalas en una sola editar_celda_carrito(self, event, tipo) con tipo
   "ventas"/"compras", y haz lo mismo con quitar_del_carrito_*. El
   comportamiento debe quedar idéntico.

Además haz que parse_cantidad convierta ZeroDivisionError en ValueError.
Prueba manualmente: vende el mismo producto dos veces seguidas, edita una
celda con Enter y otra haciendo clic fuera. Commit: "fix: crash al agregar al
carrito y doble disparo al editar celdas".
```

### Prompt 1.2 – Integridad de datos en la BD

```
Corrige estos problemas de integridad en la clase BaseDatos de ventas.py sin
cambiar el esquema:

1. modificar_producto: si falla el UPDATE de productos por IntegrityError, el
   UPDATE previo sobre transacciones queda pendiente y lo confirma el siguiente
   commit. Envuelve ambas sentencias en una transacción explícita
   (BEGIN / COMMIT) y haz rollback ante cualquier excepción. Devuelve False y
   registra el error con logging.

2. Añade un método context-manager `transaccion()` en BaseDatos que haga
   BEGIN/COMMIT/ROLLBACK, y úsalo en Aplicacion.procesar_boleta y
   procesar_boleta_compra para que toda la boleta se guarde o no se guarde
   nada. Mueve el SQL directo que hoy hace la UI (self.db.cursor.execute en
   procesar_boleta_compra y en al_seleccionar_producto_editar) a métodos de
   BaseDatos: actualizar_precio_compra(nombre, precio) y
   obtener_producto(nombre).

3. eliminar_transaccion_y_reversar_stock: si el tipo es COBRO_DEUDA, vuelve a
   PENDIENTE el FIADO original (necesitarás guardar la relación: añade la
   columna transacciones.ref_id INTEGER vía migrar_tablas y rellénala en
   pagar_fiado). Si se intenta borrar un FIADO en estado PAGADO, no lo borres y
   devuelve un código que la UI muestre como "Primero elimina el cobro asociado".

4. pagar_fiado debe recibir encargada y fecha como parámetros (la UI pasa la
   encargada del sidebar y la fecha de hoy por defecto) y registrar cantidad 0
   en el COBRO_DEUDA, no 1.

5. Reemplaza todos los `except:` desnudos por excepciones concretas, y
   configura logging a un archivo app.log junto a la BD (nivel INFO, rotación
   de 1 MB x 3). respaldar_bd y restaurar_bd deben usar self.db.db_name y,
   tras restaurar, refrescar también actualizar_lista_encargadas y
   actualizar_combo_productos.

6. Cambia migrar_tablas para que consulte PRAGMA table_info antes de hacer
   ALTER TABLE en lugar de atrapar la excepción, y activa PRAGMA foreign_keys=ON
   y journal_mode=WAL al abrir la conexión.

Commit por cada punto. Al terminar, resume qué cambió en el comportamiento
visible para la usuaria.
```

---

## Fase 2 – Estructura de paquete y pruebas

### Prompt 2.1 – Separar en módulos sin cambiar comportamiento

```
Refactoriza ventas.py en un paquete sin cambiar ningún comportamiento visible.
Estructura objetivo:

agro/
  __init__.py
  config.py          # ruta de BD, nombre de app, versión, constantes (CLIENTE_GENERAL, ENCARGADA_DEFAULT)
  db/
    __init__.py
    conexion.py      # apertura, PRAGMAs, migraciones, context manager transaccion()
    productos.py     # repositorio de productos
    transacciones.py # boletas, fiados, cobros, borrado con reversión
    contactos.py     # clientes, proveedores, encargadas
  servicios/
    __init__.py
    carrito.py       # clase Carrito (agregar, quitar, editar línea, total) sin Tk
    ventas.py        # procesar venta/fiado/compra usando repositorios + transaccion()
    reportes.py      # consultas agregadas por periodo (por ahora puede seguir usando pandas)
    formato.py       # moneda(x) -> "S/. 12.50", cantidad(x) -> "1.5", parse_cantidad
  ui/
    __init__.py
    app.py           # clase Aplicacion: ventana, sidebar, navegación
    pantallas/
      ventas.py, compras.py, contactos.py, fiados.py, inventario.py, reportes.py
    dialogos.py      # calendario, popup de contacto, historial de cliente
main.py              # punto de entrada

Reglas:
- La UI nunca ejecuta SQL; solo llama a servicios/ y db/.
- Carrito es una clase pura: la lista de dicts actual pasa a objetos LineaCarrito
  (dataclass) con producto, precio_unit, cantidad, subtotal; ventas y compras
  usan la misma clase.
- Sustituye las 14 repeticiones de f"S/. {x:.2f}" por formato.moneda().
- El diccionario de meses queda en un solo lugar (formato.py).
- Mantén ventas.py en la raíz como un stub de 3 líneas que importe y ejecute
  main para no romper el hábito de la usuaria; márcalo como deprecado.

Hazlo en pasos: primero db/, después servicios/, después ui/. Ejecuta la app
después de cada paso. Commits: "refactor: extraer capa db", "refactor: extraer
servicios", "refactor: dividir UI en pantallas".
```

### Prompt 2.2 – Pruebas de la capa de datos y servicios

```
Añade pytest al proyecto (requirements-dev.txt) y escribe pruebas para
agro/db y agro/servicios usando SQLite en memoria (fixture que cree la
conexión con ":memory:" y aplique el esquema). No pruebes la UI.

Casos mínimos:
- productos: crear, duplicado devuelve False, renombrar actualiza historial,
  renombrar a nombre existente NO deja cambios parciales (verifica con rollback).
- carrito: agregar, editar cantidad recalcula subtotal, editar subtotal no toca
  precio_unit, quitar, total, parse_cantidad con "1/2", "0,5", "1/0", "abc".
- venta: procesar boleta de 3 líneas descuenta stock de las 3; si una línea
  falla ninguna se guarda; venta sobre stock negativo queda registrada con
  stock negativo (comportamiento actual, documéntalo).
- fiado: crear fiado, pagar_fiado crea COBRO_DEUDA con ref_id y marca PAGADO;
  eliminar el cobro vuelve el fiado a PENDIENTE; no se puede borrar un FIADO
  pagado.
- compra: suma stock y actualiza precio_compra.
- reportes: ingresos/gastos/por cobrar de un mes con datos sembrados.

Añade un workflow de GitHub Actions (.github/workflows/tests.yml) que ejecute
pytest en Ubuntu con Python 3.11 y 3.12, con `sudo apt-get install -y
python3-tk` para que los imports no fallen. Commit: "test: cobertura de db y
servicios".
```

---

## Fase 3 – Modelo de datos

### Prompt 3.1 – Boletas, pagos e IDs

```
Rediseña el esquema para resolver los problemas documentados en
PLAN_MEJORA.md §1.2 (puntos 4, 5, 8, 9, 10), con migración automática y
segura de la BD existente.

Nuevo esquema (SQLite):
- productos(id, nombre UNIQUE, unidad TEXT DEFAULT 'unid', precio_venta,
  precio_compra, stock REAL, stock_minimo REAL DEFAULT 5, activo INTEGER DEFAULT 1)
- clientes(id, nombre UNIQUE, documento, telefono, activo)
- proveedores(id, nombre UNIQUE, contacto, telefono, activo)
- encargadas(id, nombre UNIQUE, activo)
- boletas(id, fecha, hora, tipo CHECK IN ('VENTA','FIADO','ENTRADA'),
  cliente_id NULL, proveedor_id NULL, encargada_id, total REAL,
  estado CHECK IN ('PAGADO','PENDIENTE','PARCIAL'), notas TEXT)
- boleta_lineas(id, boleta_id FK, producto_id FK, cantidad, precio_unit,
  subtotal, stock_resultante)
- pagos(id, boleta_id FK, fecha, hora, monto, encargada_id, notas)
- Índices: boletas(fecha), boletas(tipo, estado), boletas(cliente_id),
  boleta_lineas(boleta_id), boleta_lineas(producto_id), pagos(boleta_id).
- Versionado con PRAGMA user_version.

Migración (agro/db/migraciones.py):
1. Antes de migrar copia la BD a backups/negocio_pre_migracion_YYYYMMDD_HHMMSS.db.
2. Reconstruye boletas agrupando transacciones por (fecha, hora, tipo, cliente,
   proveedor, encargada); cada fila pasa a boleta_lineas resolviendo
   producto_id por nombre (crea el producto como inactivo si ya no existe).
3. COBRO_DEUDA pasa a pagos vinculado por ref_id si existe, o por
   (cliente, monto, fecha más cercana) si no; registra en el log los que no se
   puedan vincular.
4. Marca "borrar producto" como desactivar (activo=0) para no perder historial.
5. Conserva la tabla transacciones renombrada a _legacy_transacciones durante
   dos versiones.

Actualiza repositorios, servicios y pruebas (escribe primero la prueba de
migración con una BD de ejemplo construida en el test con el esquema viejo).
La UI debe seguir funcionando con los mismos flujos. Commit por paso.
```

---

## Fase 4 – Rediseño de interfaz

Objetivo: reducir densidad, unificar componentes y acelerar el flujo de venta,
que es la pantalla que más se usa.

### Prompt 4.1 – Tokens de diseño y componentes base

```
Crea agro/ui/tema.py y agro/ui/componentes.py.

tema.py: tokens de diseño en un solo lugar, semánticos, no por color:
  COLOR = {primario, primario_hover, exito, exito_hover, alerta, alerta_hover,
           peligro, peligro_hover, neutro, fondo_tarjeta, texto_suave}
  ESPACIO = {xs:4, s:8, m:16, l:24, xl:32}
  FUENTE = {titulo:(size 20 bold), subtitulo:(16 bold), cuerpo:(13), pequeña:(11)}
  Función aplicar_estilo_treeview(modo) que sincronice el ttk.Treeview con el
  modo claro/oscuro de CustomTkinter (fondo, texto, encabezado, fila alterna,
  altura de fila 32).

componentes.py, todos como subclases de CTkFrame:
  - Tabla(parent, columnas: list[Columna], on_select, on_doble_clic):
    Treeview + scrollbar vertical + estilo, con métodos cargar(filas),
    limpiar(), seleccion() -> dict, seleccionar_por_valor(col, valor).
    Columna = dataclass(clave, titulo, ancho, alineacion, oculta=False).
  - Tarjeta(parent, titulo, valor, color) con set_valor().
  - Encabezado(parent, titulo, subtitulo=None, acciones=[botones]).
  - Campo(parent, etiqueta, ancho, tipo="texto|numero|cantidad") con get(),
    set(), limpiar() y validación visual (borde rojo) para número/cantidad.
  - Boton primario/secundario/peligro como funciones fábrica que usan tema.
  - Toast(parent).mostrar(texto, tipo) : aviso no bloqueante de 2.5 s en la
    esquina inferior derecha, para reemplazar los messagebox.showinfo de éxito.

Reemplaza todos los literales hex de agro/ui por tokens y todos los Treeview
por Tabla. Sin cambiar aún la disposición de las pantallas. Verifica que cada
pantalla siga abriendo. Commit: "ui: tokens de diseño y componentes base".
```

### Prompt 4.2 – Sidebar, navegación y pantalla Ajustes

```
Simplifica el sidebar de agro/ui/app.py:

- Solo navegación: Inicio, Ventas, Compras, Fiados, Inventario, Contactos,
  Reportes, Ajustes. El botón de la pantalla activa se resalta (fg_color
  primario; los demás transparentes con texto). Iconos: usa texto corto o
  quita los emojis; si mantienes iconos, cárgalos como CTkImage desde
  agro/ui/iconos/ (SVG a PNG 20px, blanco y gris).
- Abajo, una sola línea "Encargada: <nombre>" con un botón pequeño "Cambiar"
  que abre un selector; no botones de alta/baja.
- Nueva pantalla Ajustes con secciones verticales: Encargadas (lista +
  agregar + quitar), Respaldo (botones respaldar/restaurar + ruta de la BD +
  fecha del último respaldo), Apariencia (modo claro/oscuro/sistema, se guarda
  en un config.json junto a la BD), Acerca de (versión).
- Ventana: minsize(1024, 680), tamaño inicial recordado en config.json.
- Atajos: F1..F7 cambian de pantalla, Ctrl+B enfoca el buscador de la pantalla
  actual si existe, Esc limpia la selección.

Commit: "ui: sidebar limpio y pantalla Ajustes".
```

### Prompt 4.3 – Ventas y Compras unificadas

```
Sustituye agro/ui/pantallas/ventas.py y compras.py por una sola
PantallaMovimiento(modo="venta"|"compra") con esta disposición, usando los
componentes de 4.1:

Fila superior (Encabezado): título ("Nueva venta" / "Ingreso de mercadería"),
y a la derecha en una sola línea: fecha con botón calendario, y el combo
Cliente (venta) o Proveedor (compra) con botón "+" pequeño.

Columna izquierda (60%): buscador con foco automático al entrar a la pantalla
y Tabla de productos (Producto, Unidad, Precio, Stock; fila roja si stock <=
stock_minimo). Doble clic o Enter sobre un producto abre un mini-diálogo
"Cantidad" (con el precio editable en modo compra) y agrega al carrito.
Escribir en el buscador y pulsar Enter selecciona el primer resultado.

Columna derecha (40%): Tabla carrito (Producto, Cant, P.Unit, Subtotal) con
edición por doble clic; debajo, una línea de acciones pequeñas "Quitar" y
"Vaciar" alineadas a la derecha; total grande alineado a la derecha.
Al pie, UN solo botón primario de altura 48: en compra "Registrar ingreso";
en venta, un CTkSegmentedButton "Contado | Fiado" seguido del botón "Cobrar
S/. 123.40" (el monto en el botón). Si se elige Fiado y el cliente es PÚBLICO
GENERAL el botón se deshabilita y aparece la razón en texto pequeño.

Quita el texto permanente "(Doble clic en ...)" y ponlo como tooltip en el
encabezado del carrito. Reemplaza el messagebox de éxito por Toast, pero
mantén messagebox para confirmaciones de stock negativo.

Atajos dentro de la pantalla: Enter en cantidad agrega; Ctrl+Enter cobra;
Supr quita la línea seleccionada.

Ejecuta la app y prueba el flujo completo en ambos modos. Commit:
"ui: pantalla unificada de ventas y compras".
```

### Prompt 4.4 – Inventario y Contactos en maestro-detalle

```
Rediseña Inventario y Contactos con el mismo patrón maestro-detalle:

Inventario (agro/ui/pantallas/inventario.py):
- Encabezado con título, buscador y botón primario "Nuevo producto".
- Izquierda (65%): Tabla con Producto, Unidad, Stock, Mínimo, P. Venta,
  P. Compra, Margen % (calculado). Filas con stock <= mínimo en alerta.
  Checkbox "Mostrar inactivos".
- Derecha (35%): panel de detalle del producto seleccionado con Campos
  verticales (Nombre, Unidad como combo unid/kg/L/saco/bolsa, P. Venta,
  P. Compra, Stock, Stock mínimo), botón "Guardar cambios" y un enlace
  discreto "Desactivar producto" (peligro, con confirmación). Si no hay
  selección, el panel muestra "Selecciona un producto o crea uno nuevo".
- "Nuevo producto" abre un CTkToplevel modal con el mismo formulario vertical.
- Elimina el combo "Seleccione" y los dos formularios horizontales actuales.

Contactos (agro/ui/pantallas/contactos.py):
- Misma estructura: pestañas Clientes / Proveedores, cada una con Tabla a la
  izquierda y panel de detalle a la derecha (Nombre, Documento o Contacto,
  Teléfono, Notas). En Clientes el detalle muestra además "Deuda pendiente:
  S/. X" y un botón "Ver fiados" que navega a Fiados filtrado por ese cliente.
- Alta por botón "Nuevo cliente/proveedor" en el encabezado.

Commit: "ui: inventario y contactos en maestro-detalle".
```

### Prompt 4.5 – Fiados por cliente y pagos parciales

```
Rediseña agro/ui/pantallas/fiados.py sobre el modelo de la Fase 3:

- Vista principal: Tabla de clientes con deuda (Cliente, Nº boletas,
  Deuda total, Boleta más antigua, Días). Encabezado con buscador y tarjeta
  "Total por cobrar".
- Al seleccionar un cliente, panel derecho con sus boletas pendientes o
  parciales (Fecha, Nº líneas, Total, Pagado, Saldo) y debajo el historial
  de pagos.
- Botón primario "Registrar pago" abre diálogo: monto (por defecto el saldo
  de la boleta seleccionada, editable para pago parcial), fecha (hoy por
  defecto, con calendario), encargada (la actual), nota. Al guardar, el
  servicio crea el pago y actualiza el estado de la boleta a PARCIAL o PAGADO.
- Doble clic en una boleta muestra sus líneas.
- Quita el botón "Actualizar": la pantalla se recarga al entrar y después de
  cada acción.

Actualiza servicios y pruebas para pagos parciales (suma de pagos nunca puede
superar el total; estado se deriva de los pagos). Commit: "feat: fiados por
cliente con pagos parciales".
```

### Prompt 4.6 – Reportes en dos niveles e Inicio

```
Rediseña Reportes y crea una pantalla Inicio:

Reportes (agro/ui/pantallas/reportes.py):
- Barra de filtros compacta: selector de periodo tipo "◀ Septiembre 2026 ▶"
  con botón "Hoy", y un botón "Filtros" que despliega Día / Cliente /
  Proveedor / Tipo en un panel colapsable. La consulta se ejecuta al cambiar
  cualquier filtro, sin botón "Consultar".
- Dos pestañas (CTkTabview):
  "Resumen": 4 tarjetas (Ingresos, Compras, Margen bruto = ventas − costo
  de lo vendido usando precio_compra de cada línea, Por cobrar TOTAL con
  subtexto "de este periodo: S/. X"); debajo, tabla "Movimiento por
  producto" a lo ancho (Producto, Salidas, Entradas, Stock actual). Elimina
  el gráfico de matplotlib; si quieres una visual, dibuja una barra de
  proporción ingresos/gastos con CTkProgressBar.
  "Movimientos": tabla de boletas (Fecha, Hora, Tipo, Cliente/Proveedor,
  Encargada, Total, Estado) expandible a líneas; toolbar con "Exportar Excel"
  (exporta lo filtrado, con dos hojas: Boletas y Líneas, cabeceras en
  negrita, columnas ajustadas) y "Eliminar" en peligro con confirmación.

Inicio (agro/ui/pantallas/inicio.py), pantalla por defecto al abrir:
- Tarjetas: Ventas de hoy, Fiados pendientes (total), Productos bajo mínimo
  (cantidad).
- Lista "Productos por reponer" (stock <= mínimo) y "Fiados con más de 30
  días".
- Dos botones grandes: "Nueva venta" e "Ingreso de mercadería".

Commit: "ui: reportes en dos niveles y pantalla Inicio".
```

---

## Fase 5 – Optimización funcional

### Prompt 5.1 – Reportes en SQL y eliminar pandas del arranque

```
agro/servicios/reportes.py carga toda la tabla en un DataFrame de pandas en
cada consulta. Reescríbelo con consultas SQL agregadas parametrizadas por
periodo y filtros (GROUP BY producto, SUM por tipo, saldo de fiados desde
pagos). Devuelve dataclasses (ResumenPeriodo, MovimientoProducto,
BoletaResumen) que la UI consume directamente.

pandas y matplotlib deben dejar de importarse al arrancar. Para exportar a
Excel usa openpyxl directamente (agro/servicios/exportar.py). Si decides
mantener pandas solo para exportar, impórtalo dentro de la función.

Mide el tiempo de arranque antes y después (python -X importtime) y el
tiempo de la consulta mensual con una BD de prueba de 20 000 líneas generada
por un script en scripts/generar_datos_prueba.py. Reporta ambos números.
Actualiza pruebas y requirements.txt. Commit: "perf: reportes en SQL y
arranque sin pandas".
```

### Prompt 5.2 – Costo promedio, historial de precios y respaldo automático

```
Tres mejoras de negocio:

1. Costo promedio ponderado: al registrar una compra, en vez de sobrescribir
   productos.precio_compra con el último costo, calcula el promedio ponderado
   (stock_actual*costo_actual + cant*costo_nuevo) / (stock_actual+cant), y
   guarda el último costo en una nueva tabla precios_historial(producto_id,
   fecha, tipo 'compra'|'venta', precio). Muestra el historial en el panel de
   detalle de Inventario. El Margen bruto de Reportes usa el costo promedio
   vigente al momento de cada línea (guárdalo en boleta_lineas.costo_unit).

2. Respaldo automático: al cerrar la app, copia la BD a backups/ con nombre
   negocio_YYYYMMDD_HHMMSS.db y conserva solo los 10 más recientes. La
   pantalla Ajustes muestra la lista y permite restaurar uno con confirmación.

3. Boleta imprimible: botón "Imprimir" tras cobrar (y en Movimientos) que
   genera un PDF simple (reportlab) de 80 mm con nombre del negocio, fecha,
   cliente, líneas, total y estado, y lo abre con el visor del sistema.
   Nombre del negocio, RUC y dirección se configuran en Ajustes.

Pruebas para el cálculo de costo promedio y la rotación de respaldos.
Commit por mejora.
```

---

## Fase 6 – Empaquetado

### Prompt 6.1 – Ejecutable para Windows

```
Prepara la distribución:
- pyproject.toml con metadatos, versión única en agro/__init__.py.
- Spec de PyInstaller (agro.spec) en modo onedir con icono, sin consola, que
  incluya los assets de customtkinter y tkcalendar (usa collect_data_files).
- La BD y config.json deben vivir en %APPDATA%/AgroNegocio/ en Windows y en
  ~/.local/share/agro-negocio/ en Linux, no junto al ejecutable; si existe una
  negocio_final_stock.db junto al ejecutable, muévela allí la primera vez y
  avisa a la usuaria.
- Workflow .github/workflows/build.yml que, al crear un tag vX.Y.Z, construya
  en windows-latest y adjunte el zip al Release.
- CHANGELOG.md con lo hecho en las fases 1 a 5.
Commit: "build: empaquetado con PyInstaller y release automático".
```

---

## 3. Qué NO hacer

- No pasar a web/Electron/Flet "para modernizar": el problema es de
  organización y densidad, no de tecnología. CustomTkinter es suficiente.
- No añadir login/roles: es un negocio familiar; la encargada como selector
  simple es adecuada.
- No hacer las Fases 3 y 4 en la misma rama. La migración de datos debe
  poder probarse y revertirse sola.
- No borrar `_legacy_transacciones` hasta haber usado la app migrada al
  menos un mes.
