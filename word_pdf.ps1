param([Parameter(Mandatory=$true)][string]$InputPath, [Parameter(Mandatory=$true)][string]$OutputPath, [string]$FieldsPath, [string]$DocxPath)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$word = $null
$doc = $null
try {
    $word = New-Object -ComObject Word.Application
    Write-Output 'Word iniciado'
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $word.AutomationSecurity = 3
    $doc = $word.Documents.Open($InputPath, $false, $true, $false)
    Write-Output 'Plantilla abierta'
    if ($FieldsPath) {
        $values=Get-Content -LiteralPath $FieldsPath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($prop in $values.PSObject.Properties) {
            $r=$doc.Content.Duplicate
            $f=$r.Find
            $f.ClearFormatting()
            $f.Text='{{'+$prop.Name+'}}'
            $f.Forward=$true
            $f.Wrap=0
            $f.MatchCase=$true
            $f.MatchWildcards=$false
            if (-not $f.Execute()) { throw "Plantilla danada: campo $($prop.Name)" }
            $r.Text=[string]$prop.Value
        }
        if ($doc.Content.Text.Contains('{{')) { throw 'La plantilla contiene campos sin completar.' }
    }
    $doc.Repaginate()
    Write-Output 'Campos completados'
    if ($doc.ComputeStatistics(2) -ne 1) {
        throw 'El texto excede una pagina. Reduzca la longitud de los campos; no se ha cambiado el formato ni el tamano de letra.'
    }
    $doc.ExportAsFixedFormat($OutputPath, 17)
    Write-Output 'PDF exportado'
    if ($DocxPath) { $doc.SaveAs2($DocxPath,16) }
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    exit 1
} finally {
    if ($null -ne $doc) { $doc.Close(0); [Runtime.InteropServices.Marshal]::ReleaseComObject($doc) | Out-Null }
    if ($null -ne $word) { $word.Quit(); [Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null }
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
