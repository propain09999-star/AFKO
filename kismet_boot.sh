#!/usr/bin/env bash
# System Component: kismet_boot.sh
# Location: Home Directory (~/)

set -e

echo "[+] Initializing KISMET-ASI Local Edge Runtime Node..."

echo "[*] Flushing local caches and clearing device memory shards..."
sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || echo "[*] User Memory Allocation Isolated."

if ! pgrep -x "ollama" > /dev/null; then
    echo "[+] Booting local Ollama Background Engine Core..."
    ollama serve > /dev/null 2>&1 &
    sleep 3
else
    echo "[*] Local Ollama daemon active on port 11434."
fi

BOOT_MODE="${AFKO_BOOT_MODE:-mixed}"
GITHUB_REPO_URL="${GITHUB_REPO_URL:-git@github.com:YOUR_GITHUB_USERNAME/YOUR_REPOSITORY_NAME.git}"
LOCAL_REPO_DIR="${AFKO_LOCAL_REPO_DIR:-${REPO_DIR_NAME:-YOUR_REPOSITORY_NAME}}"

if [ "$BOOT_MODE" = "local" ] || [ "$BOOT_MODE" = "mixed" ]; then
    if [ -d "$LOCAL_REPO_DIR/.git" ]; then
        echo "[+] Using existing local repository at $LOCAL_REPO_DIR"
        cd "$LOCAL_REPO_DIR"
    elif [ "$BOOT_MODE" = "local" ]; then
        echo "[-] Local repository not found at $LOCAL_REPO_DIR"
        exit 1
    fi
fi

if [ ! -d "$LOCAL_REPO_DIR/.git" ]; then
    echo "[+] Cloning active software repository via secure SSH keys..."
    git clone "$GITHUB_REPO_URL" "$LOCAL_REPO_DIR"
    cd "$LOCAL_REPO_DIR"
else
    echo "[*] Existing repository folder detected. Syncing with main branch..."
    cd "$LOCAL_REPO_DIR"
    git pull origin main || true
fi

if [ -f "kismet_quantum_ingress.py" ]; then
    echo "[+] Launching 12-Team Interverse Coherence Grid Engine Loop..."
    python kismet_quantum_ingress.py
else
    echo "[-] Critical Error: Core application entry script missing from repository."
fi
