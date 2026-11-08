"""
config.py
---------
Aquí están TODOS los parámetros del proyecto en un solo lugar.
Si quieres cambiar una ruta, el departamento o una fuente, se hace aquí
y no dentro del resto del código.

Todas las rutas son relativas a la carpeta del proyecto (no hay rutas de tu computador).
"""
from pathlib import Path

# --- Rutas -----------------------------------------------------------------
# RAIZ = carpeta "proyecto-incendios-tolima" (un nivel arriba de src/)
RAIZ = Path(__file__).resolve().parent.parent
DIR_RAW = RAIZ / "data" / "raw"              # datos originales (NO se modifican)
DIR_RAW_METEO = DIR_RAW / "meteo"            # opcional: archivos meteorológicos descargados a mano
DIR_INTERIM = RAIZ / "data" / "interim"      # resultados intermedios
DIR_PROCESSED = RAIZ / "data" / "processed"  # dataset final
DIR_OUTPUTS = RAIZ / "outputs"               # reportes, logs, figuras
DIR_FIGURAS = DIR_OUTPUTS / "figuras"

ARCHIVO_ALERTAS = DIR_RAW / "alertas_incendios.csv"
ARCHIVO_CNE = DIR_RAW / "CNE_IDEAM.xls"      # Catálogo Nacional de Estaciones (NO son mediciones)

# --- Lectura de las alertas ---------------------------------------------------
SEPARADOR_ALERTAS = ";"
FORMATO_FECHA_ALERTAS = "%d/%m/%Y"           # ejemplo: 1/01/2026
COLUMNAS_ALERTAS_ESPERADAS = [
    "OBJECTID", "REGION", "DEPARTAMENTO", "MUNICIPIO",
    "COD_DANE", "TEXTO_AMENAZA", "FECHA_EJECUCION",
]
COLUMNAS_CNE_ESPERADAS = [
    "CODIGO", "NOMBRE", "CATEGORIA", "ESTADO",
    "LATITUD", "LONGITUD", "DEPARTAMENTO", "MUNICIPIO",
]

# --- Alcance del proyecto (NO cambiar sin consultar al profesor) --------------
DEPARTAMENTO = "TOLIMA"
FECHA_INICIO = "2026-01-01"
FECHA_FIN = "2026-09-19"

# --- Reglas de transformación -------------------------------------------------
NIVELES_AMENAZA = {"BAJA": 1, "MODERADA": 2, "ALTA": 3}

# Categorías del catálogo que SÍ miden variables atmosféricas (ya sin tildes y en mayúscula).
# Las limnimétricas/limnigráficas miden nivel de ríos y por eso no se cuentan.
CATEGORIAS_CNE_ATMOSFERICAS = [
    "PLUVIOMETRICA", "PLUVIOGRAFICA",
    "CLIMATOLOGICA ORDINARIA", "CLIMATOLOGICA PRINCIPAL",
    "METEOROLOGICA ESPECIAL", "SINOPTICA PRINCIPAL", "SINOPTICA SECUNDARIA",
    "AGROMETEOROLOGICA",
]

# Nombres distintos para el mismo municipio entre fuentes (detectado en el catálogo CNE).
# Clave y valor van sin tildes y en mayúscula.
ALIAS_MUNICIPIOS = {
    "ARMERO (GUAYABAL)": "ARMERO",
    "MARIQUITA": "SAN SEBASTIAN DE MARIQUITA",
}

# --- Fuente meteorológica: API de datos abiertos del IDEAM (datos.gov.co) -------
# Un conjunto de datos por variable. Los identificadores salen de la documentación del IDEAM
# y del portal datos.gov.co. Si alguno cambia, solo hay que actualizarlo aquí.
URL_DATOS_ABIERTOS = "https://www.datos.gov.co/resource/{id}.json"
DATASETS_IDEAM = {
    # variable: id del dataset, cómo se resume un día en una estación, unidad
    "temperatura":   {"id": "sbwg-7ju4", "agregacion": "avg", "unidad": "C"},
    "precipitacion": {"id": "s54a-sgyg", "agregacion": "sum", "unidad": "mm"},
    "humedad":       {"id": "uext-mhny", "agregacion": "avg", "unidad": "%"},
    "viento":        {"id": "sgfv-3yp8", "agregacion": "avg", "unidad": "m/s"},
}
# Nombres de columnas en los datasets del IDEAM (el pipeline verifica que existan).
COLUMNAS_IDEAM = {
    "fecha": "fechaobservacion",
    "valor": "valorobservado",
    "estacion": "codigoestacion",
    "departamento": "departamento",
    "municipio": "municipio",
}
LIMITE_POR_PAGINA = 50000
MAX_PAGINAS = 200
TIMEOUT_SEGUNDOS = 300      # espera máxima por consulta (la precipitación es un conjunto muy grande)
INTENTOS = 3                # cuántas veces se reintenta si hay tiempo agotado o error temporal
ESPERA_REINTENTO = 10       # segundos de espera antes de reintentar (se multiplica por el número de intento)
CODIFICACION_CSV = "utf-8-sig"  # con esta codificación Excel muestra bien las tildes

# Rangos físicos razonables; valores fuera de rango se marcan como nulos (no se borra la fila).
RANGOS_VALIDOS = {
    "temperatura": (-10, 45),    # grados C
    "precipitacion": (0, 500),   # mm por día
    "humedad": (0, 100),         # %
    "viento": (0, 40),           # m/s
}
# Brillo solar: no se encontró un dataset abierto del IDEAM verificado; no se usa (ver informe).
