"""
analisis.py
-----------
Resultados verificables a partir del dataset final: tablas y gráficos.
No afirma relaciones meteorológicas: la comparación por nivel de amenaza solo se calcula si existen
mediciones reales emparejadas, y se presenta como descripción, no como causa.
"""
import matplotlib
matplotlib.use("Agg")  # permite guardar gráficos sin abrir ventanas
import matplotlib.pyplot as plt
import pandas as pd

from . import config
from .integracion import VARIABLES_SALIDA


def _guardar(fig, nombre):
    config.DIR_FIGURAS.mkdir(parents=True, exist_ok=True)
    ruta = config.DIR_FIGURAS / nombre
    fig.tight_layout()
    fig.savefig(ruta, dpi=120)
    plt.close(fig)
    return ruta


def generar_resultados(final):
    """Crea tablas CSV y figuras PNG en outputs/. Devuelve la lista de archivos creados."""
    creados = []
    config.DIR_OUTPUTS.mkdir(parents=True, exist_ok=True)

    # Tabla: alertas por mes y nivel
    por_mes = (final.groupby(["mes", "TEXTO_AMENAZA"]).size().unstack(fill_value=0)
               .reindex(columns=["baja", "moderada", "alta"], fill_value=0))
    por_mes["total"] = por_mes.sum(axis=1)
    ruta = config.DIR_OUTPUTS / "alertas_por_mes_y_nivel.csv"
    por_mes.to_csv(ruta, encoding=config.CODIFICACION_CSV)
    creados.append(ruta)

    # Tabla: alertas por municipio
    por_mun = (final.groupby(["municipio_clave", "COD_DANE"])
               .agg(total_alertas=("nivel_amenaza", "size"),
                    alertas_altas=("nivel_amenaza", lambda s: int((s == 3).sum())),
                    nivel_promedio=("nivel_amenaza", "mean"),
                    estaciones_atmosfericas_cne=("cne_estaciones_atmosfericas", "first"),
                    alertas_con_meteo=("tiene_meteo", "sum"))
               .reset_index().sort_values("total_alertas", ascending=False))
    por_mun["nivel_promedio"] = por_mun["nivel_promedio"].round(2)
    ruta = config.DIR_OUTPUTS / "resumen_alertas_por_municipio.csv"
    por_mun.to_csv(ruta, index=False, encoding=config.CODIFICACION_CSV)
    creados.append(ruta)

    # Figura 1: alertas por mes apiladas por nivel
    fig, ax = plt.subplots(figsize=(9, 5))
    por_mes[["baja", "moderada", "alta"]].plot(kind="bar", stacked=True, ax=ax,
                                               color=["#7fb77e", "#f2c14e", "#d1495b"])
    ax.set_title("Alertas de incendios por mes y nivel de amenaza - Tolima 2026")
    ax.set_xlabel("Mes (1 = enero)")
    ax.set_ylabel("Cantidad de alertas")
    creados.append(_guardar(fig, "alertas_por_mes_y_nivel.png"))

    # Figura 2: 15 municipios con más alertas
    fig, ax = plt.subplots(figsize=(9, 6))
    top = por_mun.head(15).iloc[::-1]
    ax.barh(top["municipio_clave"], top["total_alertas"], color="#3d5a80")
    ax.set_title("15 municipios con más alertas - Tolima 2026")
    ax.set_xlabel("Cantidad de alertas")
    creados.append(_guardar(fig, "top_municipios.png"))

    # Comparación meteorológica por nivel: SOLO si hay mediciones reales emparejadas
    con = final[final["tiene_meteo"]]
    if len(con) > 0:
        cols = list(VARIABLES_SALIDA.values())
        comp = con.groupby("TEXTO_AMENAZA")[cols].mean().round(2)
        comp["alertas_con_meteo"] = con.groupby("TEXTO_AMENAZA").size()
        ruta = config.DIR_OUTPUTS / "meteo_promedio_por_nivel_amenaza.csv"
        comp.to_csv(ruta, encoding=config.CODIFICACION_CSV)
        creados.append(ruta)
    return creados
