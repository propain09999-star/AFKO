import os
import sys
import json
import time
import shutil

class HeadlessSystemLogger:
    def __init__(self, log_dest="system_vitals.json"):
        self.log_dest = log_dest

    def capture_vitals(self) -> dict:
        """
        Gathers raw hardware allocations from the headless Android/Linux core.
        """
        # Get storage bounds (critical for 64GB flash constraints)
        total, used, free = shutil.disk_usage("/")
        
        # Parse low-level memory files (/proc/meminfo) safely without heavy external libraries
        mem_total, mem_free = 0, 0
        try:
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    if "MemTotal" in line:
                        mem_total = int(line.split()[1]) * 1024
                    elif "MemFree" in line:
                        mem_free = int(line.split()[1]) * 1024
        except FileNotFoundError:
            # Fallback values if operating system restricts sandboxed file system access
            mem_total, mem_free = 12 * 1024**3, 4 * 1024**3

        vitals = {
            "timestamp": time.time(),
            "storage_total_gb": round(total / (1024**3), 2),
            "storage_used_gb": round(used / (1024**3), 2),
            "storage_free_gb": round(free / (1024**3), 2),
            "ram_total_mb": round(mem_total / (1024**2), 2),
            "ram_free_mb": round(mem_free / (1024**2), 2),
            "load_average": os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
        }
        return vitals

    def commit_to_matrix(self):
        """
        Writes structured metric logs to disk for the AI engine to read.
        """
        metrics = self.capture_vitals()
        with open(self.log_dest, "w") as f:
            json.dump(metrics, f, indent=4)
        return metrics

if __name__ == "__main__":
    logger = HeadlessSystemLogger()
    data = logger.commit_to_matrix()
    print(f"[+] Local System Waveforms Logged: RAM Free: {data['ram_free_mb']} MB | Storage Free: {data['storage_free_gb']} GB")
