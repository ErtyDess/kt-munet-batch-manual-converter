$outputFile = "mai2_tachi_batch_manual_import_munet_$(Get-Date -Format 'dd-MM-yyyy').json"

$pyPath = "C:\Users\e.mucelli\AppData\Local\Programs\Python\Python312\python.exe"
$script = Join-Path $PSScriptRoot "convert_munet_scores_to_tachi_batch_manual.py"
$inputFile = (Get-ChildItem (Join-Path $PSScriptRoot "MuNET Export*.json") | Select-Object -First 1).FullName

if (-not $inputFile) {
    Write-Host "Nessun file 'MuNET Export*.json' trovato nella cartella dello script."
    exit 1
}

Write-Host "Input:  $inputFile"
Write-Host "Output: $outputFile"

& $pyPath $script $inputFile $outputFile
