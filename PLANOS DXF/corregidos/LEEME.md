# Planos de cerco perimétrico corregidos (Rev. C) – cómo usar esta carpeta

## Contenido

| Archivo | Qué es |
|---|---|
| `PLANOS_CORREGIDOS_DXF_RevC.zip` | Los dos DXF corregidos: `IG-01-260275-104-0005-EST-DWG-0005_C.dxf` (hoja 1) e `IG-01-260275-104-0005-EST-DWG-0006_C.dxf` (hoja 2 corregida + hoja 3 nueva). |
| `REGISTRO_DE_CAMBIOS.md` | Lista de cada cambio aplicado, con el ítem del informe de revisión al que responde, y las decisiones que quedan pendientes. |
| `verificacion/*.png` | Render de cada espacio de impresión (layout) después de los cambios, más recortes de los detalles nuevos. |

Los DXF originales (Rev. B.1) siguen en la carpeta `PLANOS DXF/` como archivos Git LFS.

## Cómo abrir los planos

1. Descomprimir el ZIP (194 MB en total).
2. Abrir cada DXF en AutoCAD 2018 o posterior y ejecutar `AUDIT` (responder *Sí* a corregir) y `REGEN`.
3. Ir a los layouts. En el archivo 0005: `IG-01-260275-104-0005-EST-DWG-0005`. En el archivo 0006: `IG-01-260275-104-0005-EST-DWG-0006` y `IG-01-260275-104-0005-EST-DWG-0007` (hoja 3 nueva).
4. Guardar como DWG con el nombre del plano y la revisión.

Las configuraciones de página (A1, escala 1:1, estilo de ploteo `IG-100001-DA-0000-GA-FR-00005_A.ctb`, orientación, márgenes) se conservan en las hojas 1 y 2 y se copiaron a la hoja 3. Las ventanas gráficas nuevas están en la capa `G-VIEWPORT`, que no se plotea.

El archivo 0005 conserva un layout adicional renombrado `OBSOLETO-CV-DWG-0013-HOJA2-REV-A`: es la copia antigua de la hoja 2 que venía dentro del archivo original. No plotear; se puede borrar en AutoCAD cuando se confirme que no hace falta.

## Resumen de lo corregido

- **Hoja 1 (EST-DWG-0005, Rev. C):** cajetín completo (planos de referencia, revisión C, escala INDICADA), zona UTM 18S, notas 6 a 8 (sistema prefabricado tipo Bulldog, el módulo metálico no aplica al cerco perimétrico, portón corredizo, protección anticorrosiva, nomenclatura HSS), fy en kg/cm² y MPa, nota de portón corredizo y motorizado, layout renombrado al código del plano.
- **Hoja 2 (EST-DWG-0006, Rev. C):** cajetín completo, notas 5 a 7, título de la elevación de 1.00 m corregido (puerta peatonal), poste "columna" pasa a "poste prefabricado (referencial)", panel trapezoidal 0.5 mm (a confirmar), dado de cimentación 0.80 × 0.80 × 1.00 m con 8 Ø1/2" y estribos Ø3/8" @ 0.15 según la memoria MEC-0003 (planta, corte y cotas nuevas), postes llevados a la cota de fondo correcta, referencia a la hoja 3.
- **Hoja 3 (EST-DWG-0007, Rev. A, nueva):** detalle del dado (planta y corte 1:10), detalle del cerco sobre el dado (1:50) y detalle de escalonamiento en pendiente (1:50), con el cuadro de alturas requeridas por pendiente (5 % a 30 %) y el cuadro de distancias a la cresta del talud, notas complementarias y un recuadro con lo pendiente de definir.

## Decisiones que debe cerrar el proyectista

1. Modulación de postes: la ESP indica 3.00 m (5 placas de 0.60 m); el plano traía 2.00 m. Se adoptó 3.00 m; confirmar con el proveedor.
2. La memoria MEC-0003 debe actualizarse con la altura máxima del cerco escalonado y la carga de viento correspondiente.
3. Distancia D a la cresta del talud y la cimentación en esa condición (cuadro de la hoja 3, marcado A CONFIRMAR).
4. Empotramiento del poste 0.90 m: marcado A CONFIRMAR hasta que lo valide el proveedor.
5. Portón vehicular: detalle del portón corredizo o motorizado y del encuentro con el cerco prefabricado.
6. Cierre superior de la puerta peatonal.
7. Espesor del panel trapezoidal (0.5 mm) a confirmar con la ficha técnica.
8. Código definitivo de la hoja 3 (se propuso EST-DWG-0007) y fechas y firmas de la Rev. C en los tres cajetines.
