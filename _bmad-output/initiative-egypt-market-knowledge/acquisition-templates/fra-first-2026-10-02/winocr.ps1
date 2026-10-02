# OCR PNG page images with the Windows built-in engine (Windows.Media.Ocr).
# Usage: powershell -NoProfile -File winocr.ps1 -InputDir <dir of .png> -Language ar-SA
# Writes <name>.json next to each <name>.png that has no .json yet:
#   {"language": "...", "lines": [{"text": "...", "words": n, "top": y, "left": x, "right": x2}], "angle": deg}
# Offline; no network. Lines keep the engine's own reading order.
param(
    [Parameter(Mandatory = $true)][string]$InputDir,
    [string]$Language = "ar-SA"
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Globalization.Language, Windows.Globalization, ContentType = WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
        $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
        $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, [Type]$type) {
    $task = $asTaskGeneric.MakeGenericMethod($type).Invoke($null, @($op))
    $task.Wait(-1) | Out-Null
    $task.Result
}

$lang = [Windows.Globalization.Language]::new($Language)
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)
if ($null -eq $engine) { throw "OCR language not available: $Language" }

Get-ChildItem -Path $InputDir -Filter *.png | Sort-Object Name | ForEach-Object {
    $out = [System.IO.Path]::ChangeExtension($_.FullName, ".json")
    if (Test-Path $out) { return }
    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($_.FullName)) ([Windows.Storage.StorageFile])
    $stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    $lines = @()
    foreach ($line in $result.Lines) {
        $xs = $line.Words | ForEach-Object { $_.BoundingRect.X }
        $xe = $line.Words | ForEach-Object { $_.BoundingRect.X + $_.BoundingRect.Width }
        $ys = $line.Words | ForEach-Object { $_.BoundingRect.Y }
        $lines += [ordered]@{
            text  = $line.Text
            words = $line.Words.Count
            top   = [int](($ys | Measure-Object -Minimum).Minimum)
            left  = [int](($xs | Measure-Object -Minimum).Minimum)
            right = [int](($xe | Measure-Object -Maximum).Maximum)
        }
    }
    $stream.Dispose()
    $payload = [ordered]@{ language = $Language; angle = $result.TextAngle; lines = $lines }
    [System.IO.File]::WriteAllText($out, ($payload | ConvertTo-Json -Depth 5 -Compress), [System.Text.UTF8Encoding]::new($false))
}
