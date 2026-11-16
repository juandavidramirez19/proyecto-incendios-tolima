"""Comprueba que cada columna del dataset final tenga descripción."""
import pandas as pd

from src import diccionario

COLUMNAS_FINALES = [
    "OBJECTID", "REGION", "DEPARTAMENTO", "MUNICIPIO", "COD_DANE", "TEXTO_AMENAZA", "FECHA_EJECUCION",
    "municipio_clave", "nivel_amenaza", "anio", "mes", "dia", "dia_semana", "semana_iso",
    "cne_estaciones_atmosfericas", "cne_estaciones_activas",
    "temperatura_media_c", "n_estaciones_temperatura", "precipitacion_total_mm", "n_estaciones_precipitacion",
    "humedad_media_pct", "n_estaciones_humedad", "viento_medio_ms", "n_estaciones_viento", "tiene_meteo",
]


def test_todas_las_columnas_finales_tienen_descripcion():
    faltan = [c for c in COLUMNAS_FINALES if c not in diccionario.DICCIONARIO]
    assert faltan == []


def test_construir_diccionario_marca_columnas_desconocidas():
    df = pd.DataFrame({"mes": [1], "columna_nueva": [2]})
    dic = diccionario.construir_diccionario(df)
    assert list(dic["columna"]) == ["mes", "columna_nueva"]
    assert dic.loc[1, "grupo"] == "Sin clasificar"
