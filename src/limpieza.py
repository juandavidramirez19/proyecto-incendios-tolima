"""
limpieza.py
-----------
Diagnóstico de calidad y limpieza básica. Cada paso informa cuántas filas afectó
para poder justificar que no se pierden registros sin razón.
"""
import unicodedata

import pandas as pd

from . import config


def normalizar_texto(valor):
    """'Purificación ' -> 'PURIFICACION': sin tildes, mayúsculas y sin espacios repetidos."""
    if pd.isna(valor):
        return pd.NA
    texto = unicodedata.normalize("NFKD", str(valor))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(texto.upper().split())


def diagnosticar(df, nombre):
    """Tabla de calidad: tipo, nulos y valores distintos de cada columna + duplicados."""
    tabla = pd.DataFrame({
        "fuente": nombre,
        "columna": df.columns,
        "tipo": [str(t) for t in df.dtypes],
        "nulos": df.isna().sum().values,
        "porcentaje_nulos": (df.isna().mean() * 100).round(2).values,
        "valores_distintos": df.nunique(dropna=True).values,
    })
    tabla["filas_totales"] = len(df)
    tabla["filas_duplicadas_exactas"] = int(df.duplicated().sum())
    return tabla


def quitar_espacios(df, columnas):
    """Elimina espacios al inicio y al final en columnas de texto."""
    df = df.copy()
    for col in columnas:
        df[col] = df[col].astype("string").str.strip()
    return df


def separar_filas_vacias(df):
    """
    Separa las filas que no tienen departamento, municipio ni código DANE.
    Esas filas no se pueden asignar a ningún territorio (en el CSV hay 1 con solo la fecha).
    Se devuelven aparte para que quede registro de qué se descartó.
    """
    sin_territorio = df[["DEPARTAMENTO", "MUNICIPIO", "COD_DANE"]].isna().all(axis=1)
    return df[~sin_territorio].copy(), df[sin_territorio].copy()


def eliminar_duplicados_exactos(df):
    """Elimina filas idénticas en TODAS las columnas. Devuelve (df, cantidad_eliminada)."""
    antes = len(df)
    df = df.drop_duplicates().copy()
    return df, antes - len(df)


def limpiar_cne(cne):
    """Limpieza del catálogo CNE: espacios en columnas de texto clave."""
    return quitar_espacios(cne, ["NOMBRE", "CATEGORIA", "ESTADO", "DEPARTAMENTO", "MUNICIPIO"])
