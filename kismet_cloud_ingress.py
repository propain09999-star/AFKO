# File Matrix: kismet_cloud_ingress.py
# Runtime: Cloud / Python Local Node Interface

import os
import sqlite3
import requests

from github_auth import get_github_client

class CloudDataIngressHub:
    def __init__(self, db_name="kismet_cloud_vault.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self.initialize_storage_tables()
        print("[+] KISMET Ingress Matrix: Cloud API Connections Engaged.")

    def initialize_storage_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS platform_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_platform TEXT,
                data_payload TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def pull_local_repository_data(self, local_path):
        print(f"[*] Ingesting local repository data from: {local_path}")

        for root, _, files in os.walk(local_path):
            for file in files:
                file_path = os.path.join(root, file)
                if not file_path.lower().endswith((".py", ".md", ".json", ".yaml", ".yml", ".txt")):
                    continue
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        raw_text = f.read()
                except Exception:
                    continue

                self.cursor.execute(
                    "INSERT INTO platform_cache (source_platform, data_payload) VALUES (?, ?)",
                    ("LOCAL", f"File: {os.path.relpath(file_path, local_path)}\nContent: {raw_text}")
                )

        self.conn.commit()

    def pull_repository_data(self, repo_name=None, local_path=None, token: str | None = None):
        if local_path:
            return self.pull_local_repository_data(local_path)

        if repo_name and os.path.isdir(repo_name):
            return self.pull_local_repository_data(repo_name)

        if not repo_name:
            raise ValueError("Repository name or local path must be provided.")

        print(f"[*] Ingesting codebase files from GitHub repository: {repo_name}...")
        try:
            g = get_github_client(token)
            repo = g.get_repo(repo_name)
            contents = repo.get_contents("")
            while contents:
                file_content = contents.pop(0)
                if file_content.type == "dir":
                    contents.extend(repo.get_contents(file_content.path))
                else:
                    raw_text = file_content.decoded_content.decode("utf-8", errors="ignore")
                    self.cursor.execute(
                        "INSERT INTO platform_cache (source_platform, data_payload) VALUES (?, ?)",
                        ("GITHUB", f"File: {file_content.path}\nContent: {raw_text}")
                    )
            self.conn.commit()
        except Exception as exc:
            print(f"[-] Failed to load GitHub repository data: {exc}")
            raise

    def fetch_quantum_entropy_stream(self):
        print("[+] Fetching high-entropy seed from Cisco Outshift Hardware Node...")
        headers = {"Content-Type": "application/json", "x-id-api-key": "DEMO_KEY_OR_MOCK_OVERRIDE"}
        data = {"encoding": "raw", "format": "all", "bits_per_block": 16, "number_of_blocks": 1}
        try:
            res = requests.post("https://api.qrng.outshift.com/api/v1/random_numbers", json=data, headers=headers, timeout=5)
            if res.status_code == 200:
                return res.json().get("data", "0xFA71D23E")
        except Exception:
            return "0xFA71D23E"


if __name__ == "__main__":
    hub = CloudDataIngressHub()
    print("[*] Cloud pipelines connected. System caching structural data inputs...")
