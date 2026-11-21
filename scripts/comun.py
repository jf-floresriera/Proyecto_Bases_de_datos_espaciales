"""Parámetros compartidos por los scripts del Tema 01.

Todas las rutas son relativas a la raíz del repositorio para que el flujo
funcione igual en el contenedor `lab` (/work) y en el equipo local.
"""

from __future__ import annotations

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DATOS = RAIZ / "datos"
RESULTADOS = RAIZ / "resultados"
FIGURAS = RESULTADOS / "figuras"
TMP_DUCKDB = DATOS / "tmp"

# Área de estudio: zona urbana de Bogotá D. C. (EPSG:4326, lon/lat)
X0, Y0, X1, Y1 = -74.23, 4.47, -73.99, 4.84
CENTRO = (-74.08, 4.65)

# Artefactos de datos
EDIFICIOS = DATOS / "edificios.parquet"                  # ordenado por curva de Hilbert
EDIFICIOS_SIN_ORDEN = DATOS / "edificios_sin_orden.parquet"
GRILLA = DATOS / "grilla.parquet"

FILAS_POR_GRUPO = 100_000   # row group size de los archivos GeoParquet
LADO_CELDA_GRADOS = 0.0045  # ~500 m en la latitud de Bogotá


def pg_dsn() -> str:
    """Cadena de conexión libpq a partir de las variables de entorno."""
    return (
        f"host={os.getenv('PGHOST', 'localhost')} "
        f"port={os.getenv('PGPORT', '5433')} "
        f"dbname={os.getenv('PGDATABASE', 'bde_t01')} "
        f"user={os.getenv('PGUSER', 'bde')} "
        f"password={os.getenv('PGPASSWORD', '')}"
    )


def pg_url() -> str:
    """URL de SQLAlchemy (psycopg 3)."""
    return (
        f"postgresql+psycopg://{os.getenv('PGUSER', 'bde')}:{os.getenv('PGPASSWORD', '')}"
        f"@{os.getenv('PGHOST', 'localhost')}:{os.getenv('PGPORT', '5433')}"
        f"/{os.getenv('PGDATABASE', 'bde_t01')}"
    )


def ventana(fraccion: float) -> tuple[float, float, float, float]:
    """Rectángulo centrado en CENTRO que cubre `fraccion` del área de estudio."""
    escala = fraccion ** 0.5
    medio_ancho = (X1 - X0) * escala / 2
    medio_alto = (Y1 - Y0) * escala / 2
    cx, cy = CENTRO
    return (cx - medio_ancho, cy - medio_alto, cx + medio_ancho, cy + medio_alto)


def conectar_duckdb(memoria: str | None = None, hilos: int | None = None):
    """Conexión DuckDB en memoria con las extensiones y límites del experimento."""
    import duckdb

    con = duckdb.connect(database=":memory:")
    for ext in ("spatial", "httpfs"):
        try:
            con.load_extension(ext)
        except duckdb.Error:  # fuera del contenedor puede faltar la instalación
            con.install_extension(ext)
            con.load_extension(ext)
    TMP_DUCKDB.mkdir(parents=True, exist_ok=True)
    con.execute(f"SET memory_limit = '{memoria or os.getenv('DUCKDB_MEMORY_LIMIT', '2GB')}'")
    con.execute(f"SET threads = {int(hilos or os.getenv('DUCKDB_THREADS', '4'))}")
    con.execute(f"SET temp_directory = '{TMP_DUCKDB.as_posix()}'")
    return con
