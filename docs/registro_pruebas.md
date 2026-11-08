# Registro de pruebas y errores

## Tabla de pruebas y errores
| Paso | Error | Causa probable | Corrección | Nueva prueba |
|---|---|---|---|---|
| Avance 1: integración | 183 alertas "sin coincidencia" de municipio | El cruce usaba solo `.upper()`; no unificaba tildes ni nombres distintos (`Armero (Guayabal)`, `Mariquita`) | Clave `municipio_clave` sin tildes y alias en `config.py` | `test_municipio_clave_unifica_escrituras`, `test_alias_de_municipios_del_catalogo` |
| Avance 1: integración | La "integración" solo agregaba un conteo de estaciones, sin mediciones | Se cruzó con el catálogo, que no contiene mediciones | El catálogo pasa a ser contexto; la meteorología se une solo con mediciones reales por municipio y fecha | `test_union_conserva_filas_y_no_rellena_dias_sin_medicion` |
| Avance 1: catálogo | Se contaban estaciones limnimétricas como estaciones de clima | No se filtraba por categoría | Marca `es_atmosferica` según categoría | `test_catalogo_marca_estaciones_atmosfericas` |
| Avance 1: fuente meteorológica | API `57sv-p2fu` devuelve 0 registros de enero a septiembre | Es una ventana reciente: solo tiene el 04/11/2026 | Consulta de cobertura previa y uso de los conjuntos por variable | `test_cobertura_sin_datos_en_periodo` |
| Avance 1: textos | Los comentarios dicen 221 filas × 15 columnas; las salidas muestran 19.848 × 19 | Se usaron dos endpoints distintos y no se actualizaron los textos | El pipeline usa una fuente local (Excel) y una API, documentadas | Diagnóstico `outputs/diagnostico_calidad.csv` |
| Avance 1: llaves | `OBJECTID` se repite 3.627 veces en Tolima | No es un identificador único | Llave de control (COD_DANE, fecha) | V04 en `validaciones.py` |
| Avance 1: municipios | 48 nombres vs 47 códigos DANE | `PURIFICACION` sin tilde (1 fila) | Normalización | V08 |
| Pipeline: carga del Excel | `ImportError: Import xlrd failed` al leer `.xls` | Falta la librería `xlrd` | Se agregó `xlrd` a `requirements.txt` | Ejecución del pipeline y `pytest` |
| Pipeline: validación V10 | El detalle mostraba `np.int64(1)` | Se imprimían tipos de NumPy | Conversión a `int` | Revisión de `reporte_validaciones.csv` |
| Pipeline: modo API sin internet | El aviso decía "no hay mediciones en el periodo" cuando fue error de red | Mensaje único para causas distintas | Mensaje según el estado (`ERROR_RED`, `SIN_DATOS_EN_PERIODO`, `COLUMNAS_DISTINTAS`) | `test_cobertura_error_de_red` |
| Pipeline: API | Posible rechazo del resumen (HTTP 400) si el valor viene como texto | Tipo de dato desconocido de antemano | Respaldo: descarga de filas y resumen local | `test_descarga_con_respaldo_si_la_api_rechaza_el_resumen` |
| Pipeline: precipitación (ejecución real 08/11/2026) | `ERROR_RED: Read timed out (read timeout=120)` | Conjunto muy grande (1.108.706 registros en el periodo); la consulta superó 120 s | Espera de 300 s, hasta 3 reintentos, descarga mes por mes y continuar si una variable falla | `test_reintenta_si_se_agota_el_tiempo`, `test_no_reintenta_en_error_400`, `test_ventanas_mensuales_cubren_el_periodo_sin_traslapes`, `test_descarga_junta_todos_los_meses`; nueva ejecución con la precipitación en OK |
| Pipeline: aviso de pandas | `Pandas4Warning: Series.dt.dayofweek is deprecated` | Atributo que desaparecerá en futuras versiones | Se usa `day_of_week` | `pytest` sin avisos |
| Archivos de salida | Las tildes se veían como `Ã³` al leer en PowerShell | Los CSV se guardaban en UTF-8 sin marca y PowerShell los interpretaba mal | Se guardan con `utf-8-sig`; para ver en consola: `Get-Content -Encoding UTF8` | Revisión de los CSV en Excel |
| Entorno: Git | `git` no se reconoce en la terminal | La terminal no tenía Git en el PATH | `$env:Path += ";C:\Program Files\Git\cmd"` o reiniciar el equipo | `git --version` |
| Cobertura meteorológica | 19 de 47 municipios sin ninguna medición (1.625 alertas) | Probablemente estaciones convencionales ausentes de los conjuntos de datos automáticos (no verificado) | Se documenta como limitación; no se interpola ni se asigna la estación de otro municipio | V11 (ningún dato sin estación de respaldo) |

## Pruebas ejecutadas
| Prueba | Resultado |
|---|---|
| `python -m pytest -q` | 28 pruebas pasadas |
| `python -m src.pipeline --reutilizar-cache` (08/11/2026) | Las 4 variables en OK; 4.197 filas finales; 13 validaciones en OK; V13: 1.398 de 4.197 alertas con meteorología (33,31 %); duración 474 s |
| Primera ejecución `python -m src.pipeline` (08/11/2026) | Temperatura, humedad y viento en OK; precipitación con `ERROR_RED` por tiempo agotado (corregido) |
| `outputs/municipios_meteo_sin_coincidencia.csv` | Vacío: todos los municipios de las mediciones cruzan con las alertas |

## Plantilla para nuevos errores
| Paso | Error | Causa probable | Corrección | Nueva prueba |
|---|---|---|---|---|
| | | | | |
