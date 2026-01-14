#!/usr/bin/env python3
"""
Auto-update Azure PostgreSQL firewall rule with current IP.
Run this whenever you get connection timeout errors.

Requirements:
    pip install azure-cli requests

Setup:
    az login  # One-time Azure authentication
"""

import subprocess
import requests
import sys
import json
import os
import shutil

def get_current_ip():
    """Get current public IP address."""
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        return response.text.strip()
    except Exception as e:
        print(f"Error getting IP: {e}")
        sys.exit(1)

def update_firewall_rule(ip_address, server_name, resource_group):
    """Update or create firewall rule in Azure PostgreSQL."""
    rule_name = "AutoUpdatedIP"

    print(f"Current IP: {ip_address}")
    print(f"Updating firewall rule '{rule_name}' on server '{server_name}'...")

    # Find az command (handle Windows .cmd extension)
    az_cmd = shutil.which('az')
    if not az_cmd:
        # Try common Windows installation path
        az_cmd = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
        if not os.path.exists(az_cmd):
            print("[X] Azure CLI (az) not found. Install it first:")
            print("  https://docs.microsoft.com/cli/azure/install-azure-cli")
            return False

    try:
        # Check if rule already exists with same IP
        check_cmd = [
            az_cmd, 'postgres', 'flexible-server', 'firewall-rule', 'show',
            '--resource-group', resource_group,
            '--name', server_name,
            '--rule-name', rule_name
        ]
        check_result = subprocess.run(check_cmd, capture_output=True, text=True)

        if check_result.returncode == 0:
            # Rule exists, check if IP matches
            rule_info = json.loads(check_result.stdout)
            if rule_info.get('startIpAddress') == ip_address:
                print(f"[OK] IP {ip_address} is already whitelisted!")
                return True

        # Create/update the rule
        cmd = [
            az_cmd, 'postgres', 'flexible-server', 'firewall-rule', 'create',
            '--resource-group', resource_group,
            '--name', server_name,
            '--rule-name', rule_name,
            '--start-ip-address', ip_address,
            '--end-ip-address', ip_address
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"[OK] Firewall rule updated successfully!")
            print(f"  IP {ip_address} can now access the database.")
            return True
        else:
            print(f"[ERROR] Error updating firewall rule:")
            print(result.stderr)
            return False

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

if __name__ == "__main__":
    # Configuration - UPDATE THESE VALUES
    SERVER_NAME = "ai-digest-bd-irpp"
    RESOURCE_GROUP = "AI-digest-project"  # Find in Azure Portal

    if RESOURCE_GROUP == "YOUR_RESOURCE_GROUP":
        print("⚠ Please edit update_db_firewall.py and set RESOURCE_GROUP")
        print("  Find it in Azure Portal > PostgreSQL server > Overview")
        sys.exit(1)

    current_ip = get_current_ip()
    update_firewall_rule(current_ip, SERVER_NAME, RESOURCE_GROUP)
