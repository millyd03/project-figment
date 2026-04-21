try {
    $r = Invoke-RestMethod -Method Post -Uri http://localhost:8003/_test/enable_mock_spotify -TimeoutSec 5
    Write-Output "enable: $($r | ConvertTo-Json -Compress)"
} catch {
    Write-Output "enable error: $_"
}

try {
    $s = Invoke-RestMethod -Method Get -Uri http://localhost:8003/auth/status -TimeoutSec 5
    Write-Output "status: $($s | ConvertTo-Json -Compress)"
} catch {
    Write-Output "status error: $_"
}

$payload = @{ name='FIGMENT Test Playlist'; throwback=$true; fresh=$false; tacno=$false; christmas=$false; clean=$true } | ConvertTo-Json

try {
    $resp = Invoke-RestMethod -Method Post -Uri http://localhost:8003/create_playlist -Body $payload -ContentType 'application/json' -TimeoutSec 60
    Write-Output "create: $($resp | ConvertTo-Json -Compress)"
} catch {
    Write-Output "create error: $_"
    exit 1
}