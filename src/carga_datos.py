"""
carga_datos.py
--------------
Lee las fuentes de datos:
  1. CSV de alertas de incendios (archivo local).
  2. Excel del Catálogo Nacional de Estaciones del IDEAM (CNE). OJO: es una LISTA de estaciones,
     no contiene mediciones.
  3. Mediciones meteorológicas del IDEAM (API de datos.gov.co), o archivos descargados a mano.

Los archivos originales de data/raw NUNCA se modifican; aquí solo se leen.
"""
import hashlib
import logging
import time

import pandas as pd
import requests

from . import config

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Archivos locales
# ---------------------------------------------------------------------------
def cargar_alertas(ruta=config.ARCHIVO_ALERTAS):
    """Lee el CSV de alertas (separador ';') y verifica que estén las 7 columnas."""
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró {ruta}. Copia alertas_incendios.csv en data/raw/")
    df = pd.read_csv(ruta, delimiter=config.SEPARADOR_ALERTAS)
    faltan = [c for c in config.COLUMNAS_ALERTAS_ESPERADAS if c not in df.columns]
    if faltan:
        raise ValueError(f"Faltan columnas en las alertas: {faltan}")
    log.info("Alertas cargadas: %d filas, %d columnas", *df.shape)
    return df


def cargar_cne(ruta=config.ARCHIVO_CNE):
    """Lee el Excel del catálogo de estaciones (.xls necesita la librería xlrd)."""
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró {ruta}. Copia CNE_IDEAM.xls en data/raw/")
    motor = "xlrd" if ruta.suffix.lower() == ".xls" else None
    df = pd.read_excel(ruta, engine=motor)
    faltan = [c for c in config.COLUMNAS_CNE_ESPERADAS if c not in df.columns]
    if faltan:
        raise ValueError(f"Faltan columnas en el catálogo CNE: {faltan}")
    log.info("Catálogo CNE cargado: %d filas, %d columnas", *df.shape)
    return df


def calcular_sha256(ruta):
    """Huella digital del archivo: si cambia un solo byte, cambia la huella."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()


def manifiesto_originales(rutas):
    """Tabla con tamaño y huella de cada archivo original (evidencia de que no se modificaron)."""
    filas = [{"archivo": r.name, "bytes": r.stat().st_size, "sha256": calcular_sha256(r)} for r in rutas]
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# API de datos abiertos del IDEAM (datos.gov.co, tecnología Socrata)
# ---------------------------------------------------------------------------
def _get_json(url, params):
    """
    Hace una consulta GET y devuelve el JSON.
    Si se agota el tiempo o el servidor responde con un error temporal (429, 500, 502, 503, 504),
    reintenta hasta config.INTENTOS veces esperando un poco más cada vez.
    Los demás errores (por ejemplo 400) se lanzan de inmediato.
    """
    temporales = (429, 500, 502, 503, 504)
    ultimo_error = None
    for intento in range(1, config.INTENTOS + 1):
        try:
            r = requests.get(url, params=params, timeout=config.TIMEOUT_SEGUNDOS)
            if r.status_code in temporales:
                raise requests.exceptions.HTTPError(f"HTTP {r.status_code}", response=r)
            r.raise_for_status()
            return r.json()
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as error:
            ultimo_error = error
        except requests.exceptions.HTTPError as error:
            if error.response is not None and error.response.status_code in temporales:
                ultimo_error = error
            else:
                raise
        if intento < config.INTENTOS:
            espera = config.ESPERA_REINTENTO * intento
            log.warning("Consulta fallida (%s). Intento %d de %d; se reintenta en %d s.",
                        str(ultimo_error)[:120], intento, config.INTENTOS, espera)
            time.sleep(espera)
    raise ultimo_error


def _paginar(url, params):
    """La API entrega máximo N filas por consulta; pedimos página por página hasta terminar."""
    filas, offset = [], 0
    for _ in range(config.MAX_PAGINAS):
        p = dict(params)
        p["$limit"] = config.LIMITE_POR_PAGINA
        p["$offset"] = offset
        lote = _get_json(url, p)
        filas.extend(lote)
        if len(lote) < config.LIMITE_POR_PAGINA:
            return filas
        offset += config.LIMITE_POR_PAGINA
    raise RuntimeError("Se alcanzó MAX_PAGINAS; aumenta el valor en config.py o reduce el periodo.")


def _filtro_where(departamento, inicio, fin):
    """Filtro SoQL: departamento y rango de fechas [inicio, fin] (fin incluido)."""
    c = config.COLUMNAS_IDEAM
    fin_excl = (pd.Timestamp(fin) + pd.Timedelta(days=1)).strftime("%Y-%m-%dT00:00:00")
    return (
        f"upper({c['departamento']}) = '{departamento.upper()}'"
        f" AND {c['fecha']} >= '{inicio}T00:00:00'"
        f" AND {c['fecha']} < '{fin_excl}'"
    )


def consultar_cobertura(variable, departamento=config.DEPARTAMENTO,
                        inicio=config.FECHA_INICIO, fin=config.FECHA_FIN):
    """
    Pregunta a la API cuántos registros hay en el periodo, SIN descargar todo.
    Devuelve un diccionario con el estado:
      OK | SIN_DATOS_EN_PERIODO | COLUMNAS_DISTINTAS | ERROR_RED
    """
    info = config.DATASETS_IDEAM[variable]
    url = config.URL_DATOS_ABIERTOS.format(id=info["id"])
    res = {"variable": variable, "dataset_id": info["id"], "total_registros": 0,
           "fecha_min": None, "fecha_max": None, "estado": "", "mensaje": ""}
    c = config.COLUMNAS_IDEAM
    try:
        # 1) Verificar que las columnas esperadas existan (con 1 fila de muestra)
        muestra = _get_json(url, {"$limit": 1})
        if muestra:
            faltan = [v for v in c.values() if v not in muestra[0]]
            if faltan:
                res["estado"] = "COLUMNAS_DISTINTAS"
                res["mensaje"] = f"Faltan {faltan}. Columnas reales: {list(muestra[0].keys())}"
                return res
        # 2) Contar registros y fechas extremas del periodo
        r = _get_json(url, {
            "$select": f"count(*) as total, min({c['fecha']}) as fmin, max({c['fecha']}) as fmax",
            "$where": _filtro_where(departamento, inicio, fin),
        })
        fila = r[0] if r else {}
        res["total_registros"] = int(fila.get("total", 0))
        res["fecha_min"], res["fecha_max"] = fila.get("fmin"), fila.get("fmax")
        res["estado"] = "OK" if res["total_registros"] > 0 else "SIN_DATOS_EN_PERIODO"
    except (requests.exceptions.RequestException, ValueError) as error:
        res["estado"] = "ERROR_RED"
        res["mensaje"] = str(error)[:300]
    return res


def _ventanas_mensuales(inicio, fin):
    """Divide el periodo en meses: [('2026-01-01','2026-01-31'), ..., ('2026-09-01','2026-09-19')]."""
    ventanas, actual, ultimo = [], pd.Timestamp(inicio), pd.Timestamp(fin)
    while actual <= ultimo:
        fin_mes = min(actual + pd.offsets.MonthEnd(0), ultimo)
        ventanas.append((actual.strftime("%Y-%m-%d"), fin_mes.strftime("%Y-%m-%d")))
        actual = fin_mes + pd.Timedelta(days=1)
    return ventanas


def descargar_estacion_dia(variable, departamento=config.DEPARTAMENTO,
                           inicio=config.FECHA_INICIO, fin=config.FECHA_FIN):
    """
    Descarga la variable mes por mes (cada consulta es más liviana y menos propensa a agotar el tiempo)
    y junta los resultados. Cada día pertenece a un solo mes, así que no se duplican filas.
    """
    partes = []
    for ini_m, fin_m in _ventanas_mensuales(inicio, fin):
        log.info("%s: descargando %s a %s", variable, ini_m, fin_m)
        partes.append(_descargar_ventana(variable, departamento, ini_m, fin_m))
    partes = [p for p in partes if not p.empty]
    if not partes:
        return _tipar_estacion_dia(None)
    return pd.concat(partes, ignore_index=True)


def _descargar_ventana(variable, departamento, inicio, fin):
    """
    Descarga una ventana de fechas y la resume por estación y día:
        fecha | estacion | municipio | valor | n_lecturas
    Primero intenta que la API haga el resumen (rápido). Si la API rechaza la consulta
    (por ejemplo, si el valor viene como texto), descarga las filas y resume en Python.
    """
    info = config.DATASETS_IDEAM[variable]
    url = config.URL_DATOS_ABIERTOS.format(id=info["id"])
    c = config.COLUMNAS_IDEAM
    where = _filtro_where(departamento, inicio, fin)
    dia = f"date_trunc_ymd({c['fecha']})"
    try:
        filas = _paginar(url, {
            "$select": (f"{dia} as fecha, {c['estacion']} as estacion, {c['municipio']} as municipio, "
                        f"{info['agregacion']}({c['valor']}) as valor, count(*) as n_lecturas"),
            "$where": where,
            "$group": f"{dia}, {c['estacion']}, {c['municipio']}",
            "$order": f"{dia}, {c['estacion']}, {c['municipio']}",
        })
        df = pd.DataFrame(filas)
        log.info("%s: resumen hecho por la API (%d filas estación-día)", variable, len(df))
    except requests.exceptions.HTTPError as error:
        log.warning("%s: la API rechazó el resumen (%s). Se descargan filas y se resume localmente.",
                    variable, error)
        filas = _paginar(url, {
            "$select": (f"{c['fecha']} as fecha_hora, {c['estacion']} as estacion, "
                        f"{c['municipio']} as municipio, {c['valor']} as valor"),
            "$where": where,
            "$order": f"{c['fecha']}, {c['estacion']}, {c['valor']}",
        })
        crudo = pd.DataFrame(filas)
        if crudo.empty:
            df = crudo
        else:
            crudo["fecha"] = pd.to_datetime(crudo["fecha_hora"], errors="coerce").dt.normalize()
            crudo["valor"] = pd.to_numeric(crudo["valor"], errors="coerce")
            df = (crudo.groupby(["fecha", "estacion", "municipio"], dropna=False)
                  .agg(valor=("valor", info["agregacion"]), n_lecturas=("valor", "count"))
                  .reset_index())
        log.info("%s: %d lecturas crudas -> %d filas estación-día", variable, len(crudo), len(df))
    return _tipar_estacion_dia(df)


def _tipar_estacion_dia(df):
    """Convierte tipos: fecha a datetime, valor y n_lecturas a número."""
    columnas = ["fecha", "estacion", "municipio", "valor", "n_lecturas"]
    if df is None or df.empty:
        return pd.DataFrame(columns=columnas)
    df = df.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.normalize()
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df["n_lecturas"] = pd.to_numeric(df["n_lecturas"], errors="coerce")
    df["estacion"] = df["estacion"].astype(str)
    return df[columnas]


def cargar_meteo_archivos(carpeta=config.DIR_RAW_METEO):
    """
    Alternativa: leer archivos que descargaste a mano (por ejemplo, de DHIME).
    Se espera un CSV por variable en data/raw/meteo/ con nombre temperatura.csv, precipitacion.csv,
    humedad.csv, viento.csv y columnas: fecha, estacion, municipio, valor (y opcional n_lecturas).
    """
    resultado = {}
    for variable in config.DATASETS_IDEAM:
        ruta = carpeta / f"{variable}.csv"
        if not ruta.exists():
            continue
        df = pd.read_csv(ruta)
        faltan = [c for c in ["fecha", "estacion", "municipio", "valor"] if c not in df.columns]
        if faltan:
            raise ValueError(f"{ruta.name}: faltan columnas {faltan}")
        if "n_lecturas" not in df.columns:
            df["n_lecturas"] = 1
        resultado[variable] = _tipar_estacion_dia(df)
        log.info("Meteo desde archivo %s: %d filas", ruta.name, len(df))
    return resultado
