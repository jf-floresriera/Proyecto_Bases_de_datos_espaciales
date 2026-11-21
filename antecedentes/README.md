# Antecedentes: origen del trabajo en la tesis de maestría

El patrón que evalúa este proyecto (PostgreSQL/PostGIS como sistema transaccional y DuckDB como motor analítico que exporta a GeoParquet) no nació en este repositorio. Se implementó primero en la plataforma de monitoreo de enfermedades foliares del maíz que el autor desarrolla como tesis de maestría, en el repositorio privado [`jf-floresriera/purdue-maize`](https://github.com/jf-floresriera/purdue-maize).

## Commits originales

| Commit en la tesis | Fecha real (autor y *commit*) | Contenido relacionado con el Tema 01 |
| :-- | :-- | :-- |
| [`c45ae22`](https://github.com/jf-floresriera/purdue-maize/commit/c45ae22b5cca570eb59d11a9d5f3d1ac60274c64) | 2026-10-07 16:37:21 -0500 | `purdue_maize_api/app/services/analytics.py`: motor DuckDB en memoria, `ATTACH ... (TYPE postgres)` sobre PostGIS y exportación con `COPY ... (FORMAT PARQUET)` |
| [`a0dcd30`](https://github.com/jf-floresriera/purdue-maize/commit/a0dcd30e373d6d6ce5c57aa9a5fea0aa9382bfe4) | 2026-10-07 16:37:45 -0500 | Rama `format=geoparquet` del endpoint `GET /rs/export` y dependencias `duckdb`, `pyarrow` y `geopandas` |

En la tesis, ambos commits conservan fecha de autor y fecha de *commit* idénticas al 7 de octubre de 2026, porque se hicieron ese día y nunca se reescribieron. Hacen parte de la rama `main` de la tesis, cuyo historial empieza el 1 de septiembre de 2026.

## Qué se trasladó a este repositorio

| Archivo en `tesis_purdue_maize/` | Origen | Tipo de copia |
| :-- | :-- | :-- |
| [`analytics.py`](tesis_purdue_maize/analytics.py) | `c45ae22:purdue_maize_api/app/services/analytics.py` | Copia literal |
| [`rs_export_endpoint_extracto.py`](tesis_purdue_maize/rs_export_endpoint_extracto.py) | `a0dcd30:purdue_maize_api/app/api/v1/endpoints/rs.py` | Extracto (solo la rama GeoParquet) |
| [`requirements_extracto.txt`](tesis_purdue_maize/requirements_extracto.txt) | `a0dcd30:purdue_maize_api/requirements.txt` | Extracto (solo las dependencias del tema) |

Al importarlos se conservó la **fecha de autor** original (7-oct-2026); la **fecha de *commit*** de la importación es la real del traslado (21-nov-2026). Git guarda las dos fechas por separado y ninguna se alteró.

## Cómo verificarlo

La copia literal tiene la misma huella SHA-1 que el archivo original, de modo que es byte a byte el mismo contenido escrito el 7 de octubre:

```bash
# En este repositorio
git hash-object antecedentes/tesis_purdue_maize/analytics.py
# 3c58c009f4ba9b0b9c4adae1fd8133258da17e6d

# En el repositorio de la tesis (requiere acceso de lectura)
git rev-parse c45ae22:purdue_maize_api/app/services/analytics.py
# 3c58c009f4ba9b0b9c4adae1fd8133258da17e6d
```

Las dos fechas de cada commit importado se consultan con:

```bash
git log --format='%h  autor: %ad  commit: %cd  %s' --date=iso -- antecedentes/
```

Y las fechas originales, en la tesis:

```bash
git log -1 --format='%h %ad %cd %s' --date=iso c45ae22
git log -1 --format='%h %ad %cd %s' --date=iso a0dcd30
```

El resto de la tesis no forma parte de este proyecto. Si el profesor lo solicita, se concede acceso de lectura al repositorio privado para la verificación.
