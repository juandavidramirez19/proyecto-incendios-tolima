"""
validaciones.py
---------------
Controles de calidad del pipeline. Cada control queda como OK / ADVERTENCIA / FALLA.
Si falla un control crítico, el pipeline se detiene con un error claro.
"""
import pandas as pd

from . import config
from .integracion import VARIABLES_SALIDA


def _chequeo(lista, nombre, cumple, detalle, critico=True):
    estado = "OK" if cumple else ("FALLA" if critico else "ADVERTENCIA")
    lista.append({"validacion": nombre, "estado": estado, "detalle": detalle})


def ejecutar_validaciones(ctx, final):
    """
    ctx: diccionario con conteos que va armando el pipeline.
    final: DataFrame final integrado.
    Devuelve una tabla; lanza ValueError si falla algún control crítico.
    """
    r = []

    # 1. Los originales no cambiaron
    _chequeo(r, "V01 datos originales sin modificar",
             ctx["huellas_inicio"] == ctx["huellas_fin"],
             "Las huellas SHA-256 de data/raw son iguales al inicio y al final.")

    # 2. Conservación de registros (nada se pierde sin explicación)
    suma = (ctx["filas_vacias_descartadas"] + ctx["duplicados_eliminados"]
            + ctx["filas_otros_departamentos"] + ctx["filas_tolima_limpias"])
    _chequeo(r, "V02 conservación de registros",
             suma == ctx["filas_raw"],
             f"crudo {ctx['filas_raw']} = vacías {ctx['filas_vacias_descartadas']} + duplicados "
             f"{ctx['duplicados_eliminados']} + otros departamentos {ctx['filas_otros_departamentos']} "
             f"+ Tolima {ctx['filas_tolima_limpias']} (suma {suma})")

    # 3. La integración no cambia filas
    _chequeo(r, "V03 integración sin pérdida ni duplicación de filas",
             len(final) == ctx["filas_tolima_limpias"],
             f"Tolima limpio {ctx['filas_tolima_limpias']} vs final {len(final)}")

    # 4. Llave única municipio-fecha
    dup = int(final.duplicated(subset=["municipio_clave", "FECHA_EJECUCION"]).sum())
    _chequeo(r, "V04 llave (municipio, fecha) única", dup == 0, f"duplicados encontrados: {dup}")

    # 5. Fechas dentro del periodo declarado y completas
    fmin, fmax = final["FECHA_EJECUCION"].min(), final["FECHA_EJECUCION"].max()
    _chequeo(r, "V05 periodo igual al declarado",
             fmin == pd.Timestamp(ctx["fecha_inicio"]) and fmax == pd.Timestamp(ctx["fecha_fin"]),
             f"datos: {fmin.date()} a {fmax.date()}; declarado: {ctx['fecha_inicio']} a {ctx['fecha_fin']}")
    _chequeo(r, "V06 sin fechas nulas", int(final["FECHA_EJECUCION"].isna().sum()) == 0,
             f"fechas nulas: {int(final['FECHA_EJECUCION'].isna().sum())}")

    # 6. Solo el departamento del proyecto
    deps = set(final["DEPARTAMENTO"].str.upper().unique())
    _chequeo(r, "V07 solo departamento del proyecto", deps == {config.DEPARTAMENTO}, f"departamentos: {deps}")

    # 7. Municipio <-> COD_DANE consistente (1 a 1)
    cod_por_mun = final.groupby("municipio_clave")["COD_DANE"].nunique()
    mun_por_cod = final.groupby("COD_DANE")["municipio_clave"].nunique()
    _chequeo(r, "V08 municipio y COD_DANE consistentes (1 a 1)",
             bool((cod_por_mun == 1).all() and (mun_por_cod == 1).all()),
             f"municipios: {final['municipio_clave'].nunique()}; códigos: {final['COD_DANE'].nunique()}")

    # 8. Columnas clave sin nulos y nivel de amenaza válido
    nulos = int(final[["municipio_clave", "COD_DANE", "nivel_amenaza"]].isna().sum().sum())
    _chequeo(r, "V09 columnas clave sin nulos", nulos == 0, f"nulos en municipio/COD_DANE/nivel: {nulos}")
    _chequeo(r, "V10 nivel de amenaza solo 1, 2 o 3",
             set(final["nivel_amenaza"].dropna().unique()) <= {1, 2, 3},
             f"valores: {sorted(int(x) for x in final['nivel_amenaza'].dropna().unique())}")

    # 9. Meteorología: nunca asignar un dato sin estación que lo respalde
    sin_respaldo = 0
    for variable, col in VARIABLES_SALIDA.items():
        sin_respaldo += int((final[col].notna() & (final[f"n_estaciones_{variable}"] == 0)).sum())
    _chequeo(r, "V11 ningún dato meteorológico sin estación de respaldo", sin_respaldo == 0,
             f"valores sin estación: {sin_respaldo}")

    # 10. Meteorología: valores en rango físico
    fuera = 0
    for variable, col in VARIABLES_SALIDA.items():
        minimo, maximo = config.RANGOS_VALIDOS[variable]
        fuera += int(((final[col] < minimo) | (final[col] > maximo)).sum())
    _chequeo(r, "V12 meteorología dentro de rangos físicos", fuera == 0, f"valores fuera de rango: {fuera}")

    # 11. Cobertura meteorológica (advertencia, no detiene el pipeline)
    con_meteo = int(final["tiene_meteo"].sum())
    pct = round(100 * con_meteo / len(final), 2)
    _chequeo(r, "V13 cobertura meteorológica de las alertas", con_meteo > 0,
             f"alertas con al menos una variable meteorológica: {con_meteo} de {len(final)} ({pct}%)",
             critico=False)

    tabla = pd.DataFrame(r)
    fallas = tabla[tabla["estado"] == "FALLA"]
    if not fallas.empty:
        raise ValueError("Validaciones críticas fallidas:\n" + fallas.to_string(index=False))
    return tabla
