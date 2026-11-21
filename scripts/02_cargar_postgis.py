"""Paso 2: carga de los mismos GeoParquet en PostGIS (línea base relacional).

Se cargan exactamente los registros de ``datos/edificios.parquet`` y
``datos/grilla.parquet`` en el esquema ``t01``, se crean índices GiST y B-Tree,
se ejecuta ``VACUUM ANALYZE`` y se audita el conteo de filas y la validez
geométrica, de modo que ambos motores respondan sobre datos idénticos.

Uso:

    python scripts/02_cargar_postgis.py
"""

from __future__ import annotations

import time

import geopandas as gpd
import psycopg
import shapely
from sqlalchemy import create_engine

from comun import EDIFICIOS, GRILLA, conectar_duckdb, pg_dsn, pg_url

DDL_POST_CARGA = [
    "ALTER TABLE t01.edificios ADD PRIMARY KEY (id)",
    "ALTER TABLE t01.grilla ADD PRIMARY KEY (celda_id)",
    "CREATE INDEX IF NOT EXISTS edificios_geom_gist ON t01.edificios USING GIST (geom)",
    "CREATE INDEX IF NOT EXISTS grilla_geom_gist ON t01.grilla USING GIST (geom)",
    "CREATE INDEX IF NOT EXISTS edificios_clase_btree ON t01.edificios (clase)",
]


def leer_geoparquet(ruta) -> gpd.GeoDataFrame:
    """Lee el archivo con DuckDB y reconstruye las geometrías desde WKB.

    Se evita depender de cómo cada librería interpreta los metadatos GeoParquet
    (1.x en la clave "geo" o tipos nativos de Parquet): el WKB es el contrato
    común OGC entre DuckDB y PostGIS. La columna bbox se omite porque solo le
    sirve al lector Parquet para el empuje de predicados.
    """
    con = conectar_duckdb(memoria="3GB")
    columnas = [
        c for (c,) in con.execute(
            f"SELECT column_name FROM (DESCRIBE SELECT * FROM read_parquet('{ruta}'))"
        ).fetchall()
        if c not in ("geom", "bbox")
    ]
    lista = ", ".join(columnas)
    df = con.execute(
        f"SELECT {lista}, ST_AsWKB(geom) AS wkb FROM read_parquet('{ruta}')"
    ).df()
    con.close()
    geometrias = shapely.from_wkb(df.pop("wkb").map(bytes))
    return gpd.GeoDataFrame(df, geometry=geometrias, crs=4326).rename_geometry("geom")


def cargar(ruta, tabla: str, engine) -> None:
    t0 = time.perf_counter()
    gdf = leer_geoparquet(ruta)
    gdf.to_postgis(tabla, engine, schema="t01", if_exists="replace", index=False, chunksize=50_000)
    print(f"[dml] t01.{tabla}: {len(gdf):,} filas en {time.perf_counter() - t0:.1f} s")


def main() -> None:
    with psycopg.connect(pg_dsn(), autocommit=True) as con:
        con.execute("CREATE EXTENSION IF NOT EXISTS postgis")
        con.execute("CREATE EXTENSION IF NOT EXISTS pg_stat_statements")
        con.execute("CREATE SCHEMA IF NOT EXISTS t01")

    engine = create_engine(pg_url())
    cargar(EDIFICIOS, "edificios", engine)
    cargar(GRILLA, "grilla", engine)
    engine.dispose()

    with psycopg.connect(pg_dsn(), autocommit=True) as con:
        for sentencia in DDL_POST_CARGA:
            t0 = time.perf_counter()
            con.execute(sentencia)
            print(f"[ddl] {sentencia} ({time.perf_counter() - t0:.1f} s)")
        con.execute("VACUUM ANALYZE t01.edificios")
        con.execute("VACUUM ANALYZE t01.grilla")

        filas, invalidas, srid = con.execute(
            "SELECT count(*), count(*) FILTER (WHERE NOT ST_IsValid(geom)), "
            "min(ST_SRID(geom)) FROM t01.edificios"
        ).fetchone()
        tam = con.execute(
            "SELECT pg_size_pretty(pg_total_relation_size('t01.edificios')), "
            "pg_size_pretty(pg_relation_size('t01.edificios_geom_gist'))"
        ).fetchone()
        print(f"[audit] edificios: {filas:,} filas, {invalidas} inválidas, SRID {srid}, "
              f"tabla+índices {tam[0]}, GiST {tam[1]}")


if __name__ == "__main__":
    main()
