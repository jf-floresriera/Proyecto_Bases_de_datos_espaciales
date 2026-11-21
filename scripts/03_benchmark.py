"""Paso 3: perfilamiento comparativo PostGIS (GiST) frente a DuckDB (GeoParquet).

Experimentos
------------

E0  Línea base del subproceso DuckDB (SELECT 1): memoria y lecturas fijas de
    arrancar Python + DuckDB + extensiones; se restan en el análisis.
E1  Filtro espacial por ventana (1 %, 10 % y 50 % del área de estudio)
    pg_gist        PostGIS con índice GiST (&& + ST_Intersects)
    pg_seq         PostGIS sin índice (escaneo secuencial forzado)
    ddb_bbox       DuckDB sobre GeoParquet ordenado, con filtro sobre bbox
                   (empuje de predicados) + ST_Intersects
    ddb_sin_bbox   DuckDB sobre GeoParquet ordenado, solo ST_Intersects
    ddb_bbox_desordenado  DuckDB con filtro bbox sobre el archivo sin ordenar
E2  Agregación analítica (conteo y altura media por clase, sin filtro espacial)
E3  Cruce espacial edificios x grilla con barrido de memory_limit en DuckDB

Métricas por repetición
-----------------------

* t_s: latencia de extremo a extremo medida en el cliente (incluye, en PostGIS,
  el viaje por el socket TCP y la serialización del resultado).
* cpu_s, rss_mb, rchar_mb, read_mb: solo DuckDB. Cada consulta corre en un
  subproceso nuevo para medir su pico de memoria residente (ru_maxrss) y sus
  lecturas (/proc/self/io: rchar = todo lo leído; read_bytes = lo que llegó
  del disco físico, sin caché del sistema operativo).
* pg_exec_ms, shared_hit, shared_read, temp_written: solo PostGIS, tomados de
  EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) en una ejecución adicional.
* resultado: valor devuelto, para verificar que ambos motores coinciden.

La RAM del servidor PostgreSQL se audita aparte con scripts/monitor_docker.sh
(docker stats), porque vive en otro proceso y otro contenedor.

Uso:

    python scripts/03_benchmark.py --reps 5
    python scripts/03_benchmark.py --solo E1 --reps 3
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import resource
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from comun import (
    EDIFICIOS, EDIFICIOS_SIN_ORDEN, GRILLA, RESULTADOS, conectar_duckdb, pg_dsn, ventana,
)

FRACCIONES = (0.01, 0.10, 0.50)
MEMORIAS_E3 = ("256MB", "512MB", "1GB", "2GB")
CAMPOS = [
    "marca_tiempo", "experimento", "variante", "parametro", "rep", "t_s", "cpu_s",
    "rss_mb", "rchar_mb", "read_mb", "pg_exec_ms", "shared_hit", "shared_read",
    "temp_written", "resultado", "error",
]


# ---------------------------------------------------------------- consultas SQL
def sql_pg_ventana(v) -> str:
    x0, y0, x1, y1 = v
    env = f"ST_MakeEnvelope({x0}, {y0}, {x1}, {y1}, 4326)"
    return f"SELECT count(*) FROM t01.edificios WHERE geom && {env} AND ST_Intersects(geom, {env})"


def sql_ddb_ventana(v, archivo: Path, con_bbox: bool) -> str:
    x0, y0, x1, y1 = v
    env = f"ST_MakeEnvelope({x0}, {y0}, {x1}, {y1})"
    filtro_bbox = (
        f"bbox.xmin <= {x1} AND bbox.xmax >= {x0} AND bbox.ymin <= {y1} AND bbox.ymax >= {y0} AND "
        if con_bbox else ""
    )
    return f"SELECT count(*) FROM read_parquet('{archivo}') WHERE {filtro_bbox}ST_Intersects(geom, {env})"


SQL_PG_AGREGACION = (
    "SELECT clase, count(*) AS n, round(avg(altura)::numeric, 2) AS altura_media "
    "FROM t01.edificios GROUP BY clase ORDER BY clase"
)
SQL_DDB_AGREGACION = (
    f"SELECT clase, count(*) AS n, round(avg(altura), 2) AS altura_media "
    f"FROM read_parquet('{EDIFICIOS}') GROUP BY clase ORDER BY clase"
)
SQL_PG_CRUCE = (
    "SELECT count(*) FROM ("
    " SELECT g.celda_id, count(*) AS n FROM t01.grilla g"
    " JOIN t01.edificios e ON ST_Intersects(g.geom, e.geom) GROUP BY g.celda_id) s"
)
SQL_DDB_CRUCE = (
    "SELECT count(*) FROM ("
    f" SELECT g.celda_id, count(*) AS n FROM read_parquet('{GRILLA}') g"
    f" JOIN read_parquet('{EDIFICIOS}') e ON ST_Intersects(g.geom, e.geom) GROUP BY g.celda_id) s"
)


# ---------------------------------------------------------------- DuckDB (subproceso)
def trabajador_duckdb(sql: str, memoria: str) -> None:
    """Se ejecuta dentro del subproceso: corre una consulta e imprime métricas JSON."""
    con = conectar_duckdb(memoria=memoria)
    t0 = time.perf_counter()
    filas = con.execute(sql).fetchall()
    t = time.perf_counter() - t0
    uso = resource.getrusage(resource.RUSAGE_SELF)
    io = {}
    try:
        for linea in Path("/proc/self/io").read_text().splitlines():
            k, v = linea.split(":")
            io[k] = int(v)
    except OSError:
        pass
    print(json.dumps({
        "t_s": t,
        "cpu_s": uso.ru_utime + uso.ru_stime,
        "rss_mb": uso.ru_maxrss / 1024,  # Linux: KiB
        "rchar_mb": io.get("rchar", 0) / 1e6,
        "read_mb": io.get("read_bytes", 0) / 1e6,
        "resultado": json.dumps(filas, default=str)[:500],
    }))


def medir_duckdb(sql: str, memoria: str) -> dict:
    proc = subprocess.run(
        [sys.executable, __file__, "--trabajador", "--sql", sql, "--memoria", memoria],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return {"error": proc.stderr.strip().splitlines()[-1][:300] if proc.stderr else "error"}
    return json.loads(proc.stdout.strip().splitlines()[-1])


# ---------------------------------------------------------------- PostGIS
def medir_pg(sql: str, sin_indice: bool = False) -> dict:
    import psycopg

    with psycopg.connect(pg_dsn()) as con:
        if sin_indice:
            con.execute("SET enable_indexscan = off")
            con.execute("SET enable_bitmapscan = off")
        t0 = time.perf_counter()
        filas = con.execute(sql).fetchall()
        t = time.perf_counter() - t0
        plan = con.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}").fetchone()[0][0]
    raiz = plan["Plan"]
    return {
        "t_s": t,
        "pg_exec_ms": plan.get("Execution Time"),
        "shared_hit": raiz.get("Shared Hit Blocks"),
        "shared_read": raiz.get("Shared Read Blocks"),
        "temp_written": raiz.get("Temp Written Blocks"),
        "resultado": json.dumps(filas, default=str)[:500],
    }


# ---------------------------------------------------------------- orquestación
def ejecutar(escritor, experimento, variante, parametro, reps, medir) -> None:
    medir()  # calentamiento: no se registra
    tiempos = []
    for rep in range(1, reps + 1):
        try:
            m = medir()
        except Exception as exc:  # noqa: BLE001 - el error queda en el CSV
            m = {"error": str(exc)[:300]}
        fila = {"marca_tiempo": datetime.now().isoformat(timespec="seconds"),
                "experimento": experimento, "variante": variante,
                "parametro": parametro, "rep": rep, **m}
        escritor.writerow({k: fila.get(k) for k in CAMPOS})
        if "t_s" in m:
            tiempos.append(m["t_s"])
    mediana = f"{statistics.median(tiempos):.3f} s" if tiempos else "ERROR"
    print(f"{experimento:3} {variante:22} {parametro:>8}  mediana {mediana}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--reps", type=int, default=5)
    p.add_argument("--solo", choices=("E1", "E2", "E3"))
    p.add_argument("--salida", default=str(RESULTADOS / "benchmark.csv"))
    p.add_argument("--trabajador", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--sql", help=argparse.SUPPRESS)
    p.add_argument("--memoria", default=os.getenv("DUCKDB_MEMORY_LIMIT", "2GB"), help=argparse.SUPPRESS)
    a = p.parse_args()

    if a.trabajador:
        trabajador_duckdb(a.sql, a.memoria)
        return

    salida = Path(a.salida)
    salida.parent.mkdir(parents=True, exist_ok=True)
    nuevo = not salida.exists()
    mem = a.memoria
    with salida.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if nuevo:
            w.writeheader()

        if a.solo in (None, "E1"):
            ejecutar(w, "E0", "ddb_base", "-", a.reps, lambda: medir_duckdb("SELECT 1", mem))
            for fr in FRACCIONES:
                v, par = ventana(fr), f"{fr:.0%}"
                ejecutar(w, "E1", "pg_gist", par, a.reps, lambda v=v: medir_pg(sql_pg_ventana(v)))
                ejecutar(w, "E1", "pg_seq", par, a.reps, lambda v=v: medir_pg(sql_pg_ventana(v), sin_indice=True))
                ejecutar(w, "E1", "ddb_bbox", par, a.reps,
                         lambda v=v: medir_duckdb(sql_ddb_ventana(v, EDIFICIOS, True), mem))
                ejecutar(w, "E1", "ddb_sin_bbox", par, a.reps,
                         lambda v=v: medir_duckdb(sql_ddb_ventana(v, EDIFICIOS, False), mem))
                ejecutar(w, "E1", "ddb_bbox_desordenado", par, a.reps,
                         lambda v=v: medir_duckdb(sql_ddb_ventana(v, EDIFICIOS_SIN_ORDEN, True), mem))

        if a.solo in (None, "E2"):
            ejecutar(w, "E2", "pg", "-", a.reps, lambda: medir_pg(SQL_PG_AGREGACION))
            ejecutar(w, "E2", "ddb", "-", a.reps, lambda: medir_duckdb(SQL_DDB_AGREGACION, mem))

        if a.solo in (None, "E3"):
            ejecutar(w, "E3", "pg_gist", "-", a.reps, lambda: medir_pg(SQL_PG_CRUCE))
            for m in MEMORIAS_E3:
                ejecutar(w, "E3", "ddb", m, a.reps, lambda m=m: medir_duckdb(SQL_DDB_CRUCE, m))

    print(f"[export] resultados agregados a {salida}")


if __name__ == "__main__":
    main()
