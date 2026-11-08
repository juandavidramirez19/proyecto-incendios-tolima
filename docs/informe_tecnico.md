# Informe técnico: Análisis de condiciones meteorológicas relacionadas con alertas de incendios en Tolima

## 1. Introducción
Las alertas de incendios publicadas en Datos Abiertos Colombia indican, por municipio y fecha, un nivel de
amenaza (baja, moderada o alta). Este proyecto prepara un dataset reproducible que permita estudiar si las
condiciones meteorológicas registradas por el IDEAM se relacionan con esas alertas en el departamento del Tolima
durante 2026. El trabajo parte del notebook de Colab del avance 1 (`notebooks/01_avance_original_colab.ipynb`),
cuyos procedimientos válidos se conservaron y se reorganizaron en un pipeline en `src/`.

## 2. Objetivos
**General.** Construir un pipeline reproducible que integre alertas de incendios y variables meteorológicas del
IDEAM para Tolima (01/01/2026 a 19/09/2026).

**Específicos.**
1. Cargar y diagnosticar la calidad de fuentes heterogéneas (CSV, Excel, API).
2. Aplicar y justificar transformaciones sobre las alertas y el catálogo de estaciones.
3. Integrar las fuentes sin crear relaciones artificiales y sin perder registros.
4. Validar automáticamente el resultado y dejar evidencia verificable.
5. Verificar si existe información meteorológica real que cubra el periodo, y reportarlo con honestidad.

## 3. Fuentes y arquitectura
| Fuente | Formato | Rol |
|---|---|---|
| `alertas_incendios.csv` | CSV, separador `;` | Fuente principal: 41.195 filas, 7 columnas, todo el país |
| `CNE_IDEAM.xls` | Excel | Catálogo de estaciones (4.528 filas, 20 columnas). Solo contexto, no mediciones |
| API datos.gov.co (IDEAM) | JSON | Mediciones por variable: temperatura `sbwg-7ju4`, precipitación `s54a-sgyg`, humedad `uext-mhny`, viento `sgfv-3yp8` |

Flujo: `carga_datos` → diagnóstico (`limpieza`) → `transformaciones` → `integracion` → `validaciones` → `analisis`,
orquestado por `pipeline.py` y parametrizado en `config.py`. Los datos de `data/raw` no se modifican (se
comprueba con huellas SHA-256). Se descartó el conjunto `57sv-p2fu` del avance: solo contiene datos del
04/11/2026 (5.874 registros de Tolima) y 0 registros entre enero y septiembre. El brillo solar no aparece entre sus
sensores y no se encontró otra fuente abierta verificada, por lo que no se usa.

## 4. Diagnóstico de calidad
Resultados sobre los originales (`outputs/diagnostico_calidad.csv`):
- Alertas: 41.195 filas; 6 valores nulos, todos en **una sola fila** que solo tiene fecha (02/02/2026).
- Duplicados exactos: 0. Fechas no convertibles: 0. Periodo: 01/01/2026 a 19/09/2026.
- Tolima: 4.197 alertas, 48 nombres de municipio pero 47 municipios reales (PURIFICACIÓN y PURIFICACION comparten
  COD_DANE 73585).
- `OBJECTID` no es único (3.627 repeticiones dentro de Tolima); el par (COD_DANE, fecha) sí lo es.
- Nivel de amenaza en Tolima: alta 2.122, moderada 1.143, baja 932.
- Las alertas aparecen en 204 fechas con unas 20 alertas por día: un municipio sin alerta un día no significa que
  no tuviera riesgo.
- Catálogo CNE de Tolima: 291 estaciones; 201 miden variables atmosféricas y 90 son limnimétricas o limnigráficas
  (nivel de ríos). Coordenadas con coma decimal guardadas como texto. De las 201, 96 figuran como activas.

## 5. Transformaciones
Detalle con filas antes y después en `outputs/registro_transformaciones.csv`.

| Id | Transformación | Justificación |
|---|---|---|
| L1 | Separar filas sin territorio (1 fila) | No se pueden asignar a Tolima; se guardan aparte en `data/interim` |
| L2 | Eliminar duplicados exactos (0) | Control; no se encontraron |
| T1 | Convertir tipos | Fechas de texto a fecha; códigos de decimal a entero |
| T2 | Clave de municipio sin tildes y con alias | Evita cruces fallidos (972 nombres → 962 claves en todo el país; 48 → 47 en Tolima) |
| T3 | Nivel de amenaza numérico (1 a 3) | Permite comparar y promediar por nivel |
| T4 | Variables de calendario | Estudiar estacionalidad |
| T5 | Filtrar Tolima (se apartan 36.997 filas de otros departamentos) | Alcance del proyecto |
| T6 | Preparar catálogo (coordenadas, marca de estación atmosférica) | Contar solo estaciones que miden clima |
| T7 | Anular valores meteorológicos fuera de rango físico | Errores de sensor, sin borrar la fila |

## 6. Integración
1. **Catálogo CNE → contexto.** Se agrega a cada alerta cuántas estaciones atmosféricas (y activas) hay en su
   municipio (`cne_estaciones_atmosfericas`, `cne_estaciones_activas`). Esto **no es una variable meteorológica**.
   42 de 47 municipios tienen alguna estación atmosférica catalogada; Coello, Palocabildo, Falan, Casabianca e
   Icononzo no (361 alertas). Los nombres `Armero (Guayabal)` y `Mariquita` del catálogo se enlazan con ARMERO y
   SAN SEBASTIÁN DE MARIQUITA mediante alias documentados en `config.py`.
2. **Mediciones IDEAM → meteorología.** Cada variable se resume por estación y día (promedio; la precipitación se
   suma), luego se promedia por municipio y día, y se une a la alerta por (municipio, fecha). Si no existe una
   medición de una estación de ese municipio ese día, el valor queda **vacío**: no se interpola ni se asigna la
   estación de otro municipio. Cada valor trae el número de estaciones que lo respaldan.
   En la ejecución del 08/11/2026 la API entregó datos del IDEAM para las cuatro variables en todo el periodo
   (ver sección 8). Los nombres de municipio de las mediciones cruzaron todos con los de las alertas
   (`outputs/municipios_meteo_sin_coincidencia.csv` quedó vacío).

## 7. Validaciones
Trece controles automáticos (`outputs/reporte_validaciones.csv`). En la ejecución completa con la API del IDEAM
(08/11/2026, 474 s) los 13 salieron en OK:
- V02 conservación de registros: 41.195 = 1 vacía + 0 duplicados + 36.997 de otros departamentos + 4.197 de Tolima.
- V03: la integración mantiene 4.197 filas. V04: la llave (municipio, fecha) no tiene duplicados.
- V11 y V12: ningún dato meteorológico sin estación de respaldo y ningún valor fuera de rango físico.
- V13: 1.398 de 4.197 alertas (33,31 %) tienen al menos una variable meteorológica. Este control solo exige que
  haya alguna; **no** significa que la cobertura sea buena (ver sección 9).
Además hay 28 pruebas automáticas con `pytest` (todas pasan), incluidas pruebas de la consulta a la API con
respuestas simuladas, de los reintentos y de la descarga mes por mes.

## 8. Resultados y conclusiones
**Dataset final:** `data/processed/alertas_tolima_final.csv`, 4.197 filas y 25 columnas.

**Alertas por mes (Tolima):** ene 72, feb 29, mar 44, abr 45, may 468, jun 249, jul 1.264, ago 1.339, sep (hasta el
19) 687. Julio y agosto concentran el 62 % de las alertas. Las de nivel alta pasan de 2 en enero a 894 en agosto.

**Cobertura meteorológica (datos reales del IDEAM, datos.gov.co):**

| Variable | Conjunto | Registros crudos en el periodo | Días con datos (de 262) | Estaciones | Filas estación-día |
|---|---|---|---|---|---|
| Temperatura | `sbwg-7ju4` | 105.685 | 238 | 23 | 4.251 |
| Precipitación | `s54a-sgyg` | 1.108.706 | 238 | 43 | 7.134 |
| Humedad relativa | `uext-mhny` | 105.247 | 237 | 23 | 4.240 |
| Velocidad del viento | `sgfv-3yp8` | 620.789 | 237 | 23 | 4.161 |

Cobertura de las alertas con al menos una medición, por mes: ene 85 %, feb 79 %, mar 80 %, abr 47 %, may 35 %,
jun 36 %, jul 32 %, ago 24 %, sep 41 %. En total 1.398 de 4.197 (33,3 %).

**Comparación descriptiva por nivel de amenaza** (solo con las 1.398 alertas que tienen medición;
`outputs/meteo_promedio_por_nivel_amenaza.csv`):

| Nivel | Alertas con medición | Temperatura media (°C) | Precipitación diaria (mm) | Humedad (%) | Viento (m/s) |
|---|---|---|---|---|---|
| Baja | 395 | 24,38 | 1,36 | 74,32 | 1,46 |
| Moderada | 378 | 24,98 | 0,94 | 68,15 | 1,66 |
| Alta | 625 | 26,60 | 0,15 | 61,55 | 1,73 |

En las alertas que tienen medición, los niveles más altos coinciden con días más cálidos, más secos y con algo más
de viento. **Esto describe lo observado en esa parte de los datos; no demuestra una relación entre clima y alertas.**
No se realizó ninguna prueba estadística, no se controló el municipio, la altitud ni la época del año, y la
cobertura es desigual entre niveles (ver sección 9).

**Conclusiones.**
1. Se construyó un pipeline reproducible que integra alertas con mediciones reales del IDEAM sin perder registros.
2. Sí existe información meteorológica histórica del IDEAM para el periodo, pero solo cubre una parte de las alertas.
3. Los datos son compatibles con la idea de que las alertas altas ocurren en condiciones más secas y cálidas, pero
   confirmarlo exige un análisis adicional (por ejemplo, comparar dentro de cada municipio y mes).

## 9. Limitaciones
- **Cobertura por municipio.** 19 de los 47 municipios no tienen ninguna medición en estos conjuntos de datos:
  Alvarado, Carmen de Apicalá, Dolores, Cunday, Coyaima, Coello, Chaparral, Casabianca, Falan, Honda, Palocabildo,
  Ortega, Líbano, Flandes, Herveo, San Luis, Suárez, Villahermosa y Villarrica. Suman 1.625 alertas (38,7 %). En los
  28 municipios restantes (2.572 alertas) la cobertura es del 54,4 %, y es muy baja en Anzoátegui, Rovira, Prado y
  Murillo (entre 2 y 6 alertas con medición). Las conclusiones solo representan esos municipios.
- **Posible causa (no verificada).** De esos 19 municipios, 13 tienen estaciones atmosféricas activas en el
  catálogo CNE (por ejemplo Chaparral con 5). Los conjuntos usados contienen datos crudos de estaciones
  automáticas, por lo que es probable que esas estaciones sean convencionales y no aparezcan. Esto no se comprobó
  estación por estación.
- **Cobertura por mes y por nivel.** Baja de 85 % en enero a 24 % en agosto, justo cuando se concentran las alertas
  altas. Solo el 29 % de las alertas altas tiene medición (625 de 2.122) frente al 42 % de las bajas (395 de 932).
  Los grupos comparados no son igual de representativos.
- **Variables de confusión.** La temperatura depende de la altitud y del municipio; un nivel de alerta alto en un
  municipio cálido puede reflejar el lugar y no el clima de ese día. Tampoco se controló la época del año.
- **Precipitación.** Se suma desde lecturas cada 10 minutos; un día con lecturas faltantes queda subestimado. Los
  conjuntos tienen 43 estaciones de precipitación y 23 de las demás variables.
- Los datos de datos.gov.co son crudos (no validados por el IDEAM) y pueden tener retrasos o vacíos. La cobertura
  es de 237 a 238 de 262 días, así que hay días sin ninguna medición.
- El promedio de varias estaciones de un municipio no representa condiciones locales exactas (relieve, distancia).
- Las alertas son una variable de amenaza por municipio y día, no incendios confirmados.
- La fila descartada sin territorio (02/02/2026) podría pertenecer a Tolima; no hay forma de saberlo.
- El brillo solar no está disponible.
- En el reporte de cobertura aparecen 53 nombres de municipio en la precipitación, más que los 47 de Tolima. Todos
  cruzan con las alertas tras normalizar, así que se interpreta como variantes de escritura; no se revisó una a una.
