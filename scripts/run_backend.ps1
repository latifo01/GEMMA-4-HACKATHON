$ErrorActionPreference = "Stop"

if (-not $env:PYTHONPATH) {
    $env:PYTHONPATH = "."
}

$port = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { "8000" }

uvicorn apps.backend.main:app --reload --host 0.0.0.0 --port $port
