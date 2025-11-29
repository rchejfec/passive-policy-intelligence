# Operations Guide

This guide covers the daily operation, maintenance, and troubleshooting of the AI Daily Digest Pipeline.

## 1. System Architecture

* **Host:** Azure VM (Standard_B1s, Ubuntu 22.04)
* **Runtime:** Python 3.11 (managed via `uv`)
* **Database:** PostgreSQL (Azure Database)
* **Scheduling:** Cron (runs `run_pipeline.sh`)
* **Alerting:** Microsoft Teams Webhook

## 2. Daily Schedule

The pipeline runs automatically twice daily:

1.  **7:00 AM ET:**
    *   Fetches latest news.
    *   Runs analysis.
    *   **Sends the "Morning Paper" digest to Teams.**

2.  **3:00 PM ET:**
    *   Fetches latest news.
    *   Runs analysis.
    *   *Does NOT send a digest (data collection only).*

## 3. Common Tasks

### Connect to the Server

```bash
ssh researchadmin@<YOUR_VM_IP>
```

### Check Pipeline Logs

Follow the live log output:

```bash
tail -f ~/ai-powered-thinktank-digest/pipeline_execution.log
```

### Manually Run the Pipeline

If you need to trigger an immediate run (e.g., after a fix):

```bash
# Run in background (safe to disconnect)
nohup ~/ai-powered-thinktank-digest/run_pipeline.sh > /dev/null 2>&1 &

# Run interactively (to see output)
./run_pipeline.sh
```

### Test Digest Delivery Only

To regenerate and send the digest without re-fetching/analyzing data:

```bash
cd ~/ai-powered-thinktank-digest
source .venv/bin/activate
python -m src.delivery.engine
```

### Manage Subscribers & Anchors

Use the `manage.py` CLI tool.

**List Subscribers:**
```bash
python manage.py subscribers list
```

**Add Subscriber:**
```bash
python manage.py subscribers add --email "user@example.com" --name "Jane Doe"
```

**List Semantic Anchors:**
```bash
python manage.py anchors list
```

**Create New Anchor:**
```bash
python manage.py anchors create
# Follow the interactive prompts
```

## 4. Troubleshooting

### Pipeline Failed (Red Alert in Teams)

1.  **Check the logs:** `tail -n 100 pipeline_execution.log`
2.  **Identify the error:** Look for Python tracebacks or network timeouts.
3.  **Common Issues:**
    *   **Memory Limit:** The B1s VM has limited RAM. If the process was killed, check `dmesg | grep -i oom`.
    *   **Network:** Transient DNS or RSS feed errors. The script automatically retries once after 20 minutes.
    *   **Database:** Connection timeouts. Check `.env` configuration.

### Digest Not Sent

*   Ensure it is after 7:00 AM ET.
*   Check if `run_pipeline.sh` executed successfully.
*   Check `src/delivery/engine.py` logic (it only sends if `datetime.now().hour == 7` by default, unless manually overridden).

### Updating the Code

```bash
cd ~/ai-powered-thinktank-digest
git pull
source .venv/bin/activate
uv pip install -r requirements.txt  # Update dependencies if needed
```

## 5. Maintenance

*   **Disk Space:** Regularly check disk usage with `df -h`.
*   **Database:** Monitor PostgreSQL storage. Run `VACUUM` occasionally if many rows are deleted.
*   **Logs:** The `pipeline_execution.log` can grow large. Consider rotating it if needed.
