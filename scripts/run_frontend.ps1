$ErrorActionPreference = "Stop"

$frontendPath = Join-Path $PSScriptRoot "..\apps\frontend"
Push-Location $frontendPath
try {
    if (-not (Test-Path ".env.local")) {
        Copy-Item ".env.example" ".env.local"
    }

    npm run dev
}
finally {
    Pop-Location
}
