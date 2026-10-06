# Registro de cambios – Planos de cerco perimétrico (Rev. C)

Proyecto: Complejo Logístico Industrial – Almacenamiento de Concentrado Mineral (Hartree – PIRS Río Seco).  
Fecha: 06/10/2026. Base: informe de revisión cruzada frente a ESP IG-01-260275-104-0000-CV-ESP-0007 (Rev. 0) y MEC IG-01-260275-104-0005-CV-MEC-0003 (Rev. B).

## Archivos entregados

| Archivo | Contenido | Layouts (espacios de impresión) |
|---|---|---|
| `PLANOS_CORREGIDOS_DXF_RevC.zip` | Los dos DXF corregidos comprimidos (27.8 MB; 194 MB descomprimidos). Se entregan en ZIP porque los DXF sueltos superan el límite de GitHub y el servidor Git LFS no fue accesible desde esta sesión | — |
| `IG-01-260275-104-0005-EST-DWG-0005_C.dxf` (dentro del ZIP) | Hoja 1 corregida (Rev. C) | `IG-01-260275-104-0005-EST-DWG-0005` (A1, 1:1, estilo `IG-100001-DA-0000-GA-FR-00005_A.ctb`) y `OBSOLETO-CV-DWG-0013-HOJA2-REV-A` (copia antigua de la hoja 2 que venía en el archivo; no plotear) |
| `IG-01-260275-104-0005-EST-DWG-0006_C.dxf` (dentro del ZIP) | Hoja 2 corregida (Rev. C) y hoja 3 nueva (Rev. A) | `IG-01-260275-104-0005-EST-DWG-0006` y `IG-01-260275-104-0005-EST-DWG-0007` (misma configuración de página y estilo de ploteo que la hoja 2) |
| `verificacion/*.png` | Render de cada layout tal como se plotea, para comprobar que los cambios se ven en los espacios de impresión | — |

Los DXF son AutoCAD 2018 (AC1032). Al abrirlos en AutoCAD ejecutar `AUDIT` y `REGEN`, revisar los layouts y guardar como DWG. Las cotas y directrices nuevas usan el estilo de cota `IG-DIMENSIONADO` y el estilo de directriz `Standard` existentes; las ventanas gráficas nuevas están en la capa `G-VIEWPORT` (no se plotea).

## Cambios aplicados

### HOJA 1

| Ítem del informe | Cambio |
|---|---|
| F1/F4 | Cajetín: 8 planos de referencia llenados, REV. C con fila de revisión, escala 'INDICADA' |
| F3/A1/E2/E4/E6 | Notas: zona UTM 18S; notas 6 (cerco Bulldog, módulo metálico no aplica), 7 (portón corredizo, protección anticorrosiva) y 8 (nomenclatura HSS) |
| F5/E4 | Especificaciones: fy en kg/cm2 y MPa; línea de protección anticorrosiva |
| A1 | Título del módulo metálico aclara que no aplica al cerco perimétrico |
| E2 | Nota de portón corredizo y motorizado bajo la elevación del portón vehicular |
| F7 | Layout renombrado a EST-DWG-0005; la copia antigua de la hoja 2 (Rev. A) queda marcada OBSOLETO |

### HOJA 2

| Ítem del informe | Cambio |
|---|---|
| F1/F4 | Cajetín: 8 planos de referencia, REV. C con fila de revisión, escala 'INDICADA' |
| F3/A4/C1/E2/E3/E4 | Notas: zona 18S; notas 5 (Bulldog, cotas referenciales), 6 (dado y hoja 3) y 7 (portón corredizo, cierre peatonal, anticorrosivo) |
| F5/E4 | Especificaciones: fy en kg/cm2 y MPa; línea de protección anticorrosiva |
| E1 | Título corregido: la elevación de 1.00 m es la puerta peatonal |
| A3/B3 | Título 'columna' pasa a 'poste prefabricado (referencial)' |
| A3 | Títulos del módulo nombran el sistema tipo Bulldog como la ESP |
| E5 | Panel de plancha galvanizada trapezoidal: espesor 5 mm corregido a 0.5 mm (a confirmar) |
| B3 | Armadura del poste marcada como referencial del proveedor |
| C1/C2 | Etiquetas 'ZAPATA' pasan a 'DADO DE CIMENTACIÓN'; etiquetas 'CIMIENTO CORRIDO' eliminadas |
| C1/C2/C3 | Modelo: zapatas de 0.40x0.40x0.80 y cimiento corrido reemplazados por dados de 0.80x0.80x1.00 m; postes empotrados 0.90 m |
| C1 | Ventanas gráficas de elevación y planta ampliadas para mostrar el dado completo |
| C1/C3 | Cotas 400/800/300/150 de la zapata reemplazadas por 800, 1000 y empotramiento 900 (a confirmar) |
| E2/D3 | Nota de portón corredizo y motorizado bajo la elevación del portón vehicular |
| F7 | Layout renombrado a EST-DWG-0006 |

### HOJA 3

| Ítem del informe | Cambio |
|---|---|
| nuevo | Layout nuevo IG-01-260275-104-0005-EST-DWG-0007 con la misma configuración de ploteo de la hoja 2 (34 parámetros copiados), cajetín Rev. A |
| C1/D2/D6 | Modelo: dibujados detalle de cimentación (sección y planta), esquema de escalonamiento y esquema de coronación de talud |
| C1/C5/D2/D6 | Hoja 3: 4 ventanas gráficas con sus títulos, cotas y directrices (dado, armadura, escalonamiento, distancia D) |
| B1/B2/C6 | Cuadros de longitudes de poste por pendiente y de tipos de poste (termina en y=238) |
| notas | Notas complementarias (8) y recuadro de pendientes de la revisión C (8) |

## Decisiones que quedan para Ingeniería (marcadas en la hoja 3, recuadro «Notas de revisión C»)

- **Modulación.** Planos y memoria usan 2.00 m entre postes; la ESP-0007 pide aprox. 3.00 m. No se cambió la geometría: hay que decidir y alinear los tres documentos.
- **Memoria MEC-0003.** Falta la verificación numérica de placas y postes, la altura máxima H max y la presión de viento definitiva. El cuadro de longitudes de poste de la hoja 3 queda condicionado a H max.
- **Coronación de taludes.** La distancia D y la fundación específica (sin empuje pasivo) requieren la verificación geotécnica; la hoja 3 fija la convención de medida de D, no su valor.
- **Empotramiento del poste.** Se dibujó 0.90 m dentro del dado y se acotó «900 (A CONFIRMAR)». La holgura de la placa inferior sigue pendiente del detalle aprobado del sistema.
- **Portón vehicular.** Debe pasar a corredizo y motorizado (Mecánica). La geometría batiente se mantiene como referencia con nota; falta el detalle de encuentro cerco–portón y la cimentación del portón.
- **Puerta peatonal.** El cierre superior hasta 3.00 m se indica por nota; falta el detalle.
- **Panel trapezoidal.** Se corrigió de 5 mm a 0.5 mm por ser el espesor comercial; confirmar.
- **Nomenclatura HSS.** La nota de la hoja 1 asume diámetro nominal en pulgadas por espesor de pared en mm; confirmar con el diseñador.
- **Código de la hoja 3.** `IG-01-260275-104-0005-EST-DWG-0007` es propuesto; confirmar con control documental.
- **Fechas y firmas.** La fila de revisión C lleva fecha 06/10/26, descripción «Emitido para revisión interna» y las mismas iniciales de las filas anteriores; ajustar al emitir.

## Observaciones sobre los archivos

- Los DXF originales pesan 118 y 124 MB porque el plano llave del cajetín inserta bloques exportados de Revit (edificios, camionetas, maquinaria) con cientos de miles de aristas. Se eliminaron solo los bloques sin ninguna referencia (89 y 93 bloques); los del plano llave se conservaron porque sí se usan. Para aligerar el archivo conviene reemplazar el plano llave por un bloque simplificado.
- El archivo 0005 contenía además una copia antigua de la hoja 2 (Rev. A, código CV-DWG-0013). Se dejó intacta y renombrada como `OBSOLETO-…` para que no se plotee por error.
- No se tocaron la geometría de las puertas, las ventanas gráficas de las puertas ni el bloque del cajetín; solo se modificaron valores de atributos.
