# Checks every feed listed in docs/job-sources.md and reports how many jobs it returns.
# Run from the repo root (Windows PowerShell 5.1 or PowerShell 7):
#   powershell -ExecutionPolicy Bypass -File scripts\check-sources.ps1
# Output: a table in the terminal and source-check.csv in the current folder.
# Run it once by hand. It makes one request per source (two if the first host fails).

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Rough match for Finnish locations (ASCII only so the script works in Windows PowerShell 5.1)
$finland = 'Finland|Suomi|Helsinki|Helsingfors|Espoo|Esbo|Vantaa|Vanda|Oulu|Ule.borg|Tampere|Tammerfors|Turku|Jyv.skyl.|Kuopio|Lahti|Joensuu|Sein.joki|Lappeenranta|Vaasa|Uusimaa|Pirkanmaa|Et.ty'
$sources = @(
    @{ Employer = 'Wolt';                Board = 'greenhouse'; Token = 'wolt' },
    @{ Employer = 'Smartly.io';          Board = 'greenhouse'; Token = 'smartlyio' },
    @{ Employer = 'Solita';              Board = 'greenhouse'; Token = 'solita' },
    @{ Employer = 'RELEX Solutions';     Board = 'greenhouse'; Token = 'relex' },
    @{ Employer = 'Supermetrics';        Board = 'greenhouse'; Token = 'supermetricsoy' },
    @{ Employer = 'Oura';                Board = 'greenhouse'; Token = 'oura' },
    @{ Employer = 'Alif Semiconductor';  Board = 'lever';      Token = 'alifsemi' },
    @{ Employer = 'The Upright Project'; Board = 'lever';      Token = 'uprightproject' },
    @{ Employer = 'Futurice';            Board = 'teamtailor'; Token = 'https://careers.futurice.com' },
    @{ Employer = 'Visma Finland';       Board = 'teamtailor'; Token = 'https://vismafinland.teamtailor.com' },
    @{ Employer = 'Huawei Finland R&D';  Board = 'teamtailor'; Token = 'https://huaweifinlandrnd.teamtailor.com' },
    @{ Employer = 'Codento';             Board = 'teamtailor'; Token = 'https://codento.teamtailor.com' },
    @{ Employer = 'Vincit';              Board = 'teamtailor'; Token = 'https://vincitoyj.teamtailor.com' },
    @{ Employer = 'Siili Solutions';     Board = 'teamtailor'; Token = 'https://siili.teamtailor.com' },
    @{ Employer = 'Eficode';             Board = 'teamtailor'; Token = 'https://career.eficode.com' }
)

function Get-Feed($s) {
    switch ($s.Board) {
        'greenhouse' {
            # Greenhouse hosts boards in a US and an EU region; the token doesn't say which.
            foreach ($h in 'https://boards-api.greenhouse.io', 'https://boards-api.eu.greenhouse.io') {
                $url = "$h/v1/boards/$($s.Token)/jobs"
                try {
                    $r = Invoke-RestMethod -Uri $url -TimeoutSec 30
                    return @{ Url = $url; Items = @($r.jobs | ForEach-Object { $_.location.name }) }
                } catch { }
            }
        }
        'lever' {
            $fallback = $null
            foreach ($h in 'https://api.lever.co', 'https://api.eu.lever.co') {
                $url = "$h/v0/postings/$($s.Token)?mode=json"
                try {
                    $r = @(Invoke-RestMethod -Uri $url -TimeoutSec 30)
                    $found = @{ Url = $url; Items = @($r | ForEach-Object { $_.categories.location }) }
                    if ($found.Items.Count -gt 0) { return $found }
                    if (-not $fallback) { $fallback = $found }
                } catch { }
            }
            return $fallback
        }
        'teamtailor' {
            $url = "$($s.Token)/jobs.rss"
            try {
                $r = Invoke-RestMethod -Uri $url -TimeoutSec 30
                return @{ Url = $url; Items = @($r | Where-Object { $_ } | ForEach-Object { $_.OuterXml }) }
            } catch { }
        }
    }
    return $null
}

$results = foreach ($s in $sources) {
    $f = Get-Feed $s
    if ($f) {
        $count = $f.Items.Count
        $fi = @($f.Items | Where-Object { $_ -match $finland }).Count
        [pscustomobject]@{
            Employer    = $s.Employer
            Board       = $s.Board
            Jobs        = $count
            FinlandJobs = $fi
            Status      = $(if ($count -gt 0) { 'OK' } else { 'EMPTY' })
            FeedUrl     = $f.Url
        }
    } else {
        [pscustomobject]@{
            Employer = $s.Employer; Board = $s.Board; Jobs = 0; FinlandJobs = 0
            Status = 'FAILED'; FeedUrl = ''
        }
    }
}

$results | Format-Table -AutoSize
$results | Export-Csv -Path 'source-check.csv' -NoTypeInformation -Encoding UTF8
Write-Host "Saved source-check.csv. Checked on $(Get-Date -Format 'yyyy-MM-dd')."
