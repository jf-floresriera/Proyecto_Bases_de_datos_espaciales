"""Paso 1: obtención de datos y escritura de archivos GeoParquet.

Dos fuentes posibles:

* ``overture`` (por defecto): huellas de edificaciones de Overture Maps para
  Bogotá, leídas directamente desde el almacenamiento S3 público con DuckDB
  (solo se descargan los grupos de filas que intersecan el área de estudio).
* ``sintetico``: polígonos rectangulares aleatorios con semilla fija, para aulas
  sin conexión o para el barrido de volumen (1, 5, 10 millones de registros).

Salidas en ``datos/``:

* ``edificios.parquet``: GeoParquet ordenado por curva de Hilbert, con columna
  ``bbox`` (xmin, ymin, xmax, ymax) para el empuje de predicados.
* ``edificios_sin_orden.parquet``: mismos registros en orden aleatorio
  (control del experimento E1b: efecto del ordenamiento espacial).
* ``grilla.parquet``: celdas cuadradas de ~500 m para el cruce espacial (E3).

Uso:

    python scripts/01_preparar_datos.py                       # Overture
    python scripts/01_preparar_datos.py --fuente sintetico --n 5000000
"""

from __future__ import annotations

import argparse
import os
import time

from comun import (
    DATOS, EDIFICIOS, EDIFICIOS_SIN_ORDEN, FILAS_POR_GRUPO, GRILLA,
    LADO_CELDA_GRADOS, X0, X1, Y0, Y1, conectar_duckdb,
)

CAJA = f"{{'min_x': {X0}, 'min_y': {Y0}, 'max_x': {X1}, 'max_y': {Y1}}}::BOX_2D"


def release_overture(con) -> str:
    """Versión de Overture: variable OVERTURE_RELEASE o la última del catálogo STAC."""
    release = os.getenv("OVERTURE_RELEASE", "").strip()
    if release:
        return release
    fila = con.execute(
        "SELECT latest FROM read_json_auto('https://stac.overturemaps.org/catalog.json')"
    ).fetchone()
    return str(fila[0])


def crear_tabla_overture(con) -> None:
    con.execute("SET s3_region = 'us-west-2'")
    release = release_overture(con)
    ruta = (
        f"s3://overturemaps-us-west-2/release/{release}"
        "/theme=buildings/type=building/*.parquet"
    )
    print(f"[overture] release {release}")
    # El filtro sobre bbox.* se empuja al lector Parquet: DuckDB descarta grupos
    # de filas completos usando las estadísticas min/max sin descargarlos.
    con.execute(
        f"""
        CREATE TABLE edificios AS
        SELECT
            id,
            names.primary            AS nombre,
            coalesce("class", 'sin_clase') AS clase,
            height                   AS altura,
            num_floors               AS pisos,
            geometry                 AS geom
        FROM read_parquet('{ruta}', hive_partitioning = true)
        WHERE bbox.xmin <= {X1} AND bbox.xmax >= {X0}
          AND bbox.ymin <= {Y1} AND bbox.ymax >= {Y0}
        """
    )


def crear_tabla_sintetica(con, n: int) -> None:
    clases = "['residential', 'commercial', 'industrial', 'education', 'sin_clase']"
    con.execute("SELECT setseed(0.2026)")
    con.execute(
        f"""
        CREATE TABLE edificios AS
        WITH base AS (
            SELECT
                i,
                {X0} + random() * ({X1} - {X0})       AS x,
                {Y0} + random() * ({Y1} - {Y0})       AS y,
                0.00005 + random() * 0.00025          AS lado,
                random()                              AS r_clase,
                random()                              AS r_altura
            FROM range({n}) t(i)
        )
        SELECT
            'sint-' || i                                         AS id,
            NULL::VARCHAR                                        AS nombre,
            {clases}[1 + floor(r_clase * 5)::INTEGER]            AS clase,
            round(3 + r_altura * 45, 1)                          AS altura,
            (1 + floor(r_altura * 15))::INTEGER                  AS pisos,
            ST_MakeEnvelope(x, y, x + lado, y + lado)            AS geom
        FROM base
        """
    )


def escribir_geoparquet(con) -> None:
    columnas = """
        id, nombre, clase, altura, pisos, geom,
        struct_pack(
            xmin := ST_XMin(geom), ymin := ST_YMin(geom),
            xmax := ST_XMax(geom), ymax := ST_YMax(geom)
        ) AS bbox
    """
    opciones = f"(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE {FILAS_POR_GRUPO})"

    # Orden espacial: geometrías cercanas quedan en el mismo grupo de filas, lo
    # que estrecha los rangos min/max de bbox y hace efectivo el empuje.
    try:
        orden = f"ST_Hilbert(geom, {CAJA})"
        con.execute(f"SELECT {orden} FROM edificios LIMIT 1")
    except Exception as exc:  # noqa: BLE001 - se informa y se usa un orden alternativo
        print(f"[aviso] ST_Hilbert no disponible ({exc}); se ordena por centroide")
        orden = "ST_X(ST_Centroid(geom)), ST_Y(ST_Centroid(geom))"

    con.execute(f"COPY (SELECT {columnas} FROM edificios ORDER BY {orden}) TO '{EDIFICIOS}' {opciones}")
    con.execute(f"COPY (SELECT {columnas} FROM edificios ORDER BY random()) TO '{EDIFICIOS_SIN_ORDEN}' {opciones}")


def escribir_grilla(con) -> None:
    nx = int((X1 - X0) / LADO_CELDA_GRADOS) + 1
    ny = int((Y1 - Y0) / LADO_CELDA_GRADOS) + 1
    d = LADO_CELDA_GRADOS
    con.execute(
        f"""
        COPY (
            SELECT
                row_number() OVER (ORDER BY j, i)::INTEGER AS celda_id,
                ST_MakeEnvelope({X0} + i * {d}, {Y0} + j * {d},
                                {X0} + (i + 1) * {d}, {Y0} + (j + 1) * {d}) AS geom
            FROM range({nx}) a(i), range({ny}) b(j)
        ) TO '{GRILLA}' (FORMAT PARQUET)
        """
    )


def auditar(con) -> None:
    for ruta in (EDIFICIOS, EDIFICIOS_SIN_ORDEN, GRILLA):
        filas = con.execute(f"SELECT count(*) FROM read_parquet('{ruta}')").fetchone()[0]
        grupos = con.execute(
            f"SELECT count(DISTINCT row_group_id) FROM parquet_metadata('{ruta}')"
        ).fetchone()[0]
        megas = ruta.stat().st_size / 1e6
        print(f"[audit] {ruta.name}: {filas:,} filas, {grupos} grupos de filas, {megas:.1f} MB")
    # Metadatos GeoParquet ("geo") escritos por DuckDB
    geo = con.execute(
        f"SELECT decode(value) FROM parquet_kv_metadata('{EDIFICIOS}') WHERE decode(key) = 'geo'"
    ).fetchone()
    print("[audit] metadatos 'geo':", geo[0][:300] if geo else "AUSENTES (revisar tipo GEOMETRY)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fuente", choices=("overture", "sintetico"), default="overture")
    parser.add_argument("--n", type=int, default=2_000_000, help="registros sintéticos")
    args = parser.parse_args()

    DATOS.mkdir(parents=True, exist_ok=True)
    con = conectar_duckdb(memoria="4GB")
    t0 = time.perf_counter()
    if args.fuente == "overture":
        crear_tabla_overture(con)
    else:
        crear_tabla_sintetica(con, args.n)
    print(f"[dml] tabla edificios: {con.execute('SELECT count(*) FROM edificios').fetchone()[0]:,} filas "
          f"({time.perf_counter() - t0:.1f} s)")
    escribir_geoparquet(con)
    escribir_grilla(con)
    auditar(con)


if __name__ == "__main__":
    main()
