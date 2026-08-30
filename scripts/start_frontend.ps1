$ErrorActionPreference = "Stop"
$frontend = Join-Path $PSScriptRoot "..\frontend"
Set-Location $frontend
npm install
npm run dev
