# Extracto de purdue_maize_api/app/api/v1/endpoints/rs.py en el commit a0dcd30
# (repositorio privado de tesis jf-floresriera/purdue-maize). Solo la rama GeoParquet
# del endpoint de exportación; el resto del archivo pertenece a la tesis.

@router.get("/export")
async def export_timeseries(
    field_id: str = Query(...),
    product_type: str = Query(default="ndvi"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    format: str = Query(default="csv", pattern="^(csv|geojson|geoparquet)$"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Export the L4 series as CSV, GeoJSON, or GeoParquet via DuckDB."""
    if format == "geoparquet":
        from app.services.analytics import get_analytics_engine
        engine = get_analytics_engine()
        try:
            parquet_bytes = engine.export_zonal_stats_geoparquet(
                field_id=field_id,
                product_type=product_type,
                start_date=start_date,
                end_date=end_date,
            )
            return Response(
                content=parquet_bytes,
                media_type="application/vnd.apache.parquet",
                headers={
                    "Content-Disposition": f'attachment; filename="{product_type}_{field_id}.parquet"'
                },
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Analytics Engine Error: {e}")
        finally:
            engine.close()
    # ... (exportación CSV / GeoJSON omitida)
