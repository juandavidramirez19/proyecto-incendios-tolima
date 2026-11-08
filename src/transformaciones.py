"""
transformaciones.py
-------------------
Transformaciones del pipeline. Cada una:
  - hace UNA cosa,
  - registra en `registro` qué hizo, por qué, y cuántas filas había antes y después.
Ese registro se guarda en outputs/registro_transformaciones.csv (evidencia para el informe).
"""
import pandas as pd

from . import config
from .limpieza import normalizar_texto

DIAS_SEMANA = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]


def registrar(registro, nombre, justificacion, antes, despues, detalle=""):
    registro.append({
        "transformacion": nombre, "justificacion": justificacion,
        "filas_antes": antes, "filas_despues": despues, "detalle": detalle,
    })


# T1 ---------------------------------------------------------------------------
def convertir_tipos_alertas(df, registro):
    """Fecha de texto a fecha real; OBJECTID y COD_DANE de decimal a entero."""
    df = df.copy()
    n = len(df)
    df["FECHA_EJECUCION"] = pd.to_datetime(
        df["FECHA_EJECUCION"], format=config.FORMATO_FECHA_ALERTAS, errors="coerce")
    invalidas = int(df["FECHA_EJECUCION"].isna().sum())
    df["OBJECTID"] = df["OBJECTID"].astype("Int64")
    df["COD_DANE"] = df["COD_DANE"].astype("Int64")
    registrar(registro, "T1 convertir tipos",
              "Las fechas venían como texto y los códigos como decimales (float); "
              "se necesitan fechas reales para agrupar por mes y códigos enteros para identificar municipios.",
              n, len(df), f"fechas no convertibles: {invalidas}")
    return df


# T2 ---------------------------------------------------------------------------
def normalizar_municipios(df, registro, columna="MUNICIPIO"):
    """Crea 'municipio_clave': sin tildes, mayúsculas y con alias unificados."""
    df = df.copy()
    n = len(df)
    clave = df[columna].map(normalizar_texto)
    df["municipio_clave"] = clave.replace(config.ALIAS_MUNICIPIOS)
    distintos_antes = df[columna].nunique()
    registrar(registro, "T2 normalizar municipios",
              "El mismo municipio aparece escrito de varias formas (p. ej. PURIFICACIÓN y PURIFICACION). "
              "Una clave sin tildes evita cruces fallidos entre fuentes.",
              n, len(df), f"nombres distintos antes: {distintos_antes}; claves distintas después: "
                          f"{df['municipio_clave'].nunique()}")
    return df


# T3 ---------------------------------------------------------------------------
def normalizar_amenaza(df, registro):
    """Texto de amenaza en minúscula consistente + nivel numérico (1 baja, 2 moderada, 3 alta)."""
    df = df.copy()
    n = len(df)
    texto = df["TEXTO_AMENAZA"].map(normalizar_texto)
    df["nivel_amenaza"] = texto.map(config.NIVELES_AMENAZA).astype("Int64")
    df["TEXTO_AMENAZA"] = texto.str.lower()
    sin_nivel = int(df["nivel_amenaza"].isna().sum())
    registrar(registro, "T3 codificar nivel de amenaza",
              "Un nivel numérico ordenado permite promediar y comparar condiciones por nivel de amenaza.",
              n, len(df), f"filas sin nivel reconocido: {sin_nivel}")
    return df


# T4 ---------------------------------------------------------------------------
def agregar_calendario(df, registro):
    """Año, mes, día, día de la semana y semana ISO a partir de la fecha."""
    df = df.copy()
    n = len(df)
    f = df["FECHA_EJECUCION"]
    df["anio"] = f.dt.year
    df["mes"] = f.dt.month
    df["dia"] = f.dt.day
    df["dia_semana"] = f.dt.day_of_week.map(lambda i: DIAS_SEMANA[int(i)] if pd.notna(i) else pd.NA)
    df["semana_iso"] = f.dt.isocalendar().week.astype("Int64")
    registrar(registro, "T4 variables de calendario",
              "Permiten analizar la estacionalidad de las alertas (mes, semana, día).", n, len(df))
    return df


# T5 ---------------------------------------------------------------------------
def filtrar_departamento(df, registro, departamento=config.DEPARTAMENTO):
    """Se queda solo con el departamento del proyecto. Las demás filas se cuentan, no se pierden de vista."""
    antes = len(df)
    dep = df["DEPARTAMENTO"].map(normalizar_texto)
    salida = df[dep == departamento.upper()].copy()
    registrar(registro, "T5 filtrar departamento",
              f"El proyecto analiza solo {departamento}; las alertas de otros departamentos quedan fuera del alcance.",
              antes, len(salida), f"filas de otros departamentos: {antes - len(salida)}")
    return salida


# T6 ---------------------------------------------------------------------------
def transformar_cne(cne, registro, departamento=config.DEPARTAMENTO):
    """Catálogo CNE: coordenadas con coma decimal a número, fechas, y marca de estación atmosférica."""
    df = cne.copy()
    n = len(df)
    for col in ["LATITUD", "LONGITUD"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    df["FECHA_INSTALACION"] = pd.to_datetime(df["FECHA_INSTALACION"], format="%d/%m/%Y", errors="coerce")
    df["municipio_clave"] = df["MUNICIPIO"].map(normalizar_texto).replace(config.ALIAS_MUNICIPIOS)
    df["categoria_norm"] = df["CATEGORIA"].map(normalizar_texto)
    df["es_atmosferica"] = df["categoria_norm"].isin(config.CATEGORIAS_CNE_ATMOSFERICAS)
    df["es_activa"] = df["ESTADO"].map(normalizar_texto) == "ACTIVA"
    df = df[df["DEPARTAMENTO"].map(normalizar_texto) == departamento.upper()].copy()
    registrar(registro, "T6 preparar catálogo de estaciones",
              "Las coordenadas usan coma decimal (texto). Además, solo las estaciones pluviométricas, "
              "climatológicas, sinópticas, etc. miden clima; las limnimétricas miden nivel de ríos.",
              n, len(df), f"estaciones atmosféricas: {int(df['es_atmosferica'].sum())}; "
                          f"no atmosféricas: {int((~df['es_atmosferica']).sum())}")
    return df


# T7 ---------------------------------------------------------------------------
def marcar_fuera_de_rango(df, variable, registro):
    """Valores físicamente imposibles se marcan como nulos (la fila NO se elimina)."""
    df = df.copy()
    minimo, maximo = config.RANGOS_VALIDOS[variable]
    fuera = (df["valor"] < minimo) | (df["valor"] > maximo)
    df.loc[fuera, "valor"] = pd.NA
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    registrar(registro, f"T7 rango válido ({variable})",
              "Un sensor puede enviar valores erróneos; se anulan valores fuera de rango físico sin borrar la fila.",
              len(df), len(df), f"valores anulados: {int(fuera.sum())} (rango {minimo} a {maximo})")
    return df
