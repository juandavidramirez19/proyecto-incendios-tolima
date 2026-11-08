"""
integracion.py
--------------
Une las fuentes SIN inventar relaciones:

  * Catálogo CNE  -> solo aporta CONTEXTO (cuántas estaciones hay en el municipio). No son mediciones.
  * Mediciones IDEAM -> se unen por (municipio, fecha) y SOLO si existe una medición real ese día
    en una estación de ese municipio. Si no existe, queda vacío (no se rellena ni se interpola).
"""
import pandas as pd

from . import config
from .limpieza import normalizar_texto

VARIABLES_SALIDA = {
    "temperatura": "temperatura_media_c",
    "precipitacion": "precipitacion_total_mm",
    "humedad": "humedad_media_pct",
    "viento": "viento_medio_ms",
}


def resumir_cne_por_municipio(cne_tolima):
    """Cuenta estaciones ATMOSFÉRICAS (y cuántas están activas) por municipio."""
    atm = cne_tolima[cne_tolima["es_atmosferica"]]
    resumen = (atm.groupby("municipio_clave")
               .agg(cne_estaciones_atmosfericas=("CODIGO", "nunique"),
                    cne_estaciones_activas=("es_activa", "sum"))
               .reset_index())
    resumen["cne_estaciones_activas"] = resumen["cne_estaciones_activas"].astype(int)
    return resumen


def unir_contexto_cne(alertas, resumen_cne):
    """Agrega el conteo de estaciones a cada alerta. Municipios sin estaciones quedan en 0."""
    n = len(alertas)
    df = alertas.merge(resumen_cne, on="municipio_clave", how="left", validate="many_to_one")
    for col in ["cne_estaciones_atmosfericas", "cne_estaciones_activas"]:
        df[col] = df[col].fillna(0).astype(int)
    if len(df) != n:
        raise ValueError(f"La unión con el catálogo cambió el número de filas: {n} -> {len(df)}")
    return df


def agregar_meteo_municipio_dia(meteo_estacion_dia):
    """
    Pasa de 'estación-día' a 'municipio-día' promediando las estaciones que midieron ese día.
    Entrada: dict {variable: DataFrame[fecha, estacion, municipio, valor, n_lecturas]}
    Salida: una fila por (municipio_clave, fecha) con una columna por variable y el número de estaciones.
    """
    partes = []
    for variable, df in meteo_estacion_dia.items():
        if df is None or df.empty:
            continue
        d = df.dropna(subset=["valor", "fecha"]).copy()
        d["municipio_clave"] = d["municipio"].map(normalizar_texto).replace(config.ALIAS_MUNICIPIOS)
        g = (d.groupby(["municipio_clave", "fecha"])
             .agg(**{VARIABLES_SALIDA[variable]: ("valor", "mean"),
                     f"n_estaciones_{variable}": ("estacion", "nunique")})
             .reset_index())
        partes.append(g.set_index(["municipio_clave", "fecha"]))
    if not partes:
        return pd.DataFrame(columns=["municipio_clave", "fecha"])
    return pd.concat(partes, axis=1).reset_index()


def unir_meteo(alertas, meteo_municipio_dia):
    """
    Une alertas con meteorología por (municipio_clave, fecha). Garantiza que no cambie el número de filas.
    Siempre deja las mismas columnas (con vacíos si no hay datos) para que el dataset tenga estructura fija.
    """
    n = len(alertas)
    if meteo_municipio_dia is None or meteo_municipio_dia.empty:
        df = alertas.copy()
    else:
        df = alertas.merge(meteo_municipio_dia, left_on=["municipio_clave", "FECHA_EJECUCION"],
                           right_on=["municipio_clave", "fecha"], how="left", validate="many_to_one")
        df = df.drop(columns=["fecha"])
    for variable, col in VARIABLES_SALIDA.items():
        if col not in df.columns:
            df[col] = pd.NA
        ncol = f"n_estaciones_{variable}"
        if ncol not in df.columns:
            df[ncol] = 0
        df[ncol] = df[ncol].fillna(0).astype(int)
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["tiene_meteo"] = df[list(VARIABLES_SALIDA.values())].notna().any(axis=1)
    if len(df) != n:
        raise ValueError(f"La unión con meteorología cambió el número de filas: {n} -> {len(df)}")
    return df


def municipios_meteo_sin_coincidencia(meteo_estacion_dia, alertas):
    """Municipios que aparecen en las mediciones pero no existen en las alertas (para revisar alias)."""
    claves_alertas = set(alertas["municipio_clave"].dropna())
    filas = []
    for variable, df in meteo_estacion_dia.items():
        if df is None or df.empty:
            continue
        claves = df["municipio"].map(normalizar_texto).replace(config.ALIAS_MUNICIPIOS)
        for m in sorted(set(claves.dropna()) - claves_alertas):
            filas.append({"variable": variable, "municipio_en_meteo": m})
    return pd.DataFrame(filas, columns=["variable", "municipio_en_meteo"])
