# Instrucciones para continuar el proyecto final · Tema 01 (DuckDB espacial y GeoParquet)

Responde y escribe todo en español. Trabaja en mi computador desde la terminal integrada de Visual Studio Code.

## 1. Quién soy y qué necesito

Soy Jesús Enrique Flores Riera, estudiante de posgrado de la Universidad Nacional de Colombia. Curso: **Bases de datos espaciales** (2026-2), profesor **Alexys Rodríguez Avellaneda**. Me asignaron el **Tema 01: DuckDB espacial y GeoParquet** (seminario de la semana 13). Necesito terminar el proyecto final para cumplir con la guía y la rúbrica del profesor, ejecutándolo de verdad en mi equipo.

## 2. Repositorios

| Repositorio | Uso |
|:-|:-|
| `jf-floresriera/Proyecto_Bases_de_datos_espaciales` (rama `main`) | **Mi repositorio del proyecto.** Aquí está todo lo hecho hasta ahora. Aquí se trabaja. |
| `alexyshr/bde2026` (privado, del profesor) | Lineamientos. Solo lectura. Lee: `proyectos/00-guia_y_rubrica_proyecto_final.qmd`, `proyectos/01-temas_proyecto_final.qmd`, el syllabus (`chapters/01-syllabus.qmd` o similar), `_quarto.yml` y uno o dos capítulos de `chapters/` para imitar el estilo Quarto del curso. |
| `jf-floresriera/purdue-maize` (privado, mi tesis) | Solo lectura y solo si hace falta. De allí salió el antecedente (commits `c45ae22` y `a0dcd30` del 7-oct-2026). **No copies nada más de la tesis.** |

Clona o actualiza mi repositorio del proyecto y lee primero su `README.md` y la carpeta `proyectos/tema_01_duckdb_geoparquet/`.

## 3. Lo que exige el profesor (resumen de la guía y la rúbrica)

* Carpeta `proyectos/tema_01_duckdb_geoparquet/` con: `01_informe_duckdb_geoparquet.qmd` (capítulo del libro), `01_slides_duckdb_geoparquet.qmd` (RevealJS, 30 min), `01_taller_duckdb_geoparquet.qmd` (live coding, 60 min) y `references.bib`.
* Sesión de 105 min: 30 de presentación, 60 de taller con la cohorte conectada al entorno Docker, 15 de debate sobre métricas (CPU, RAM, E/S, planes de ejecución).
* Diseño experimental del tema: comparar tiempos, memoria y lecturas de E/S de millones de registros en GeoParquet frente a tablas con GiST en PostGIS. Preguntas: (1) ¿cuánto reducen el formato columnar y el empuje de predicados los tiempos de filtrado frente a un escaneo indexado en PostGIS? (2) ¿cuál es el límite de volumen de geometrías complejas que DuckDB procesa en memoria antes de degradarse por paginación en disco? Opcional: demostrar GeoLibre consumiendo GeoParquet/PMTiles.
* Rúbrica: rigor teórico 20 %, implementación y taller 25 %, perfilamiento de rendimiento 25 %, reproducibilidad (Git con **historial progresivo**, Docker con dependencias fijadas, datos abiertos) 15 %, estándares Quarto 15 %.
* Estándares Quarto: opciones de bloque con `#| label:` (Bash, Python, R) y `--| label:` (SQL), sin sintaxis Knitr heredada; etiquetas en kebab-case con prefijos `setup-`, `docker-`, `ddl-`, `dml-`, `query-`/`sql-`, `audit-`, `export-`/`backup-`; un espacio después de cada modificador corto de CLI (`psql -h <host> -p <puerto> -U <usuario> -d <base>`); redacción impersonal y neutral de plataforma ("la terminal integrada de Visual Studio Code", "el sistema anfitrión"); encabezados en *Sentence case*; línea en blanco antes de listas, bloques de código y tablas; referencias cruzadas `@tbl-`, `@fig-`, `@eq-`; citas BibTeX.
* Políticas: entrega por Classroom50 (repositorio privado generado vacío); no se acepta un único commit masivo; los `.qmd` deben compilar sin errores; se sanciona falsificar métricas; la IA se permite si el estudiante entiende y puede explicar cada línea.

## 4. Lo que ya está hecho en `main`

* `antecedentes/tesis_purdue_maize/`: código original de la tesis, importado con su fecha de autoría real (7-oct-2026). **No modificar.**
* `docker-compose.yml` (servicios `db-postgis` con `postgis/postgis:17-3.5` y `lab` con Python 3.12 + DuckDB 1.5.6), `docker/lab/`, `.env.example`, `sql/`.
* `scripts/01_preparar_datos.py` (Overture Maps desde S3 o datos sintéticos → GeoParquet ordenado por Hilbert y sin ordenar + grilla), `02_cargar_postgis.py`, `03_benchmark.py` (experimentos E0-E3), `04_graficas.py`, `monitor_docker.sh`.
* Los tres `.qmd` y `references.bib`, ya redactados. El informe tiene las tablas de resultados, la discusión y las conclusiones **vacías a propósito**.
* **Nada de esto se ha ejecutado todavía.** Es la primera vez que corre: espera errores y corrígelos.

## 5. Reglas que no se negocian

1. **Honestidad del historial**: no cambies fechas de commits (nada de `GIT_AUTHOR_DATE`, `--date`, `rebase` para alterar fechas ni `push --force` sobre `main`). Cada avance real va en un commit nuevo con la fecha real.
2. **Commits pequeños y frecuentes**, con mensajes claros en español (por ejemplo `fix(datos): ...`, `feat(benchmark): ...`, `docs(informe): ...`). Autor: mi identidad de Git. **No agregues líneas `Co-Authored-By`, `Generated with` ni enlaces de sesión** en commits ni en pull requests.
3. **Cero cifras inventadas**: todo número del informe y de las diapositivas debe salir de `resultados/benchmark.csv` y `resultados/resumen.csv` generados en mi equipo. Si algo no se pudo medir, se dice.
4. **No borres** volúmenes, ramas ni archivos sin preguntarme antes.
5. Explícame en lenguaje sencillo cada corrección importante, porque yo debo poder defender cada línea ante el profesor.

## 6. Tareas, en orden

1. **Entorno**: `cp .env.example .env` (cambia la clave), `docker compose up -d --build`, verifica con `docker compose ps`. Corrige lo que falle.
2. **Datos**: `docker compose exec lab python scripts/01_preparar_datos.py`. Si Overture falla, revisa la lectura de la versión desde `https://stac.overturemaps.org/catalog.json` o fija `OVERTURE_RELEASE` en `.env`. Puntos de riesgo a verificar: que exista `ST_Hilbert(geom, BOX_2D)` en DuckDB 1.5.6, los nombres de columna de `parquet_metadata` y que el archivo lleve los metadatos `geo`. Luego `python scripts/02_cargar_postgis.py` y confirma que el número de filas coincide en ambos motores.
3. **Benchmark**: en el sistema anfitrión `bash scripts/monitor_docker.sh resultados/docker_stats.csv`; en paralelo, `docker compose exec lab python scripts/03_benchmark.py --reps 5` y después `scripts/04_graficas.py`. Revisa que la auditoría diga `OK` (mismos resultados en ambos motores).
4. **Barrido de volumen (pregunta 2)**: genera datos sintéticos de 1, 5 y 10 millones (`--fuente sintetico --n ...`), recarga PostGIS y corre E3 guardando cada corrida en un CSV distinto (`--salida resultados/benchmark_sint_5M.csv`). Si hace falta, agrega a los scripts una columna de volumen y actualiza las gráficas.
5. **Informe**: completa la tabla de entorno con las especificaciones reales de mi equipo, llena las tablas de resultados con los valores medidos, activa las figuras comentadas y redacta discusión y conclusiones contrastando H1, H2 y H3. Ajusta la declaración de uso de IA para que describa el uso real.
6. **Diapositivas**: reemplaza la diapositiva de resultados por las cifras y figuras reales.
7. **Quarto**: renderiza los tres `.qmd`. Compara con el `_quarto.yml` y los capítulos del profesor para que el informe compile como capítulo del libro. Revisa la taxonomía de etiquetas y el resto de estándares de la sección 3.
8. **Ensayo del taller**: desde un clon limpio, sigue `01_taller_duckdb_geoparquet.qmd` paso a paso tal como lo haría un compañero, mide cuánto tarda cada paso y ajusta la guía para que quepa en 60 minutos sin bloqueos.
9. **Opcional**: demostración con GeoLibre abriendo `resultados/densidad_celdas.parquet`.
10. **Entrega**: cuando yo tenga el enlace de Classroom50, sigue la guía del profesor: `git remote add classroom <URL>`, `git push -u classroom --all` y `git push classroom --tags`.
11. **Limpieza**: en GitHub queda una rama vieja `tema-01-duckdb-geoparquet` (y el PR #1 cerrado), reemplazada por `main`. Pregúntame antes de borrarla.

Al terminar cada tarea, haz commit y push a `main` y dime en dos o tres líneas qué cambió y qué sigue.
