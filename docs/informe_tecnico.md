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

## 7. Validaciones
Trece controles automáticos (`outputs/reporte_validaciones.csv`). En la ejecución sin meteorología (`--meteo ninguna`):
V01 a V12 en OK; V13 (cobertura meteorológica) en ADVERTENCIA porque 0 de 4.197 alertas tienen mediciones.
Conservación de registros: 41.195 = 1 vacía + 0 duplicados + 36.997 de otros departamentos + 4.197 de Tolima.
La integración mantiene 4.197 filas. Además hay 24 pruebas con `pytest`, incluidas pruebas de la consulta a la API
con respuestas simuladas.

## 8. Resultados y conclusiones
- Dataset final `data/processed/alertas_tolima_final.csv`: 4.197 filas y 25 columnas.
- Alertas por mes (Tolima): ene 72, feb 29, mar 44, abr 45, may 468, jun 249, jul 1.264, ago 1.339, sep (hasta el 19) 687.
  Julio y agosto concentran el 62 % de las alertas. Las de nivel alta pasan de 2 en enero a 894 en agosto.
- **Relación con el clima: todavía no comprobada.** Los resultados meteorológicos dependen de ejecutar el pipeline
  con acceso a la API. La cobertura real (fechas mínimas y máximas, días y municipios con datos) queda en
  `outputs/reporte_cobertura_meteo.csv`. Hasta no verlo, no se afirma ninguna relación. Cuando exista cobertura, el
  proyecto entrega una tabla descriptiva (`meteo_promedio_por_nivel_amenaza.csv`); una diferencia entre promedios
  describe, no demuestra causalidad.
- **Pendiente de completar tras ejecutar:** sección de resultados meteorológicos y la cobertura observada.

## 9. Limitaciones
- No se verificó desde el entorno de desarrollo si los conjuntos del IDEAM cubren enero–septiembre de 2026 en
  Tolima; se verifica en cada ejecución.
- Los datos del IDEAM en datos.gov.co son crudos (no validados por el IDEAM) y pueden tener retrasos o vacíos.
- Solo hay estaciones en 42 de 47 municipios y muchas están suspendidas; los municipios sin estación no tendrán
  meteorología. Estimarla por vecindad requeriría una decisión metodológica adicional.
- Las alertas son una variable de amenaza por municipio y día, no incendios confirmados.
- La fila descartada sin territorio (02/02/2026) podría pertenecer a Tolima; no hay forma de saberlo.
- El brillo solar no está disponible.
- Los identificadores y columnas de la API se tomaron de documentación del IDEAM y no pudieron probarse en vivo
  durante el desarrollo; el pipeline avisa si las columnas no coinciden.
