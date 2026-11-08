"""Pruebas de limpieza y transformaciones con datos pequeños inventados SOLO para probar el código."""
import pandas as pd

from src import config, limpieza, transformaciones


def alertas_ejemplo():
    return pd.DataFrame({
        "OBJECTID": [1.0, 2.0, 3.0, None],
        "REGION": ["ANDINA", "ANDINA", "ANDINA", None],
        "DEPARTAMENTO": ["TOLIMA", "TOLIMA", "HUILA", None],
        "MUNICIPIO": ["PURIFICACIÓN", "PURIFICACION", "NEIVA", None],
        "COD_DANE": [73585.0, 73585.0, 41001.0, None],
        "TEXTO_AMENAZA": ["ALTA", "baja ", "MODERADA", None],
        "FECHA_EJECUCION": ["1/01/2026", "2/01/2026", "3/01/2026", "2/02/2026"],
    })


def test_normalizar_texto_quita_tildes_y_espacios():
    assert limpieza.normalizar_texto("  Purificación ") == "PURIFICACION"
    assert pd.isna(limpieza.normalizar_texto(None))


def test_filas_vacias_se_separan_no_se_pierden():
    df = alertas_ejemplo()
    limpio, descartadas = limpieza.separar_filas_vacias(df)
    assert len(descartadas) == 1
    assert len(limpio) + len(descartadas) == len(df)


def test_tipos_fecha_y_codigos():
    reg = []
    df = transformaciones.convertir_tipos_alertas(alertas_ejemplo(), reg)
    assert str(df["FECHA_EJECUCION"].dtype).startswith("datetime64")
    assert df["COD_DANE"].dropna().iloc[0] == 73585
    assert len(reg) == 1


def test_municipio_clave_unifica_escrituras():
    reg = []
    df = transformaciones.normalizar_municipios(alertas_ejemplo().dropna(subset=["MUNICIPIO"]), reg)
    assert df["municipio_clave"].iloc[0] == df["municipio_clave"].iloc[1] == "PURIFICACION"


def test_alias_de_municipios_del_catalogo():
    reg = []
    df = pd.DataFrame({"MUNICIPIO": ["Mariquita", "Armero (Guayabal)"]})
    df = transformaciones.normalizar_municipios(df, reg)
    assert list(df["municipio_clave"]) == ["SAN SEBASTIAN DE MARIQUITA", "ARMERO"]


def test_nivel_de_amenaza():
    reg = []
    df = transformaciones.normalizar_amenaza(alertas_ejemplo().dropna(subset=["TEXTO_AMENAZA"]), reg)
    assert list(df["nivel_amenaza"]) == [3, 1, 2]
    assert list(df["TEXTO_AMENAZA"]) == ["alta", "baja", "moderada"]


def test_calendario():
    reg = []
    df = transformaciones.convertir_tipos_alertas(alertas_ejemplo(), reg)
    df = transformaciones.agregar_calendario(df, reg)
    assert df["mes"].iloc[0] == 1 and df["dia_semana"].iloc[0] == "jueves"  # 1 enero 2026 fue jueves


def test_filtro_departamento_cuenta_lo_que_saca():
    reg = []
    df = alertas_ejemplo().dropna(subset=["DEPARTAMENTO"])
    salida = transformaciones.filtrar_departamento(df, reg)
    assert len(salida) == 2
    assert "filas de otros departamentos: 1" in reg[0]["detalle"]


def test_rango_valido_anula_sin_borrar_filas():
    reg = []
    df = pd.DataFrame({"valor": [20.0, 999.0, 10.0]})
    salida = transformaciones.marcar_fuera_de_rango(df, "temperatura", reg)
    assert len(salida) == 3 and salida["valor"].isna().sum() == 1


def test_catalogo_marca_estaciones_atmosfericas():
    reg = []
    cne = pd.DataFrame({
        "CODIGO": [1, 2], "CATEGORIA": ["Pluviométrica", "Limnimétrica"], "ESTADO": ["Activa", "Suspendida"],
        "DEPARTAMENTO": ["Tolima", "Tolima"], "MUNICIPIO": ["Ibagué", "Ibagué"],
        "LATITUD": ["4,43", "4,6"], "LONGITUD": ["-75,23", "-75,35"],
        "FECHA_INSTALACION": ["15/01/1943", "15/01/1950"],
    })
    out = transformaciones.transformar_cne(cne, reg)
    assert list(out["es_atmosferica"]) == [True, False]
    assert out["LATITUD"].iloc[0] == 4.43
