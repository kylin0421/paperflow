$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$root = Split-Path -Parent $PSScriptRoot
$output = Join-Path $root "branding\PaperFlow.ico"
$bitmap = New-Object System.Drawing.Bitmap 256, 256
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.Clear([System.Drawing.Color]::Transparent)

$background = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 24, 24, 31))
$graphics.FillRectangle($background, 8, 8, 240, 240)

$flowPen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 129, 140, 248)), 16
$flowPen.StartCap = $flowPen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
$graphics.DrawArc($flowPen, 48, 43, 160, 166, 205, 305)
$node = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 199, 210, 254))
$graphics.FillEllipse($node, 54, 68, 26, 26)

$paper = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(255, 247, 247, 251))
$graphics.FillRectangle($paper, 56, 82, 121, 107)
$linePen = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 99, 102, 241)), 10
$linePen.StartCap = $linePen.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
$graphics.DrawLine($linePen, 82, 112, 151, 112)
$graphics.DrawLine($linePen, 82, 136, 136, 136)
$graphics.DrawLine($linePen, 82, 160, 146, 160)

$handle = $bitmap.GetHicon()
$icon = [System.Drawing.Icon]::FromHandle($handle)
$stream = [System.IO.File]::Create($output)
$icon.Save($stream)
$stream.Close()

$linePen.Dispose(); $paper.Dispose(); $node.Dispose(); $flowPen.Dispose(); $background.Dispose()
$graphics.Dispose(); $bitmap.Dispose()
Write-Host "Generated $output"
