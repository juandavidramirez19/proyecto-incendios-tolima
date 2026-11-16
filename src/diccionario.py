"""
diccionario.py
--------------
Describe cada columna del dataset final: a qué grupo pertenece y qué contiene.
Se usa para (1) mostrar al final del pipeline qué hay en el archivo y (2) guardar
outputs/diccionario_dataset_final.csv.
"""
import pandas as pd

# columna: (grupo, descripción)
DICCIONARIO = {
    "OBJECTID": ("Alerta original", "Identificador original de la fuente. NO es único (se repite)."),
    "REGION": ("Alerta original", "Región natural del país."),
    "DEPARTAMENTO": ("Alerta original", "Departamento (siempre TOLIMA)."),
    "MUNICIPIO": ("Alerta original", "Municipio tal como viene en la fuente."),
    "COD_DANE": ("Alerta original", "Código DANE del municipio."),
    "TEXTO_AMENAZA": ("Alerta original", "Nivel de amenaza de incendio: baja, moderada o alta."),
    "FECHA_EJECUCION": ("Alerta original", "Fecha de la alerta (entre 2026-01-01 y 2026-09-19)."),
    "municipio_clave": ("Derivada de la alerta", "Municipio sin tildes y en mayúscula; es la llave para unir fuentes."),
    "nivel_amenaza": ("Derivada de la alerta", "Nivel numérico: 1 = baja, 2 = moderada, 3 = alta."),
    "anio": ("Calendario", "Año de la alerta."),
    "mes": ("Calendario", "Mes de la alerta (1 = enero)."),
    "dia": ("Calendario", "Día del mes."),
    "dia_semana": ("Calendario", "Día de la semana en texto (lunes a domingo)."),
    "semana_iso": ("Calendario", "Número de semana del año (norma ISO)."),
    "cne_estaciones_atmosfericas": ("Contexto del catálogo CNE (NO son mediciones)",
                                    "Estaciones del catálogo del IDEAM que miden variables atmosféricas en el municipio."),
    "cne_estaciones_activas": ("Contexto del catálogo CNE (NO son mediciones)",
                               "De esas estaciones, cuántas figuran como activas en el catálogo."),
    "temperatura_media_c": ("Mediciones del IDEAM", "Temperatura del aire (°C): promedio del día entre las estaciones del municipio."),
    "n_estaciones_temperatura": ("Mediciones del IDEAM", "Estaciones del municipio con dato de temperatura ese día (0 = sin medición)."),
    "precipitacion_total_mm": ("Mediciones del IDEAM", "Lluvia (mm): total del día por estación, promediado entre las estaciones del municipio."),
    "n_estaciones_precipitacion": ("Mediciones del IDEAM", "Estaciones del municipio con dato de precipitación ese día (0 = sin medición)."),
    "humedad_media_pct": ("Mediciones del IDEAM", "Humedad relativa del aire (%): promedio del día entre las estaciones del municipio."),
    "n_estaciones_humedad": ("Mediciones del IDEAM", "Estaciones del municipio con dato de humedad ese día (0 = sin medición)."),
    "viento_medio_ms": ("Mediciones del IDEAM", "Velocidad del viento (m/s): promedio del día entre las estaciones del municipio."),
    "n_estaciones_viento": ("Mediciones del IDEAM", "Estaciones del municipio con dato de viento ese día (0 = sin medición)."),
    "tiene_meteo": ("Indicador", "Verdadero si la alerta tiene al menos una variable medida ese día en su municipio."),
}


def construir_diccionario(final):
    """Tabla con una fila por columna del dataset final (en el mismo orden que el archivo)."""
    filas = []
    for col in final.columns:
        grupo, descripcion = DICCIONARIO.get(col, ("Sin clasificar", "Columna sin descripción: agregarla en src/diccionario.py"))
        filas.append({"columna": col, "grupo": grupo, "tipo": str(final[col].dtype),
                      "valores_no_nulos": int(final[col].notna().sum()), "descripcion": descripcion})
    return pd.DataFrame(filas)
