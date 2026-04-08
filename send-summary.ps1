[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$url = "https://api.telegram.org/bot8793913620:AAFALwtiJ2AjrnpMiJ7aUNcobHMuhYLjVwM/sendMessage"

function Send-Message($text) {
    $json = @{chat_id="8208591984"; text=$text} | ConvertTo-Json -Compress
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    for ($i=1; $i<=3; $i++) {
        try {
            $result = Invoke-RestMethod -Uri $url -Method Post -Body $bytes -ContentType "application/json; charset=utf-8" -TimeoutSec 30
            if ($result.ok) { return $result.result.message_id }
        } catch { Start-Sleep -Seconds 2 }
    }
    return -1
}

$text = "Test message from Windows Claude Code"
$id = Send-Message $text
if ($id -gt 0) { Write-Host "Sent (id: $id)" } else { Write-Host "Failed after 3 retries" }