# File Matrix: kismet_notebook_rag.py
# Execution: Part of the automated background boot sequence

import os
import requests
import sqlite3

class LocalNotebookEngine:
    def __init__(self, db_path="kismet_knowledge_base.db"):
        self.db_path = db_path
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "MOCK_KEY")
        self.initialize_vector_mirror()
        print("[+] KISMET NotebookLM Core Engine: Armed and Ingesting Strata.")

    def initialize_vector_mirror(self):
        # Build an embedded SQL table to store raw file chunks alongside embeddings
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_name TEXT,
                file_type TEXT,
                code_chunk TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def ingest_polyglot_repository(self, target_directory="."):
        # Universal Extension Ingestor: Parses ALL code blocks (.rs, .sh, .json, .py)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        print("[*] Documenting all non-python and polyglot repository tracks...")
        for root, dirs, files in os.walk(target_directory):
            # Bypass git tracking layers to save processing overhead
            if ".git" in root or "__pycache__" in root:
                continue
                
            for file in files:
                file_path = os.path.join(root, file)
                file_extension = os.path.splitext(file)[1]
                
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        raw_content = f.read()
                        
                    # Split files into dense 1000-character semantic code chunks
                    chunks = [raw_content[i:i+1000] for i in range(0, len(raw_content), 800)]
                    
                    for chunk in chunks:
                        if len(chunk.strip()) > 10:
                            cursor.execute(
                                "INSERT INTO knowledge_chunks (file_name, file_type, code_chunk) VALUES (?, ?, ?)",
                                (file, file_extension, chunk)
                            )
                    print(f"[+] Ingested: {file} [{file_extension}] -> Split into {len(chunks)} chunks.")
                except Exception as read_error:
                    print(f"[-] Skipped binary node file '{file}': {read_error}")
                    
        conn.commit()
        conn.close()

if __name__ == "__main__":
    notebook = LocalNotebookEngine()
    notebook.ingest_polyglot_repository()
