$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

& (Join-Path $PSScriptRoot "generate_icon.ps1")
uv sync --extra desktop --group dev
uv run pyinstaller --noconfirm --clean PaperFlow.spec

$exe = Join-Path $root "dist\PaperFlow\PaperFlow.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Build completed without producing dist\PaperFlow\PaperFlow.exe"
}

Write-Host "Paper Flow desktop build created at: $exe"

$portable = Join-Path $root "dist\PaperFlow-portable.zip"
if (Test-Path -LiteralPath $portable) { Remove-Item -LiteralPath $portable -Force }
Compress-Archive -Path (Join-Path $root "dist\PaperFlow\*") -DestinationPath $portable -CompressionLevel Optimal
Write-Host "Paper Flow portable archive created at: $portable"

$bootstrapper = Join-Path $root "installer\MicrosoftEdgeWebview2Setup.exe"
if (-not (Test-Path -LiteralPath $bootstrapper)) {
    Invoke-WebRequest -UseBasicParsing -Uri "https://go.microsoft.com/fwlink/p/?LinkId=2124703" -OutFile $bootstrapper
}
$signature = Get-AuthenticodeSignature -LiteralPath $bootstrapper
if ($signature.Status -ne "Valid" -or $signature.SignerCertificate.Subject -notlike "*Microsoft Corporation*") {
    throw "The downloaded WebView2 bootstrapper does not have a valid Microsoft signature."
}

$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
    $isccPath = Get-ChildItem "$env:LOCALAPPDATA\Programs\Inno Setup*\ISCC.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($isccPath) { $iscc = $isccPath }
}
if ($iscc) {
    $compiler = if ($iscc.Source) { $iscc.Source } else { $iscc.FullName }
    & $compiler (Join-Path $root "installer\PaperFlow.iss")
    Write-Host "Paper Flow installer created under dist\installer"
} else {
    Write-Host "Inno Setup was not found; the portable desktop build is ready."
    Write-Host "Install Inno Setup and run this script again to create PaperFlow-Setup.exe."
}
