# Muestrea CPU y RAM de ambos contenedores mientras corre el benchmark.
# Equivalente de monitor_docker.sh para Windows (PowerShell 5.1 o 7).
# Se ejecuta en el sistema anfitrión (host), en una segunda terminal:
#
#   powershell -ExecutionPolicy Bypass -File scripts/monitor_docker.ps1 resultados/docker_stats.csv
#
# Detener con Ctrl+C. Produce el mismo CSV que la versión Bash.
param([string]$Salida = "resultados/docker_stats.csv")
$ErrorActionPreference = "Stop"
$dir = Split-Path -Parent $Salida
if ($dir) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
"marca_tiempo,contenedor,cpu_pct,mem_uso" | Set-Content -Encoding utf8 $Salida
while ($true) {
    $ts = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
    docker stats --no-stream --format "{{.Name}},{{.CPUPerc}},{{.MemUsage}}" bde_t01_postgis bde_t01_lab |
        ForEach-Object { "$ts,$_" } | Add-Content -Encoding utf8 $Salida
    Start-Sleep -Seconds 1
}
