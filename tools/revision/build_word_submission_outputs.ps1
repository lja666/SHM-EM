[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$BaselineDocx,
    [Parameter(Mandatory = $true)][string]$CleanDocx,
    [Parameter(Mandatory = $true)][string]$MarkedDocx,
    [Parameter(Mandatory = $true)][string]$ResponseDocx,
    [Parameter(Mandatory = $true)][string]$HighlightsDocx,
    [Parameter(Mandatory = $true)][string]$PdfDirectory
)

$ErrorActionPreference = 'Stop'

function Resolve-InputPath([string]$PathValue) {
    return (Resolve-Path -LiteralPath $PathValue).Path
}

function Resolve-OutputPath([string]$PathValue) {
    $full = [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $PathValue))
    $parent = Split-Path -Parent $full
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent | Out-Null
    }
    return $full
}

$baselinePath = Resolve-InputPath $BaselineDocx
$cleanPath = Resolve-InputPath $CleanDocx
$responsePath = Resolve-InputPath $ResponseDocx
$highlightsPath = Resolve-InputPath $HighlightsDocx
$markedPath = Resolve-OutputPath $MarkedDocx
$pdfRoot = Resolve-OutputPath (Join-Path $PdfDirectory '.keep')
$pdfRoot = Split-Path -Parent $pdfRoot

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0

try {
    $baseline = $word.Documents.Open($baselinePath, $false, $true, $false)
    $revised = $word.Documents.Open($cleanPath, $false, $true, $false)
    try {
        $compared = $word.CompareDocuments(
            $baseline,
            $revised,
            2,
            1,
            $false,
            $true,
            $false,
            $true,
            $false,
            $true,
            $true,
            $true,
            $false,
            $true,
            'SHM-EM Authors',
            $true
        )
        try {
            $compared.TrackRevisions = $true
            $compared.SaveAs2($markedPath, 16)
        }
        finally {
            $compared.Close(0)
        }
    }
    finally {
        $revised.Close(0)
        $baseline.Close(0)
    }

    $exports = @(
        @{ Input = $cleanPath; Output = (Join-Path $pdfRoot 'SHM-EM_Revised_Manuscript_Clean.pdf'); Item = 0 },
        @{ Input = $markedPath; Output = (Join-Path $pdfRoot 'SHM-EM_Revised_Manuscript_Marked.pdf'); Item = 7 },
        @{ Input = $responsePath; Output = (Join-Path $pdfRoot 'SHM-EM_Response_to_Reviewers.pdf'); Item = 0 },
        @{ Input = $highlightsPath; Output = (Join-Path $pdfRoot 'SHM-EM_Highlights.pdf'); Item = 0 }
    )
    foreach ($export in $exports) {
        $document = $word.Documents.Open($export.Input, $false, $true, $false)
        try {
            $document.Repaginate()
            $document.ExportAsFixedFormat(
                $export.Output,
                17,
                $false,
                0,
                0,
                1,
                1,
                $export.Item,
                $true,
                $true,
                1,
                $true,
                $true,
                $false
            )
            Write-Output ("{0} -> {1} ({2} pages)" -f $export.Input, $export.Output, $document.ComputeStatistics(2))
        }
        finally {
            $document.Close(0)
        }
    }
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) | Out-Null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()
}
