#!/usr/bin/env python3
"""
scripts/setup_cron.py

Set up nightly cron job for training team knowledge refresh.

Usage:
    python3.11 scripts/setup_cron.py --install    # install cron job
    python3.11 scripts/setup_cron.py --remove     # remove cron job
    python3.11 scripts/setup_cron.py --status     # show current cron jobs
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FLOW_SCRIPT = REPO_ROOT / "flows" / "training_flow.py"
LOG_PATH = REPO_ROOT / "logs" / "cron.log"
PYTHON = sys.executable

# Run at 2:00 AM daily
CRON_SCHEDULE = "0 2 * * *"
CRON_COMMENT = "# Protean Pursuits — Training Team nightly refresh"
CRON_CMD = (
    f"{CRON_SCHEDULE} "
    f"cd {REPO_ROOT} && "
    f"PYTHONPATH={REPO_ROOT} {PYTHON} {FLOW_SCRIPT} --mode full "
    f">> {LOG_PATH} 2>&1"
)


def get_current_crontab() -> str:
    try:
        result = subprocess.run(["crontab", "-l"],
                                capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def install_cron() -> None:
    current = get_current_crontab()
    if "training_flow.py" in current:
        print("✅ Cron job already installed.")
        return

    new_crontab = current.rstrip() + f"\n{CRON_COMMENT}\n{CRON_CMD}\n"
    proc = subprocess.run(["crontab", "-"],
                          input=new_crontab, text=True)
    if proc.returncode == 0:
        print(f"✅ Cron job installed — runs nightly at 2:00 AM")
        print(f"   Log: {LOG_PATH}")
        print(f"\n   To run manually:")
        print(f"   python3.11 flows/training_flow.py --mode full")
    else:
        print("❌ Failed to install cron job")


def remove_cron() -> None:
    current = get_current_crontab()
    if "training_flow.py" not in current:
        print("ℹ️  No training team cron job found.")
        return

    lines = [l for l in current.splitlines()
             if "training_flow.py" not in l and
             "Protean Pursuits — Training Team" not in l]
    new_crontab = "\n".join(lines) + "\n"
    proc = subprocess.run(["crontab", "-"],
                          input=new_crontab, text=True)
    if proc.returncode == 0:
        print("✅ Cron job removed.")
    else:
        print("❌ Failed to remove cron job")


def show_status() -> None:
    current = get_current_crontab()
    if "training_flow.py" in current:
        print("✅ Training team cron job is INSTALLED")
        for line in current.splitlines():
            if "training_flow.py" in line:
                print(f"   {line}")
    else:
        print("❌ Training team cron job is NOT installed")
        print("   Run: python3.11 scripts/setup_cron.py --install")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--remove", action="store_true")
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.install:
        install_cron()
    elif args.remove:
        remove_cron()
    else:
        show_status()
