# Análisis de condiciones meteorológicas relacionadas con alertas de incendios en Tolima

Proyecto universitario de Ingeniería en Analítica de Datos. Pipeline en Python que toma las alertas de
incendios de Tolima (2026), las limpia, las transforma, las integra con información del IDEAM y genera un
dataset final con controles de calidad.

> **Estado honesto de la fuente meteorológica.** El conjunto de datos del IDEAM que se consultó al inicio
> (`57sv-p2fu`) solo tiene datos del 4/nov/2026, así que **no sirve** para enero–septiembre de 2026.
> El pipeline consulta los conjuntos de datos por variable del IDEAM (temperatura, precipitación, humedad,
> viento), **verifica primero si cubren el periodo** y solo integra lo que exista. Si no hay cobertura, lo dice
> en `outputs/reporte_cobertura_meteo.csv` y en el log, y **no afirma ninguna relación clima-alertas**.
> El brillo solar no se incluye porque no se encontró una fuente abierta verificada.

## Fuentes
| Fuente | Archivo / API | Qué contiene |
|---|---|---|
| Alertas de incendios | `data/raw/alertas_incendios.csv` | 41.195 alertas del país (Tolima: 4.197), 01/01/2026 al 19/09/2026 |
| Catálogo Nacional de Estaciones (CNE) | `data/raw/CNE_IDEAM.xls` | Lista de estaciones. **No son mediciones**; solo da contexto |
| Mediciones IDEAM | API de datos.gov.co (ver `src/config.py`) | Temperatura, precipitación, humedad relativa, velocidad del viento |

## Qué hace cada archivo
| Archivo | Función |
|---|---|
| `src/config.py` | Rutas, periodo, departamento, fuentes y reglas. Todo parámetro se cambia aquí |
| `src/carga_datos.py` | Lee CSV, Excel y la API del IDEAM; calcula huellas SHA-256 de los originales |
| `src/limpieza.py` | Diagnóstico de calidad, limpieza de espacios, filas vacías y duplicados |
| `src/transformaciones.py` | Tipos, normalización de municipios, nivel de amenaza, calendario, filtro, rangos válidos |
| `src/integracion.py` | Une alertas + catálogo (contexto) + mediciones por (municipio, fecha), sin rellenar vacíos |
| `src/validaciones.py` | 13 controles de calidad (conservación de registros, llaves, rangos, cobertura) |
| `src/analisis.py` | Tablas y gráficos de resultados |
| `src/pipeline.py` | Ejecuta todo en orden |
| `tests/` | 24 pruebas automáticas (`pytest`) |
| `notebooks/01_avance_original_colab.ipynb` | Tu notebook original, sin modificar |
| `docs/` | Informe técnico, registro de pruebas y guía paso a paso de VS Code y GitHub |

## Instalación (Windows, PowerShell)
Requiere Python 3.10 o superior (https://www.python.org/downloads/, marcar "Add python.exe to PATH").

```powershell
cd ruta\a\proyecto-incendios-tolima
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```
Si PowerShell bloquea la activación: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`.

## Ejecución
```powershell
python -m pytest -q                       # pruebas (deben pasar las 24)
python -m src.pipeline                    # pipeline completo, consulta la API del IDEAM (requiere internet)
python -m src.pipeline --meteo ninguna    # solo alertas y catálogo, sin internet
python -m src.pipeline --meteo archivos   # meteorología desde data/raw/meteo/*.csv (descargas manuales)
python -m src.pipeline --reutilizar-cache # no vuelve a descargar variables ya guardadas
```
Formato de `data/raw/meteo/<variable>.csv` (variables: `temperatura`, `precipitacion`, `humedad`, `viento`):
columnas `fecha, estacion, municipio, valor` (un valor por estación y día).

## Archivos que genera
| Ruta | Contenido |
|---|---|
| `data/processed/alertas_tolima_final.csv` | **Dataset final**: 1 fila por alerta + calendario + contexto + meteorología |
| `data/interim/alertas_tolima_limpias.csv` | Alertas de Tolima tras limpieza |
| `data/interim/filas_descartadas_sin_territorio.csv` | Filas descartadas (con justificación) |
| `data/interim/meteo_<variable>_estacion_dia.csv` | Mediciones descargadas, resumidas por estación y día |
| `outputs/log_ejecucion.txt` | Registro de consola de la ejecución |
| `outputs/resumen_ejecucion.json` | Resumen de la corrida |
| `outputs/diagnostico_calidad.csv` | Diagnóstico de calidad de las fuentes originales |
| `outputs/registro_transformaciones.csv` | Cada transformación: justificación y filas antes/después |
| `outputs/reporte_validaciones.csv` | Resultado de los 13 controles |
| `outputs/reporte_cobertura_meteo.csv` | Qué cobertura tiene cada variable meteorológica en el periodo |
| `outputs/municipios_meteo_sin_coincidencia.csv` | Municipios de las mediciones que no cruzan con las alertas |
| `outputs/manifiesto_datos_originales.csv` | Huellas SHA-256 de los originales |
| `outputs/contexto_estaciones_por_municipio.csv` | Estaciones atmosféricas del catálogo por municipio |
| `outputs/alertas_por_mes_y_nivel.csv`, `outputs/resumen_alertas_por_municipio.csv` | Tablas de resultados |
| `outputs/figuras/*.png` | Gráficos |

## Cómo comprobar que quedó bien
1. En la consola deben aparecer las validaciones `OK` (V13 puede salir `ADVERTENCIA` si no hay meteorología).
2. `outputs/reporte_validaciones.csv`: ninguna fila con `FALLA`.
3. `data/processed/alertas_tolima_final.csv`: 4.197 filas.
4. Revisa `outputs/reporte_cobertura_meteo.csv` para saber si hubo mediciones reales en el periodo.

Guía completa de VS Code y GitHub: `docs/guia_vscode_github.md`.
