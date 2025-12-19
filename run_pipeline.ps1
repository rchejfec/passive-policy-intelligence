# PowerShell version of run_pipeline.sh
# Usage:
#   .\run_pipeline.ps1              # Run pipeline and auto-deploy
#   .\run_pipeline.ps1 -SkipDeploy  # Run pipeline without deploying

param(
    [switch]$SkipDeploy
)

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

    # Auto-deploy unless -SkipDeploy flag is set
    if (-not $SkipDeploy) {
        Write-Host "=================================================="
        Write-Host "AUTO-DEPLOY: Committing and pushing changes"
        Write-Host "=================================================="

        # Check if there are changes to commit
        $gitStatus = git status --porcelain portal/src/data/

        if ($gitStatus) {
            Write-Host "Changes detected in portal/src/data/"

            # Stage parquet files
            git add portal/src/data/*.parquet

            # Commit with timestamp
            $commitMessage = "Update data: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
            git commit -m $commitMessage

            # Push to GitHub (triggers GitHub Actions)
            Write-Host "Pushing to GitHub..."
            git push origin main

            if ($LASTEXITCODE -eq 0) {
                Write-Host ""
                Write-Host "✅ Changes pushed successfully!"
                Write-Host "GitHub Actions will build and deploy to:"
                Write-Host "https://rchejfec.github.io/passive-policy-intelligence/"
                Send-TeamsNotification -Status "Success" -Color "00FF00" -Message "✅ The DEMO Digest Pipeline completed successfully and deployed to GitHub."
            } else {
                Write-Host ""
                Write-Host "❌ Failed to push to GitHub (exit code: $LASTEXITCODE)"
                Send-TeamsNotification -Status "Warning" -Color "FF0000" -Message "⚠️ Pipeline succeeded but failed to deploy. Check git configuration."
            }
        } else {
            Write-Host "No changes detected in portal data - skipping deployment"
            Send-TeamsNotification -Status "Success" -Color "00FF00" -Message "✅ The DEMO Digest Pipeline completed successfully (no data changes)."
        }
    } else {
        Write-Host "Deployment skipped (-SkipDeploy flag set)"
        Write-Host ""
        Write-Host "Next steps:"
        Write-Host "  1. Review exported files in portal\src\data\"
        Write-Host "  2. Commit & push when ready: git add portal/src/data/*.parquet && git commit -m 'Update data' && git push"
        Send-TeamsNotification -Status "Success" -Color "00FF00" -Message "✅ The DEMO Digest Pipeline completed successfully (deployment skipped)."
    }
} else {
    Write-Host "FAILURE: Pipeline crashed at $(Get-Date) with exit code $exitCode"
    Send-TeamsNotification -Status "Failure" -Color "FF0000" -Message "❌ The DEMO Digest Pipeline crashed. Check logs."
}

Write-Host "=================================================="
Write-Host ""
