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
| Pipeline: modo API sin internet | El aviso decía "no hay mediciones en el periodo" cuando en realidad fue error de red | Mensaje único para causas distintas | Mensaje según el estado (`ERROR_RED`, `SIN_DATOS_EN_PERIODO`, `COLUMNAS_DISTINTAS`) | `test_cobertura_error_de_red` y ejecución con `--meteo api` sin acceso |
| Pipeline: API | Posible rechazo del resumen en la API (HTTP 400) si el valor viene como texto | Tipo de dato desconocido de antemano | Respaldo: descarga de filas y resumen local | `test_descarga_con_respaldo_si_la_api_rechaza_el_resumen` |

## Pruebas ejecutadas durante el desarrollo
| Prueba | Resultado |
|---|---|
| `python -m pytest -q` | 24 pruebas pasadas |
| `python -m src.pipeline --meteo ninguna` | 4.197 filas finales; V01 a V12 OK; V13 en ADVERTENCIA |
| `python -m src.pipeline --meteo api` (entorno sin acceso a datos.gov.co) | `ERROR_RED` registrado, el pipeline termina sin fallar y avisa claramente |
| `python -m src.pipeline --meteo api` en tu computador | **Pendiente: pega aquí el resultado de `outputs/reporte_cobertura_meteo.csv`** |

## Plantilla para nuevos errores
| Paso | Error | Causa probable | Corrección | Nueva prueba |
|---|---|---|---|---|
| | | | | |
