# Azure VM Deployment Guide - AI Think Tank Digest Pipeline

This guide walks you through deploying your daily digest pipeline to an Azure B1s VM (free tier) for automated execution.

**Prerequisites:**
- Azure account with free tier active
- Local environment working (pipeline runs successfully)
- Azure PostgreSQL database already configured
- Local files: `/data/chroma_db/`, `.env`, `user_content/*.csv`

---

## Phase 1: Create Azure VM

### 1.1 Create VM via Azure Portal

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Virtual Machines** → **Create** → **Azure virtual machine**
3. Configure:

**Basics:**
- **Subscription:** Your free tier subscription
- **Resource Group:** Create new: `digest-pipeline-rg`
- **VM Name:** `digest-pipeline-vm`
- **Region:** Choose closest to your PostgreSQL database (reduces latency)
- **Image:** `Ubuntu 22.04 LTS - x64 Gen2`
- **Size:** `B1s` (1 vCPU, 1 GB RAM - free tier eligible)
- **Authentication:** SSH public key
  - **Username:** `azureuser`
  - **SSH public key source:** Generate new key pair or use existing
  - **Key pair name:** `digest-vm-key` (download and save securely!)

**Disks:**
- **OS disk type:** Standard SSD (30 GB - included in free tier)
- **Delete with VM:** Yes (recommended)

**Networking:**
- **Virtual network:** Create new or use default
- **Public IP:** Yes (needed for SSH access)
- **NIC network security group:** Basic
- **Public inbound ports:** Allow SSH (22)
- **Delete public IP and NIC when VM is deleted:** Yes

**Management:**
- **Auto-shutdown:** Optional (recommended to prevent accidental overages)
  - Enable: Yes
  - Time: 2:00 AM (after pipeline runs)

**Advanced/Tags:** Leave as defaults

4. Click **Review + Create** → **Create**
5. **IMPORTANT:** Download the private key if you generated a new one
6. Wait for deployment to complete (~3-5 minutes)

### 1.2 Note Connection Details

After deployment completes:
1. Go to the VM resource
2. Copy the **Public IP address** (e.g., `20.185.123.45`)
3. Save this - you'll need it for SSH

---

## Phase 2: Initial VM Setup

### 2.1 SSH into VM

On your local machine:

```bash
# Move SSH key to ~/.ssh/ and set permissions
mv ~/Downloads/digest-vm-key.pem ~/.ssh/
chmod 600 ~/.ssh/digest-vm-key.pem

# SSH into VM
ssh -i ~/.ssh/digest-vm-key.pem azureuser@<YOUR_VM_PUBLIC_IP>
```

**First login:** You'll see a welcome message. Type `yes` to accept fingerprint.

### 2.2 Update System and Install Dependencies

Run these commands on the VM:

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and pip
sudo apt install -y python3.11 python3.11-venv python3-pip

# Install PostgreSQL client (for psycopg2)
sudo apt install -y postgresql-client libpq-dev

# Install git (for version control)
sudo apt install -y git

# Install build essentials (needed for some Python packages)
sudo apt install -y build-essential python3.11-dev

# Verify installations
python3.11 --version  # Should show Python 3.11.x
pip3 --version
```

### 2.3 Create Directory Structure

```bash
# Create app directory
mkdir -p ~/digest-pipeline
cd ~/digest-pipeline

# Create data and logs directories
mkdir -p data logs user_content
```

---

## Phase 3: Transfer Files from Local to VM

**Run these commands on your LOCAL machine** (not on the VM).

### 3.1 Transfer Code

```bash
# Navigate to your local repo
cd ~/path/to/AI-powered-thinktank-digest

# Transfer entire src/ directory
rsync -avz -e "ssh -i ~/.ssh/digest-vm-key.pem" \
  ./src/ \
  azureuser@<YOUR_VM_PUBLIC_IP>:~/digest-pipeline/src/

# Transfer scripts/
rsync -avz -e "ssh -i ~/.ssh/digest-vm-key.pem" \
  ./scripts/ \
  azureuser@<YOUR_VM_PUBLIC_IP>:~/digest-pipeline/scripts/

# Transfer main files
scp -i ~/.ssh/digest-vm-key.pem \
  test_orchestrator.py manage.py requirements.txt \
  azureuser@<YOUR_VM_PUBLIC_IP>:~/digest-pipeline/
```

### 3.2 Transfer User Content (CSV files)

```bash
# Transfer CSV files from user_content/
rsync -avz -e "ssh -i ~/.ssh/digest-vm-key.pem" \
  --include="*.csv" \
  --exclude="*" \
  ./user_content/ \
  azureuser@<YOUR_VM_PUBLIC_IP>:~/digest-pipeline/user_content/
```

### 3.3 Transfer ChromaDB

**IMPORTANT:** This is the largest transfer (~1-3 GB). It may take 10-30 minutes.

```bash
# Transfer ChromaDB directory
rsync -avz --progress -e "ssh -i ~/.ssh/digest-vm-key.pem" \
  ./data/chroma_db/ \
  azureuser@<YOUR_VM_PUBLIC_IP>:~/digest-pipeline/data/chroma_db/

# The --progress flag shows transfer progress
```

### 3.4 Transfer Environment Variables

```bash
# Transfer .env file (contains database credentials)
scp -i ~/.ssh/digest-vm-key.pem \
  .env \
  azureuser@<YOUR_VM_PUBLIC_IP>:~/digest-pipeline/.env
```

### 3.5 Verify Transfer

SSH back into the VM and check:

```bash
ssh -i ~/.ssh/digest-vm-key.pem azureuser@<YOUR_VM_PUBLIC_IP>

# Verify structure
cd ~/digest-pipeline
ls -la

# Check ChromaDB size
du -sh data/chroma_db/

# Verify .env exists (don't cat it - it has credentials!)
ls -la .env
```

---

## Phase 4: Configure Python Environment on VM

SSH into VM and run:

### 4.1 Create Virtual Environment

```bash
cd ~/digest-pipeline

# Create virtual environment with Python 3.11
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 4.2 Install Python Dependencies

```bash
# Install all requirements
pip install -r requirements.txt

# This will take 5-10 minutes (PyTorch is large)
# Watch for any errors - particularly with psycopg2
```

**If psycopg2 fails:**
```bash
# Reinstall with binary version
pip uninstall psycopg2-binary
pip install psycopg2-binary --no-cache-dir
```

### 4.3 Verify Installation

```bash
# Test imports
python3.11 -c "import chromadb; import psycopg2; from sentence_transformers import SentenceTransformer; print('All imports successful!')"

# Test database connection
python3.11 -c "from src.management.db_utils import get_db_connection; conn = get_db_connection(); print('Database connection successful!'); conn.close()"
```

---

## Phase 5: Test Pipeline Execution

### 5.1 Manual Test Run

```bash
cd ~/digest-pipeline
source .venv/bin/activate

# Run the orchestrator
python3.11 test_orchestrator.py

# Monitor output for errors
# Check logs/
ls -lh logs/
```

### 5.2 Verify Results

```bash
# Check that logs were created
cat logs/indexing_log_articles.txt | tail -20

# Test the management CLI
python3.11 manage.py system status
```

---

## Phase 6: Set Up Automated Execution (Cron)

### 6.1 Create Wrapper Script

Create a script that activates the venv and runs the pipeline:

```bash
cd ~/digest-pipeline

cat > run_pipeline.sh << 'EOF'
#!/bin/bash

# Daily Digest Pipeline Runner
# This script is called by cron to run the pipeline

# Set working directory
cd /home/azureuser/digest-pipeline

# Activate virtual environment
source .venv/bin/activate

# Run the orchestrator
python3.11 test_orchestrator.py >> logs/cron_run.log 2>&1

# Log completion
echo "[$(date)] Pipeline run completed" >> logs/cron_run.log

# Deactivate venv
deactivate
EOF

# Make executable
chmod +x run_pipeline.sh
```

### 6.2 Test the Wrapper Script

```bash
# Test it manually first
./run_pipeline.sh

# Check the log
tail -50 logs/cron_run.log
```

### 6.3 Configure Cron Job

```bash
# Open crontab editor
crontab -e

# If prompted, choose nano (easier for beginners)
```

Add this line to run daily at 6:00 AM UTC:

```cron
# Daily Digest Pipeline - Runs at 6:00 AM UTC
0 6 * * * /home/azureuser/digest-pipeline/run_pipeline.sh

# Alternative times (choose one):
# 0 9 * * *   # 9:00 AM UTC
# 0 12 * * *  # 12:00 PM UTC (noon)
# 0 0 * * *   # Midnight UTC
```

**To convert UTC to your local time:**
- Use: https://www.worldtimebuddy.com/
- Or calculate: UTC + your timezone offset

Save and exit:
- In nano: `Ctrl+O` (save), `Enter`, `Ctrl+X` (exit)

### 6.4 Verify Cron Setup

```bash
# List cron jobs
crontab -l

# Check cron logs (after the scheduled time passes)
grep CRON /var/log/syslog | tail -20
```

### 6.5 Manual Trigger Test (Optional)

To test immediately without waiting:

```bash
# Temporarily change cron to run in 2 minutes
# Edit crontab and set: */2 * * * * (runs every 2 minutes)
# Watch logs/cron_run.log
# Then change back to daily schedule
```

---

## Phase 7: Set Up Backups

### 7.1 Create Backup Script

```bash
cd ~/digest-pipeline

cat > backup_chromadb.sh << 'EOF'
#!/bin/bash

# ChromaDB Backup Script
# Runs daily to backup vector database

BACKUP_DIR="/home/azureuser/digest-pipeline/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CHROMA_DIR="/home/azureuser/digest-pipeline/data/chroma_db"

# Create backup directory if needed
mkdir -p "$BACKUP_DIR"

# Create compressed backup
tar -czf "$BACKUP_DIR/chroma_backup_$TIMESTAMP.tar.gz" -C "$CHROMA_DIR" .

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "chroma_backup_*.tar.gz" -mtime +7 -delete

echo "[$(date)] ChromaDB backup completed: chroma_backup_$TIMESTAMP.tar.gz"
EOF

chmod +x backup_chromadb.sh
```

### 7.2 Add Backup to Cron

```bash
crontab -e
```

Add this line (runs at 3:00 AM UTC daily, after pipeline completes):

```cron
# ChromaDB Backup - Runs at 3:00 AM UTC
0 3 * * * /home/azureuser/digest-pipeline/backup_chromadb.sh >> /home/azureuser/digest-pipeline/logs/backup.log 2>&1
```

### 7.3 Test Backup Script

```bash
# Run manually
./backup_chromadb.sh

# Check that backup was created
ls -lh backups/
```

### 7.4 Optional: Azure Blob Storage Backups

For extra safety, you can copy backups to Azure Blob Storage (5GB free):

```bash
# Install Azure CLI
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Login to Azure
az login --use-device-code

# Create storage account (do this once)
az storage account create \
  --name digestbackups \
  --resource-group digest-pipeline-rg \
  --location <YOUR_REGION> \
  --sku Standard_LRS

# Create container
az storage container create \
  --name chromadb-backups \
  --account-name digestbackups

# Upload latest backup
az storage blob upload \
  --account-name digestbackups \
  --container-name chromadb-backups \
  --name "chroma_backup_$(date +%Y%m%d).tar.gz" \
  --file ~/digest-pipeline/backups/chroma_backup_*.tar.gz
```

---

## Phase 8: Monitoring and Maintenance

### 8.1 Check Pipeline Health

Create a monitoring script:

```bash
cd ~/digest-pipeline

cat > check_health.sh << 'EOF'
#!/bin/bash

echo "=== Digest Pipeline Health Check ==="
echo "Date: $(date)"
echo ""

# Check last run
echo "Last cron run:"
tail -5 logs/cron_run.log
echo ""

# Check disk usage
echo "Disk usage:"
df -h /
echo ""

# Check ChromaDB size
echo "ChromaDB size:"
du -sh data/chroma_db/
echo ""

# Check recent article count (requires psql)
echo "Recent articles in database:"
source .venv/bin/activate
python3.11 -c "
from src.management.db_utils import get_db_connection
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM articles WHERE created_at > NOW() - INTERVAL \\'7 days\\'')
count = cursor.fetchone()[0]
print(f'Articles in last 7 days: {count}')
conn.close()
"
EOF

chmod +x check_health.sh
```

Run it anytime:

```bash
./check_health.sh
```

### 8.2 Log Rotation

Prevent logs from growing too large:

```bash
sudo apt install -y logrotate

# Create logrotate config
sudo tee /etc/logrotate.d/digest-pipeline << 'EOF'
/home/azureuser/digest-pipeline/logs/*.log
/home/azureuser/digest-pipeline/logs/*.txt {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 0644 azureuser azureuser
}
EOF
```

### 8.3 Set Up Alerts (Optional)

Simple email alert on failure:

```bash
# Install mailutils
sudo apt install -y mailutils

# Modify cron to email on failure
crontab -e
```

Change cron line to:

```cron
0 6 * * * /home/azureuser/digest-pipeline/run_pipeline.sh || echo "Pipeline failed" | mail -s "Digest Pipeline Error" your-email@example.com
```

---

## Phase 9: Ongoing Maintenance

### 9.1 Weekly Tasks

**Check logs:**
```bash
ssh -i ~/.ssh/digest-vm-key.pem azureuser@<YOUR_VM_PUBLIC_IP>
cd ~/digest-pipeline
./check_health.sh
```

### 9.2 Monthly Tasks

**Update dependencies:**
```bash
ssh -i ~/.ssh/digest-vm-key.pem azureuser@<YOUR_VM_PUBLIC_IP>
cd ~/digest-pipeline
source .venv/bin/activate

# Update Python packages
pip list --outdated
pip install --upgrade <package-name>

# Update system packages
sudo apt update && sudo apt upgrade -y
```

### 9.3 Code Updates

When you update code locally:

**On local machine:**
```bash
cd ~/path/to/AI-powered-thinktank-digest

# Transfer updated files
rsync -avz -e "ssh -i ~/.ssh/digest-vm-key.pem" \
  ./src/ \
  azureuser@<YOUR_VM_PUBLIC_IP>:~/digest-pipeline/src/
```

### 9.4 Recovery from Failure

**If ChromaDB corrupts:**
```bash
# Restore from backup
cd ~/digest-pipeline
tar -xzf backups/chroma_backup_YYYYMMDD_HHMMSS.tar.gz -C data/chroma_db/
```

**If pipeline fails repeatedly:**
```bash
# Check logs
tail -100 logs/cron_run.log
tail -100 logs/indexing_log_articles.txt

# Test database connection
source .venv/bin/activate
python3.11 -c "from src.management.db_utils import get_db_connection; get_db_connection()"

# Restart from scratch
./run_pipeline.sh
```

---

## Troubleshooting

### SSH Connection Issues

**"Connection refused":**
- Check VM is running in Azure Portal
- Verify Public IP hasn't changed
- Check NSG (Network Security Group) allows SSH

**"Permission denied (publickey)":**
- Verify key path: `~/.ssh/digest-vm-key.pem`
- Check permissions: `chmod 600 ~/.ssh/digest-vm-key.pem`
- Verify username: `azureuser`

### Pipeline Failures

**"Module not found":**
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

**"Database connection failed":**
- Check `.env` file exists
- Verify Azure PostgreSQL firewall allows VM's IP
- Test connection manually

**"ChromaDB error":**
- Check disk space: `df -h`
- Verify ChromaDB directory exists: `ls -la data/chroma_db/`
- Restore from backup if corrupted

### Cron Not Running

```bash
# Check cron service
sudo systemctl status cron

# Check cron logs
grep CRON /var/log/syslog | tail -50

# Verify crontab
crontab -l

# Test script manually
./run_pipeline.sh
```

---

## Cost Monitoring

Even with free tier, monitor usage:

1. **Azure Portal** → **Cost Management** → **Cost Analysis**
2. Set up budget alerts (recommended: $5/month threshold)
3. Expected costs with free tier: **$0/month** for first year

**If you exceed free hours:**
- B1s costs ~$10/month
- Stop VM when not needed: `az vm deallocate`
- Use auto-shutdown to prevent overruns

---

## Next Steps

Once deployment is complete:

1. **Monitor for 1 week** - Verify daily runs work
2. **Phase 2: Smart Newsletter** - LLM-powered digest generation
3. **Phase 3: Open Source** - Clean up and publish

---

## Quick Reference

**SSH into VM:**
```bash
ssh -i ~/.ssh/digest-vm-key.pem azureuser@<VM_IP>
```

**Check last run:**
```bash
tail -50 ~/digest-pipeline/logs/cron_run.log
```

**Run manually:**
```bash
cd ~/digest-pipeline && ./run_pipeline.sh
```

**View cron schedule:**
```bash
crontab -l
```

**Health check:**
```bash
~/digest-pipeline/check_health.sh
```

---

**Questions or issues?** Check logs first:
- `logs/cron_run.log` - Overall execution
- `logs/indexing_log_articles.txt` - Article ingestion
- `logs/indexing_log_kb.txt` - Knowledge base indexing
- `/var/log/syslog` - System/cron logs
