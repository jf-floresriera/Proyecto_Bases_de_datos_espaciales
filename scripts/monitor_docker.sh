#!/usr/bin/env bash
# Muestrea CPU y RAM de ambos contenedores mientras corre el benchmark.
# Se ejecuta en el sistema anfitrión (host), en una segunda terminal:
#
#   bash scripts/monitor_docker.sh resultados/docker_stats.csv
#
# Detener con Ctrl+C.
set -euo pipefail
salida="${1:-resultados/docker_stats.csv}"
mkdir -p "$(dirname "$salida")"
echo "marca_tiempo,contenedor,cpu_pct,mem_uso" > "$salida"
while true; do
  ts="$(date -Iseconds)"
  docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}}" bde_t01_postgis bde_t01_lab \
    | sed "s/^/${ts},/" >> "$salida"
  sleep 1
done
