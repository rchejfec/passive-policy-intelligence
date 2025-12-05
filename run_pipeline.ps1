# PowerShell version of run_pipeline.sh

# 1. Navigate to project folder (already here)
Set-Location $PSScriptRoot

# 2. Load environment variables from .env file
if (Test-Path .env) {
    Get-Content .env | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+?)\s*=\s*(.+?)\s*$') {
            $name = $matches[1]
            $value = $matches[2]
            # Remove quotes if present
            $value = $value -replace '^["'']|["'']$', ''
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
}

# 3. Activate virtual environment
if (Test-Path .venv\Scripts\Activate.ps1) {
    & .venv\Scripts\Activate.ps1
}

# 4. Define Teams Notification Function (ADAPTIVE CARD FORMAT)
function Send-TeamsNotification {
    param(
        [string]$Status,
        [string]$Color,
        [string]$Message
    )

    # Convert hex colors to Adaptive Card colors
    if ($Color -eq "00FF00") {
        $Color = "Good"
    } else {
        $Color = "Attention"
    }

    # Get current time and hostname
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $hostname = $env:COMPUTERNAME

    # Adaptive Card JSON Payload
    $jsonPayload = @{
        type = "message"
        attachments = @(
            @{
                contentType = "application/vnd.microsoft.card.adaptive"
                content = @{
                    type = "AdaptiveCard"
                    body = @(
                        @{
                            type = "TextBlock"
                            text = "Pipeline Status: $Status"
                            weight = "Bolder"
                            size = "Medium"
                            color = $Color
                        },
                        @{
                            type = "TextBlock"
                            text = $Message
                            wrap = $true
                        },
                        @{
                            type = "FactSet"
                            facts = @(
                                @{
                                    title = "Time"
                                    value = $timestamp
                                },
                                @{
                                    title = "Host"
                                    value = $hostname
                                }
                            )
                        }
                    )
                    "`$schema" = "http://adaptivecards.io/schemas/adaptive-card.json"
                    version = "1.2"
                }
            }
        )
    } | ConvertTo-Json -Depth 10

    # Send the request
    $webhookUrl = $env:TEAMS_WEBHOOK_URL
    # Convert to UTF-8 bytes to properly handle emojis
    $utf8Bytes = [System.Text.Encoding]::UTF8.GetBytes($jsonPayload)
    Invoke-RestMethod -Uri $webhookUrl -Method Post -Body $utf8Bytes -ContentType "application/json; charset=utf-8"
}

# 5. Run the Orchestrator (with automatic DEMO-only export)
Write-Host "=================================================="
Write-Host "DEMO UPDATE: Starting Pipeline Run"
Write-Host "=================================================="
Write-Host "This will update ONLY DEMO anchors for the public site"
Write-Host "Started: $(Get-Date)"
Write-Host ""

python test_orchestrator.py
$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "SUCCESS: Demo data update completed at $(Get-Date)"
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. Review exported files in portal\src\data\"
    Write-Host "  2. Build portal: cd portal && npm run build"
    Write-Host "  3. Deploy when ready: npm run deploy"
    Send-TeamsNotification -Status "Success" -Color "00FF00" -Message "✅ The DEMO Digest Pipeline completed successfully."
} else {
    Write-Host "FAILURE: Pipeline crashed at $(Get-Date) with exit code $exitCode"
    Send-TeamsNotification -Status "Failure" -Color "FF0000" -Message "❌ The DEMO Digest Pipeline crashed. Check logs."
}

Write-Host "=================================================="
Write-Host ""
