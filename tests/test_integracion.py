"""Pruebas de integración y validaciones con datos pequeños inventados SOLO para probar el código."""
import pandas as pd
import pytest

from src import integracion, validaciones


def alertas():
    return pd.DataFrame({
        "municipio_clave": ["IBAGUE", "IBAGUE", "COELLO"],
        "FECHA_EJECUCION": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-01"]),
    })


def meteo():
    return {"temperatura": pd.DataFrame({
        "fecha": pd.to_datetime(["2026-01-01", "2026-01-01"]),
        "estacion": ["A", "B"], "municipio": ["Ibagué", "Ibagué"],
        "valor": [20.0, 22.0], "n_lecturas": [24, 24]})}


def test_meteo_se_promedia_por_municipio_dia():
    md = integracion.agregar_meteo_municipio_dia(meteo())
    assert len(md) == 1
    assert md["temperatura_media_c"].iloc[0] == 21.0
    assert md["n_estaciones_temperatura"].iloc[0] == 2


def test_union_conserva_filas_y_no_rellena_dias_sin_medicion():
    md = integracion.agregar_meteo_municipio_dia(meteo())
    df = integracion.unir_meteo(alertas(), md)
    assert len(df) == 3
    assert list(df["tiene_meteo"]) == [True, False, False]  # 2 enero y Coello NO tienen medición
    assert pd.isna(df.loc[1, "temperatura_media_c"])


def test_union_sin_meteo_deja_estructura_fija():
    df = integracion.unir_meteo(alertas(), pd.DataFrame())
    assert len(df) == 3 and not df["tiene_meteo"].any()
    assert "precipitacion_total_mm" in df.columns


def test_municipio_de_meteo_sin_coincidencia_se_reporta():
    datos = meteo()
    datos["temperatura"].loc[0, "municipio"] = "Pueblo Inventado"
    sin = integracion.municipios_meteo_sin_coincidencia(datos, alertas())
    assert "PUEBLO INVENTADO" in set(sin["municipio_en_meteo"])


def test_contexto_cne_no_cambia_filas():
    resumen = pd.DataFrame({"municipio_clave": ["IBAGUE"], "cne_estaciones_atmosfericas": [5],
                            "cne_estaciones_activas": [2]})
    df = integracion.unir_contexto_cne(alertas(), resumen)
    assert len(df) == 3
    assert df.loc[2, "cne_estaciones_atmosfericas"] == 0  # Coello no tiene estaciones atmosféricas


def contexto_valido(n):
    return {"huellas_inicio": ["a"], "huellas_fin": ["a"], "filas_raw": n, "filas_vacias_descartadas": 0,
            "duplicados_eliminados": 0, "filas_otros_departamentos": 0, "filas_tolima_limpias": n,
            "fecha_inicio": "2026-01-01", "fecha_fin": "2026-01-02"}


def final_valido():
    df = alertas()
    df["DEPARTAMENTO"] = "TOLIMA"
    df["COD_DANE"] = [73001, 73001, 73200]
    df["nivel_amenaza"] = [1, 2, 3]
    df["municipio_clave"] = ["IBAGUE", "IBAGUE", "COELLO"]
    df["FECHA_EJECUCION"] = pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-02"])
    df = integracion.unir_meteo(df, pd.DataFrame())
    return df


def test_validaciones_pasan_con_datos_correctos():
    tabla = validaciones.ejecutar_validaciones(contexto_valido(3), final_valido())
    assert "FALLA" not in set(tabla["estado"])


def test_validacion_detecta_perdida_de_registros():
    ctx = contexto_valido(3)
    ctx["filas_raw"] = 10  # el crudo tenía más filas de las que se explican
    with pytest.raises(ValueError):
        validaciones.ejecutar_validaciones(ctx, final_valido())
