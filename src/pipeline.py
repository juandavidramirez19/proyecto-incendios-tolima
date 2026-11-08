"""
pipeline.py
-----------
Orquesta todo el proceso, desde la carga hasta el dataset final.

Ejecución (desde la carpeta del proyecto, con el entorno virtual activo):
    python -m src.pipeline                      # alertas + meteorología desde la API del IDEAM
    python -m src.pipeline --meteo ninguna      # solo alertas y catálogo (sin consultar la API)
    python -m src.pipeline --meteo archivos     # meteorología desde data/raw/meteo/*.csv
    python -m src.pipeline --meteo api --reutilizar-cache   # no vuelve a descargar lo ya guardado

Parámetros del periodo, departamento y fuentes: ver src/config.py
"""
import argparse
import json
import logging
import sys
from datetime import datetime

import pandas as pd

from . import analisis, carga_datos, config, integracion, limpieza, transformaciones, validaciones

log = logging.getLogger("pipeline")


def configurar_logging():
    config.DIR_OUTPUTS.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s", force=True,
        handlers=[logging.FileHandler(config.DIR_OUTPUTS / "log_ejecucion.txt", mode="w", encoding="utf-8"),
                  logging.StreamHandler(sys.stdout)])


def crear_carpetas():
    for d in [config.DIR_RAW, config.DIR_RAW_METEO, config.DIR_INTERIM, config.DIR_PROCESSED,
              config.DIR_OUTPUTS, config.DIR_FIGURAS]:
        d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Paso: alertas
# ---------------------------------------------------------------------------
def procesar_alertas(alertas_raw, registro, ctx):
    ctx["filas_raw"] = len(alertas_raw)

    df = limpieza.quitar_espacios(alertas_raw, ["REGION", "DEPARTAMENTO", "MUNICIPIO", "TEXTO_AMENAZA"])

    df, descartadas = limpieza.separar_filas_vacias(df)
    ctx["filas_vacias_descartadas"] = len(descartadas)
    descartadas.to_csv(config.DIR_INTERIM / "filas_descartadas_sin_territorio.csv", index=False, encoding=config.CODIFICACION_CSV)
    transformaciones.registrar(
        registro, "L1 separar filas sin territorio",
        "Filas sin departamento, municipio ni código DANE no se pueden asignar a Tolima; se guardan aparte.",
        len(alertas_raw), len(df), f"descartadas: {len(descartadas)} (ver data/interim/)")

    antes = len(df)
    df, n_dup = limpieza.eliminar_duplicados_exactos(df)
    ctx["duplicados_eliminados"] = n_dup
    transformaciones.registrar(
        registro, "L2 eliminar duplicados exactos",
        "Una fila idéntica en todas sus columnas es un registro repetido.", antes, len(df),
        f"duplicados eliminados: {n_dup}")

    df = transformaciones.convertir_tipos_alertas(df, registro)
    df = transformaciones.normalizar_municipios(df, registro)
    df = transformaciones.normalizar_amenaza(df, registro)
    df = transformaciones.agregar_calendario(df, registro)

    total_antes_filtro = len(df)
    tolima = transformaciones.filtrar_departamento(df, registro)
    ctx["filas_otros_departamentos"] = total_antes_filtro - len(tolima)
    ctx["filas_tolima_limpias"] = len(tolima)
    tolima.to_csv(config.DIR_INTERIM / "alertas_tolima_limpias.csv", index=False, encoding=config.CODIFICACION_CSV)
    return tolima.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Paso: meteorología
# ---------------------------------------------------------------------------
def obtener_meteo(modo, reutilizar, registro):
    """Devuelve (dict {variable: DataFrame estación-día}, tabla de cobertura)."""
    cobertura, datos = [], {}

    if modo == "ninguna":
        for v, info in config.DATASETS_IDEAM.items():
            cobertura.append({"variable": v, "dataset_id": info["id"], "estado": "NO_CONSULTADO",
                              "mensaje": "Se ejecutó con --meteo ninguna"})
    elif modo == "archivos":
        datos = carga_datos.cargar_meteo_archivos()
        for v, info in config.DATASETS_IDEAM.items():
            cobertura.append({"variable": v, "dataset_id": "archivo local",
                              "estado": "OK" if v in datos else "SIN_ARCHIVO",
                              "mensaje": "" if v in datos else f"No existe data/raw/meteo/{v}.csv"})
    else:  # api
        for v, info in config.DATASETS_IDEAM.items():
            cache = config.DIR_INTERIM / f"meteo_{v}_estacion_dia.csv"
            cob = carga_datos.consultar_cobertura(v)
            log.info("Cobertura API %-13s dataset %s -> %s | registros: %s | %s a %s %s",
                     v, info["id"], cob["estado"], cob["total_registros"], cob["fecha_min"],
                     cob["fecha_max"], cob["mensaje"])
            cobertura.append(cob)
            if cob["estado"] != "OK":
                continue
            if reutilizar and cache.exists():
                datos[v] = carga_datos._tipar_estacion_dia(pd.read_csv(cache))
                log.info("%s: se reutilizó el archivo guardado %s", v, cache.name)
            else:
                datos[v] = carga_datos.descargar_estacion_dia(v)
                datos[v].to_csv(cache, index=False, encoding=config.CODIFICACION_CSV)

    # Limpieza de rangos y estadísticas de cobertura local
    cob_df = pd.DataFrame(cobertura)
    dias_periodo = (pd.Timestamp(config.FECHA_FIN) - pd.Timestamp(config.FECHA_INICIO)).days + 1
    stats = {}
    for v in list(datos):
        datos[v] = transformaciones.marcar_fuera_de_rango(datos[v], v, registro)
        d = datos[v].dropna(subset=["valor"])
        stats[v] = {"dias_con_datos": d["fecha"].nunique(), "dias_periodo": dias_periodo,
                    "estaciones": d["estacion"].nunique(), "municipios": d["municipio"].nunique(),
                    "filas_estacion_dia": len(d)}
    for col in ["dias_con_datos", "dias_periodo", "estaciones", "municipios", "filas_estacion_dia"]:
        cob_df[col] = cob_df["variable"].map(lambda v: stats.get(v, {}).get(col, 0))
    return datos, cob_df


# ---------------------------------------------------------------------------
# Programa principal
# ---------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description="Pipeline alertas de incendios y meteorología - Tolima")
    parser.add_argument("--meteo", choices=["api", "archivos", "ninguna"], default="api",
                        help="de dónde salen las mediciones meteorológicas (por defecto: api del IDEAM)")
    parser.add_argument("--reutilizar-cache", action="store_true",
                        help="si ya se descargó una variable (data/interim), no volver a descargarla")
    args = parser.parse_args(argv)

    crear_carpetas()
    configurar_logging()
    inicio = datetime.now()
    log.info("=== INICIO DEL PIPELINE | departamento=%s | periodo=%s a %s | meteo=%s ===",
             config.DEPARTAMENTO, config.FECHA_INICIO, config.FECHA_FIN, args.meteo)

    registro, ctx = [], {}
    originales = [config.ARCHIVO_ALERTAS, config.ARCHIVO_CNE]

    # 1. Carga
    log.info("--- 1. Carga de fuentes heterogéneas (CSV y Excel) ---")
    manifiesto = carga_datos.manifiesto_originales(originales)
    ctx["huellas_inicio"] = manifiesto["sha256"].tolist()
    manifiesto.to_csv(config.DIR_OUTPUTS / "manifiesto_datos_originales.csv", index=False, encoding=config.CODIFICACION_CSV)
    alertas_raw = carga_datos.cargar_alertas()
    cne_raw = carga_datos.cargar_cne()

    # 2. Diagnóstico de calidad (sobre los datos originales)
    log.info("--- 2. Diagnóstico inicial de calidad ---")
    diag = pd.concat([limpieza.diagnosticar(alertas_raw, "alertas_incendios.csv"),
                      limpieza.diagnosticar(cne_raw, "CNE_IDEAM.xls")], ignore_index=True)
    diag.to_csv(config.DIR_OUTPUTS / "diagnostico_calidad.csv", index=False, encoding=config.CODIFICACION_CSV)
    log.info("Alertas: %d filas | nulos totales: %d", len(alertas_raw), int(alertas_raw.isna().sum().sum()))

    # 3. Limpieza y transformaciones de alertas
    log.info("--- 3. Limpieza y transformaciones de alertas ---")
    alertas = procesar_alertas(alertas_raw, registro, ctx)
    log.info("Alertas de %s listas: %d filas", config.DEPARTAMENTO, len(alertas))

    # 4. Catálogo de estaciones (contexto, NO mediciones)
    log.info("--- 4. Catálogo de estaciones (contexto) ---")
    cne = transformaciones.transformar_cne(limpieza.limpiar_cne(cne_raw), registro)
    resumen_cne = integracion.resumir_cne_por_municipio(cne)
    resumen_cne.to_csv(config.DIR_OUTPUTS / "contexto_estaciones_por_municipio.csv", index=False, encoding=config.CODIFICACION_CSV)
    final = integracion.unir_contexto_cne(alertas, resumen_cne)

    # 5. Meteorología
    log.info("--- 5. Mediciones meteorológicas del IDEAM ---")
    datos_meteo, cobertura = obtener_meteo(args.meteo, args.reutilizar_cache, registro)
    cobertura.to_csv(config.DIR_OUTPUTS / "reporte_cobertura_meteo.csv", index=False, encoding=config.CODIFICACION_CSV)
    meteo_md = integracion.agregar_meteo_municipio_dia(datos_meteo)
    sin_match = integracion.municipios_meteo_sin_coincidencia(datos_meteo, alertas)
    sin_match.to_csv(config.DIR_OUTPUTS / "municipios_meteo_sin_coincidencia.csv", index=False, encoding=config.CODIFICACION_CSV)
    if len(sin_match):
        log.warning("Hay %d municipios en la meteorología sin coincidencia en las alertas "
                    "(ver outputs/municipios_meteo_sin_coincidencia.csv; revisar ALIAS_MUNICIPIOS)", len(sin_match))
    final = integracion.unir_meteo(final, meteo_md)
    if not datos_meteo:
        estados = set(cobertura["estado"])
        if "ERROR_RED" in estados:
            causa = "No se pudo consultar la API (error de red o de acceso a datos.gov.co): revisa tu conexión y vuelve a ejecutar."
        elif "COLUMNAS_DISTINTAS" in estados:
            causa = "La API respondió con columnas distintas a las esperadas: ajusta COLUMNAS_IDEAM en config.py."
        elif "SIN_DATOS_EN_PERIODO" in estados:
            causa = "La API no tiene registros de Tolima entre %s y %s." % (config.FECHA_INICIO, config.FECHA_FIN)
        else:
            causa = "No se solicitó o no hay archivos meteorológicos."
        log.warning("SIN MEDICIONES METEOROLÓGICAS. %s El dataset final se genera con las columnas "
                    "meteorológicas vacías y NO se afirma ninguna relación clima-alertas.", causa)

    # 6. Validaciones
    log.info("--- 6. Validaciones ---")
    ctx["huellas_fin"] = carga_datos.manifiesto_originales(originales)["sha256"].tolist()
    ctx["fecha_inicio"], ctx["fecha_fin"] = config.FECHA_INICIO, config.FECHA_FIN
    tabla_val = validaciones.ejecutar_validaciones(ctx, final)
    tabla_val.to_csv(config.DIR_OUTPUTS / "reporte_validaciones.csv", index=False, encoding=config.CODIFICACION_CSV)
    for _, f in tabla_val.iterrows():
        log.info("%-12s %s | %s", f["estado"], f["validacion"], f["detalle"])

    # 7. Guardar resultados
    log.info("--- 7. Resultados ---")
    pd.DataFrame(registro).to_csv(config.DIR_OUTPUTS / "registro_transformaciones.csv", index=False, encoding=config.CODIFICACION_CSV)
    ruta_final = config.DIR_PROCESSED / "alertas_tolima_final.csv"
    final.sort_values(["FECHA_EJECUCION", "municipio_clave"]).to_csv(ruta_final, index=False, encoding=config.CODIFICACION_CSV)
    creados = analisis.generar_resultados(final)

    resumen = {
        "inicio": inicio.isoformat(timespec="seconds"),
        "duracion_segundos": round((datetime.now() - inicio).total_seconds(), 1),
        "modo_meteo": args.meteo, "periodo": [config.FECHA_INICIO, config.FECHA_FIN],
        "filas_alertas_originales": ctx["filas_raw"], "filas_tolima_final": len(final),
        "alertas_con_meteo": int(final["tiene_meteo"].sum()),
        "validaciones": tabla_val["estado"].value_counts().to_dict(),
        "dataset_final": str(ruta_final.relative_to(config.RAIZ)),
        "archivos_generados": [str(p.relative_to(config.RAIZ)) for p in creados],
    }
    (config.DIR_OUTPUTS / "resumen_ejecucion.json").write_text(
        json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Dataset final: %s (%d filas, %d columnas)", ruta_final.name, len(final), final.shape[1])
    log.info("=== FIN DEL PIPELINE (%.1f s) ===", resumen["duracion_segundos"])
    return final


if __name__ == "__main__":
    main()
