"""Paso 4: resumen estadístico y figuras a partir de resultados/benchmark.csv.

Genera:

* resultados/resumen.csv: mediana, rango intercuartílico y n por
  experimento/variante/parámetro (latencia, CPU, RSS neto, lecturas).
* resultados/figuras/e1_ventanas.png, e2_agregacion.png, e3_memoria.png
* verificación de que PostGIS y DuckDB devuelven el mismo resultado.

Uso:

    python scripts/04_graficas.py
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from comun import FIGURAS, RESULTADOS  # noqa: E402

COLORES = {  # paleta Okabe-Ito (apta para daltonismo)
    "pg_gist": "#0072B2", "pg_seq": "#56B4E9", "pg": "#0072B2",
    "ddb_bbox": "#D55E00", "ddb_sin_bbox": "#E69F00",
    "ddb_bbox_desordenado": "#CC79A7", "ddb": "#D55E00",
}


def iqr(s: pd.Series) -> float:
    return s.quantile(0.75) - s.quantile(0.25)


def resumir(df: pd.DataFrame) -> pd.DataFrame:
    ok = df[df["error"].isna() | (df["error"] == "")]
    base = ok[ok["experimento"] == "E0"]["rss_mb"].median()
    ok = ok.assign(rss_neto_mb=ok["rss_mb"] - (base if pd.notna(base) else 0))
    agr = ok.groupby(["experimento", "variante", "parametro"], sort=False).agg(
        n=("t_s", "size"),
        t_mediana_s=("t_s", "median"), t_iqr_s=("t_s", iqr),
        cpu_mediana_s=("cpu_s", "median"),
        rss_neto_mb=("rss_neto_mb", "median"),
        rchar_mb=("rchar_mb", "median"), read_mb=("read_mb", "median"),
        pg_exec_ms=("pg_exec_ms", "median"),
        shared_hit=("shared_hit", "median"), shared_read=("shared_read", "median"),
        temp_written=("temp_written", "median"),
    )
    return agr.reset_index()


def verificar(df: pd.DataFrame) -> None:
    """Comprueba que todas las variantes de una misma consulta den el mismo valor."""
    d = df.dropna(subset=["resultado"]).copy()
    d = d[d["experimento"] != "E0"]
    # En E1 la ventana define la consulta; en E2 y E3 el parámetro solo es memoria
    d["consulta"] = d["experimento"] + " " + d["parametro"].where(d["experimento"] == "E1", "")
    # Se normaliza Decimal('2.5') de psycopg frente a 2.5 de DuckDB
    d["resultado"] = d["resultado"].str.replace(r"Decimal\('([^']*)'\)", r"\1", regex=True)
    for consulta, g in d.groupby("consulta"):
        valores = g.groupby("variante")["resultado"].first()
        estado = "OK" if valores.nunique() == 1 else "DIFERENCIA"
        print(f"[audit] {consulta.strip()}: {estado} {dict(valores) if estado != 'OK' else ''}")


def barras(res: pd.DataFrame, exp: str, archivo: str, titulo: str) -> None:
    d = res[res["experimento"] == exp]
    if d.empty:
        return
    tabla = d.pivot(index="parametro", columns="variante", values="t_mediana_s")
    err = d.pivot(index="parametro", columns="variante", values="t_iqr_s") / 2
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    tabla.plot.bar(ax=ax, yerr=err, capsize=3, rot=0,
                   color=[COLORES.get(c, "#999999") for c in tabla.columns])
    ax.set_ylabel("Latencia mediana (s)")
    ax.set_xlabel("")
    ax.set_title(titulo)
    ax.legend(frameon=False, fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIGURAS / archivo, dpi=300)
    plt.close(fig)


def memoria(res: pd.DataFrame) -> None:
    d = res[(res["experimento"] == "E3") & (res["variante"] == "ddb")]
    if d.empty:
        return
    pg = res[(res["experimento"] == "E3") & (res["variante"] == "pg_gist")]["t_mediana_s"]
    fig, ax1 = plt.subplots(figsize=(7.5, 4.2))
    ax1.plot(d["parametro"], d["t_mediana_s"], "o-", color=COLORES["ddb"], label="DuckDB: latencia")
    if not pg.empty:
        ax1.axhline(pg.iloc[0], ls="--", color=COLORES["pg_gist"], label="PostGIS GiST: latencia")
    ax1.set_xlabel("memory_limit de DuckDB")
    ax1.set_ylabel("Latencia mediana (s)")
    ax2 = ax1.twinx()
    ax2.bar(d["parametro"], d["rss_neto_mb"], alpha=0.25, color="#555555", label="DuckDB: RSS neto")
    ax2.set_ylabel("RSS neto (MB)")
    fig.legend(loc="upper right", frameon=False, fontsize=8)
    ax1.set_title("E3. Cruce espacial edificios x grilla según presupuesto de memoria")
    fig.tight_layout()
    fig.savefig(FIGURAS / "e3_memoria.png", dpi=300)
    plt.close(fig)


def main() -> None:
    df = pd.read_csv(RESULTADOS / "benchmark.csv")
    FIGURAS.mkdir(parents=True, exist_ok=True)
    res = resumir(df)
    res.to_csv(RESULTADOS / "resumen.csv", index=False)
    print(res.to_string(index=False))
    verificar(df)
    barras(res, "E1", "e1_ventanas.png", "E1. Filtro espacial por ventana (fracción del área)")
    barras(res, "E2", "e2_agregacion.png", "E2. Agregación analítica por clase")
    memoria(res)
    print(f"[export] figuras en {FIGURAS}")


if __name__ == "__main__":
    main()
