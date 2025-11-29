#!/bin/bash

# 1. Navigate to YOUR project folder
cd /home/researchadmin/ai-powered-thinktank-digest

# 2. Load environment variables
set -o allexport
source .env
set +o allexport

# 3. Activate the virtual environment
source .venv/bin/activate

# 4. Define the Teams Notification Function (ADAPTIVE CARD FORMAT)
send_teams_notification() {
    local status=$1
    local color=$2   # "Good" (Green) or "Attention" (Red)
    local message=$3

    # Convert logic colors to Adaptive Card colors
    if [ "$color" == "00FF00" ]; then color="Good"; else color="Attention"; fi

    # Adaptive Card JSON Payload
    json_payload=$(cat <<EOF
{
    "type": "message",
    "attachments": [
        {
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "type": "AdaptiveCard",
                "body": [
                    {
                        "type": "TextBlock",
                        "text": "Pipeline Status: $status",
                        "weight": "Bolder",
                        "size": "Medium",
                        "color": "$color"
                    },
                    {
                        "type": "TextBlock",
                        "text": "$message",
                        "wrap": true
                    },
                    {
                        "type": "FactSet",
                        "facts": [
                            {
                                "title": "Time",
                                "value": "$(date)"
                            },
                            {
                                "title": "Host",
                                "value": "$(hostname)"
                            }
                        ]
                    }
                ],
                "\$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "version": "1.2"
            }
        }
    ]
}
EOF
)

    # Send the request
    curl -H "Content-Type: application/json" -d "$json_payload" "$TEAMS_WEBHOOK_URL"
}

# 5. Run the Orchestrator
echo "=================================================="
echo "Starting Pipeline Run: $(date)"

python test_orchestrator.py
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "SUCCESS: Pipeline finished at $(date)"
    send_teams_notification "Success" "00FF00" "✅ The AI Digest Pipeline completed successfully."
else
    echo "FAILURE: Pipeline crashed at $(date) with exit code $EXIT_CODE"
    send_teams_notification "Failure" "FF0000" "❌ The AI Digest Pipeline crashed. Check logs."
fi

echo "=================================================="
echo ""
