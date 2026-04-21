$ports = @(8002,8003)
foreach ($port in $ports) {
  $conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
  if ($conns) {
    $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($pid in $pids) {
      try {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Write-Output "killed $pid on port $port"
      } catch {
        Write-Output "failed to kill $pid on port $port: $_"
      }
    }
  } else {
    Write-Output "no-listener on $port"
  }
}

Write-Output '--- netstat 8002 ---'
netstat -ano | findstr :8002
Write-Output '--- netstat 8003 ---'
netstat -ano | findstr :8003
