"""OLAP analytics using DuckDB and GeoParquet export.

Implements the pattern requested by the project director: pushing spatial
filters and analytical reductions down to a fast in-process columnar engine
(DuckDB) instead of burdening the OLTP Postgres database.

Uses DuckDB's postgres_scanner and spatial extension to read directly from
the PostGIS tables, crossing them in memory and returning raw Parquet binaries
without ever materializing the massive intermediate sets into Python memory.
"""

import duckdb
import os
import tempfile
from pathlib import Path
from typing import Optional
from datetime import date

from app.core.config import get_settings


class DuckDBAnalyticsEngine:
    def __init__(self):
        # We start a transient in-memory DuckDB connection
        self.conn = duckdb.connect(database=":memory:")
        self.conn.execute("INSTALL spatial;")
        self.conn.execute("LOAD spatial;")
        self.conn.execute("INSTALL postgres;")
        self.conn.execute("LOAD postgres;")

        # Mount the primary PostGIS database into DuckDB.
        # This allows DuckDB to run SELECTs against postgres tables directly.
        settings = get_settings()
        pg_url = settings.SQLALCHEMY_DATABASE_URI
        # The postgres scanner needs the postgresql:// format, not postgresql+asyncpg
        if pg_url.startswith("postgresql+asyncpg://"):
            pg_url = pg_url.replace("postgresql+asyncpg://", "postgresql://")

        self.conn.execute(f"ATTACH '{pg_url}' AS pg (TYPE postgres);")

    def export_zonal_stats_geoparquet(
        self,
        field_id: str,
        product_type: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> bytes:
        """Query zonal statistics directly from PostgreSQL and export to GeoParquet.

        This executes the join and filtering inside DuckDB, taking advantage of
        its highly optimized columnar execution engine.
        """
        where_clauses = [
            f"z.field_id = '{field_id}'",
            f"p.product_type = '{product_type}'"
        ]
        if start_date:
            where_clauses.append(f"z.acquired_at >= '{start_date.isoformat()}'")
        if end_date:
            # We want inclusive end date for the whole day
            where_clauses.append(f"z.acquired_at <= '{end_date.isoformat()} 23:59:59'")

        where_stmt = " AND ".join(where_clauses)

        query = f"""
        SELECT
            z.id,
            z.field_id,
            z.acquired_at,
            p.product_type,
            z.mean,
            z.median,
            z.p10,
            z.p90,
            z.std,
            z.valid_fraction,
            z.u_random,
            z.n_pixels,
            f.geometry
        FROM pg.rs_zonal_stats z
        JOIN pg.rs_products p ON z.product_id = p.id
        JOIN pg.fields f ON z.field_id = f.id
        WHERE {where_stmt}
        ORDER BY z.acquired_at
        """

        # DuckDB handles the conversion to Parquet natively. We write to a temporary
        # file because the parquet format expects seekable binary output.
        with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            self.conn.execute(f"COPY ({query}) TO '{tmp_path}' (FORMAT PARQUET);")
            with open(tmp_path, "rb") as f:
                parquet_bytes = f.read()
            return parquet_bytes
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def close(self):
        self.conn.close()


def get_analytics_engine() -> DuckDBAnalyticsEngine:
    """Factory to instantiate the engine."""
    return DuckDBAnalyticsEngine()
