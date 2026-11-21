# Tema 01 · DuckDB espacial y GeoParquet frente a PostgreSQL/PostGIS

Proyecto final del curso de posgrado **Bases de datos espaciales** (Universidad Nacional de Colombia, 2026-2, prof. Alexys Rodríguez Avellaneda).
Autor: Jesús Enrique Flores Riera.

Evaluación experimental del procesamiento analítico columnar embebido (DuckDB + extensión `spatial`) sobre archivos GeoParquet locales y en la nube, comparado con tablas indexadas con GiST en PostgreSQL/PostGIS: latencia, CPU, memoria RAM y E/S.

## Estructura

```text
.
├── docker-compose.yml          # db-postgis (PostGIS 17) + lab (Python 3.12, DuckDB 1.5.6)
├── docker/lab/                 # imagen del laboratorio con dependencias fijadas
├── scripts/
│   ├── 01_preparar_datos.py    # Overture Maps (S3) o sintético → GeoParquet ordenado/desordenado
│   ├── 02_cargar_postgis.py    # mismos registros en PostGIS + GiST + auditoría
│   ├── 03_benchmark.py         # experimentos E0-E3 y métricas
│   ├── 04_graficas.py          # resumen, figuras y verificación de resultados
│   └── monitor_docker.sh       # CPU/RAM de ambos contenedores
├── sql/                        # inicialización del esquema t01
├── proyectos/tema_01_duckdb_geoparquet/
│   ├── 01_informe_duckdb_geoparquet.qmd   # capítulo del libro
│   ├── 01_slides_duckdb_geoparquet.qmd    # RevealJS, bloque 1 (30 min)
│   ├── 01_taller_duckdb_geoparquet.qmd    # guía del taller, bloque 2 (60 min)
│   └── references.bib
├── resultados/                 # salidas del benchmark (se generan, no se inventan)
└── antecedentes/tesis_purdue_maize/       # código original de la tesis (ver abajo)
```

## Ejecución rápida

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec lab python scripts/01_preparar_datos.py            # o: --fuente sintetico --n 2000000
docker compose exec lab python scripts/02_cargar_postgis.py
docker compose exec lab python scripts/03_benchmark.py --reps 5
docker compose exec lab python scripts/04_graficas.py
```

Compilación de los documentos Quarto:

```bash
quarto render proyectos/tema_01_duckdb_geoparquet/01_slides_duckdb_geoparquet.qmd
quarto render proyectos/tema_01_duckdb_geoparquet/01_taller_duckdb_geoparquet.qmd
quarto render proyectos/tema_01_duckdb_geoparquet/01_informe_duckdb_geoparquet.qmd
```

## Datos abiertos

* [Overture Maps Foundation](https://docs.overturemaps.org/getting-data/duckdb), tema `buildings`, consultado directamente en `s3://overturemaps-us-west-2/` (licencia indicada por Overture para cada tema). La versión usada queda registrada en la salida de `01_preparar_datos.py`.
* Modo sintético con semilla fija para reproducir el barrido de volumen sin red.

## Antecedentes: origen del trabajo en la tesis

El patrón PostGIS (OLTP) + DuckDB (OLAP) con exportación a GeoParquet se implementó primero en la tesis de maestría del autor (repositorio privado `jf-floresriera/purdue-maize`), en los commits `c45ae22` y `a0dcd30` del **7 de octubre de 2026**. Esos archivos se importaron a `antecedentes/tesis_purdue_maize/` conservando la **fecha de autoría original**; la fecha de *commit* de la importación es la del momento en que se trasladaron a este repositorio (ambas son visibles con `git log --format='%h %ad %cd %s'`). El resto de la tesis no forma parte de este proyecto.

Desde ese antecedente, este repositorio desarrolla el componente experimental que pide el curso: el benchmark comparativo, el taller y el informe.
