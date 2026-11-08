"""Pruebas de la consulta a la API del IDEAM SIN internet: se simulan las respuestas."""
import pandas as pd
import requests

from src import carga_datos, config


def test_paginacion_junta_todas_las_paginas(monkeypatch):
    monkeypatch.setattr(config, "LIMITE_POR_PAGINA", 2)
    paginas = {0: [{"a": 1}, {"a": 2}], 2: [{"a": 3}]}
    monkeypatch.setattr(carga_datos, "_get_json", lambda url, p: paginas[p["$offset"]])
    assert len(carga_datos._paginar("url", {})) == 3


def test_cobertura_ok(monkeypatch):
    columnas = {v: "x" for v in config.COLUMNAS_IDEAM.values()}

    def falso(url, params):
        if params.get("$limit") == 1:
            return [columnas]
        return [{"total": "10", "fmin": "2026-01-01T00:00:00", "fmax": "2026-09-19T00:00:00"}]
    monkeypatch.setattr(carga_datos, "_get_json", falso)
    cob = carga_datos.consultar_cobertura("temperatura")
    assert cob["estado"] == "OK" and cob["total_registros"] == 10


def test_cobertura_sin_datos_en_periodo(monkeypatch):
    columnas = {v: "x" for v in config.COLUMNAS_IDEAM.values()}
    monkeypatch.setattr(carga_datos, "_get_json",
                        lambda url, p: [columnas] if p.get("$limit") == 1 else [{"total": "0"}])
    assert carga_datos.consultar_cobertura("temperatura")["estado"] == "SIN_DATOS_EN_PERIODO"


def test_cobertura_columnas_distintas(monkeypatch):
    monkeypatch.setattr(carga_datos, "_get_json", lambda url, p: [{"otra_columna": 1}])
    assert carga_datos.consultar_cobertura("temperatura")["estado"] == "COLUMNAS_DISTINTAS"


def test_cobertura_error_de_red(monkeypatch):
    def falla(url, p):
        raise requests.exceptions.ConnectionError("sin internet")
    monkeypatch.setattr(carga_datos, "_get_json", falla)
    assert carga_datos.consultar_cobertura("temperatura")["estado"] == "ERROR_RED"


def test_descarga_resumida_por_la_api(monkeypatch):
    filas = [{"fecha": "2026-01-01T00:00:00.000", "estacion": "1", "municipio": "Ibagué",
              "valor": "20.5", "n_lecturas": "24"}]
    monkeypatch.setattr(carga_datos, "_get_json", lambda url, p: filas)
    df = carga_datos.descargar_estacion_dia("temperatura", inicio="2026-01-01", fin="2026-01-31")
    assert df["valor"].iloc[0] == 20.5 and df["fecha"].iloc[0] == pd.Timestamp("2026-01-01")


def test_descarga_con_respaldo_si_la_api_rechaza_el_resumen(monkeypatch):
    crudo = [{"fecha_hora": "2026-01-01T00:10:00", "estacion": "1", "municipio": "Ibagué", "valor": "1.0"},
             {"fecha_hora": "2026-01-01T00:20:00", "estacion": "1", "municipio": "Ibagué", "valor": "2.0"}]

    def falso(url, p):
        if "$group" in p:
            r = requests.Response()
            r.status_code = 400
            raise requests.exceptions.HTTPError("400", response=r)
        return crudo
    monkeypatch.setattr(carga_datos, "_get_json", falso)
    df = carga_datos.descargar_estacion_dia("precipitacion", inicio="2026-01-01", fin="2026-01-31")  # se suma
    assert df["valor"].iloc[0] == 3.0 and df["n_lecturas"].iloc[0] == 2


def test_ventanas_mensuales_cubren_el_periodo_sin_traslapes():
    v = carga_datos._ventanas_mensuales("2026-01-01", "2026-09-19")
    assert len(v) == 9
    assert v[0] == ("2026-01-01", "2026-01-31")
    assert v[1] == ("2026-02-01", "2026-02-28")
    assert v[-1] == ("2026-09-01", "2026-09-19")


def test_descarga_junta_todos_los_meses(monkeypatch):
    def falso(url, p):
        return [{"fecha": "2026-01-01T00:00:00", "estacion": "1", "municipio": "Ibagué",
                 "valor": "1", "n_lecturas": "1"}]
    monkeypatch.setattr(carga_datos, "_get_json", falso)
    df = carga_datos.descargar_estacion_dia("temperatura", inicio="2026-01-01", fin="2026-03-31")
    assert len(df) == 3  # una respuesta por cada uno de los 3 meses


class RespuestaFalsa:
    status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return [{"ok": 1}]


def test_reintenta_si_se_agota_el_tiempo(monkeypatch):
    llamadas = []

    def get(url, params, timeout):
        llamadas.append(1)
        if len(llamadas) < 3:
            raise requests.exceptions.Timeout("lento")
        return RespuestaFalsa()
    monkeypatch.setattr(carga_datos.requests, "get", get)
    monkeypatch.setattr(carga_datos.time, "sleep", lambda s: None)
    assert carga_datos._get_json("url", {}) == [{"ok": 1}]
    assert len(llamadas) == 3


def test_no_reintenta_en_error_400(monkeypatch):
    llamadas = []

    class Respuesta400(RespuestaFalsa):
        status_code = 400

        def raise_for_status(self):
            raise requests.exceptions.HTTPError("400", response=self)

    def get(url, params, timeout):
        llamadas.append(1)
        return Respuesta400()
    monkeypatch.setattr(carga_datos.requests, "get", get)
    monkeypatch.setattr(carga_datos.time, "sleep", lambda s: None)
    try:
        carga_datos._get_json("url", {})
        assert False, "debía lanzar error"
    except requests.exceptions.HTTPError:
        pass
    assert len(llamadas) == 1
