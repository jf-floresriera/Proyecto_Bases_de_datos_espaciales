# Laboratorio del Tema 01: Python + DuckDB (in-process) + clientes PostGIS
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Cliente psql para comparar con el motor relacional desde la misma terminal
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client time \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Las extensiones de DuckDB se descargan en la construcción de la imagen para
# que el taller no dependa de la red del aula (spatial, httpfs, postgres).
RUN python -c "import duckdb; c = duckdb.connect(); [c.install_extension(e) for e in ('spatial', 'httpfs', 'postgres')]; print(duckdb.__version__)"

WORKDIR /work
