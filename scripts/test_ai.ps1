$ErrorActionPreference = "Stop"
$body = @{
    model = "jarvis-qwen"
    messages = @(
        @{ role = "system"; content = "You are a concise assistant." },
        @{ role = "user"; content = "Reply with exactly: Jarvis AI is online." }
    )
    temperature = 0
    stream = $false
} | ConvertTo-Json -Depth 6

$response = Invoke-RestMethod -UseBasicParsing `
    -Method Post `
    -Uri "http://127.0.0.1:1234/v1/chat/completions" `
    -ContentType "application/json" `
    -Body $body

$response.choices[0].message.content
