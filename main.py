# File: main.py
# Execution: python3 main.py
# Environment: Linux Virtual Environment inside PRoot Ubuntu Container

import os
import sys
import psutil
import requests
import json

class AutonomousLocalAgent:
    def __init__(self, data_directory="./data_vault"):
        self.ollama_url = "http://localhost:11434/api/generate"
        self.data_dir = data_directory
        self.thermal_limit_celsius = 40.0
        
        # Automatically establish a local folder to read system inputs
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def read_local_system_telemetry(self):
        memory_stats = psutil.virtual_memory()
        free_ram_gb = memory_stats.available / (1024**3)
        cpu_utilization = psutil.cpu_percent(interval=0.1)
        
        # Pull native mobile thermal data
        current_temp = 35.0
        try:
            sensors = psutil.sensors_temperatures()
            if 'battery' in sensors:
                current_temp = sensors['battery'].current
        except Exception:
            pass

        return {
            "free_ram_gb": round(free_ram_gb, 2),
            "cpu_percent": cpu_utilization,
            "temperature_celsius": current_temp
        }

    def read_local_knowledge_files(self):
        # The community knowledge harvester loop
        combined_text_context = ""
        for file_name in os.listdir(self.data_dir):
            if file_name.endswith(".txt") or file_name.endswith(".json") or file_name.endswith(".md"):
                file_path = os.path.join(self.data_dir, file_name)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        combined_text_context += f"\n[File: {file_name}]\n{f.read()}\n"
                except Exception as file_read_error:
                    print(f"[-] Error parsing local file {file_name}: {file_read_error}")
        return combined_text_context

    def select_local_model_dynamically(self, metrics):
        # FIXED: Merged methods and made the hardware routing logic real
        if metrics["temperature_celsius"] > self.thermal_limit_celsius or metrics["free_ram_gb"] < 2.0:
            print("[-] Hardware Strained. Selecting low-overhead model.")
            return "tinyllama:latest"  # Preserves battery and device stability
        else:
            print("[+] Resources Optimal. Selecting smart model.")
            return "phi3:mini"       # Unlocks advanced community context parsing

    def execute_autonomous_loop(self, user_objective):
        telemetry = self.read_local_system_telemetry()
        local_files_context = self.read_local_knowledge_files()
        
        # FIXED: Corrected syntax matching name call
        selected_model = self.select_local_model_dynamically(telemetry)
        
        system_instruction = (
            f"You are a local autonomous community agent running natively on an Android device.\n"
            f"Current System Hardware Metrics: {json.dumps(telemetry)}\n"
            f"Available Local Community Knowledge Files:\n{local_files_context}\n"
            f"Use the files above to completely answer the user's objective."
        )
        
        payload = {
            "model": selected_model,
            "prompt": f"{system_instruction}\nObjective: {user_objective}\nResponse:",
            "stream": False
        }

        try:
            response = requests.post(self.ollama_url, json=payload, timeout=45)
            return response.json().get("response", "")
        except Exception as conn_error:
            return f"[-] Connection failed. Is 'ollama serve' running? Error: {conn_error}"

if __name__ == "__main__":
    agent = AutonomousLocalAgent()
    print("[+] KISMET Local Architecture Framework Initialized.")
    
    task = "Summarize the major community assets found inside the data vault files."
    agent_output = agent.execute_autonomous_loop(task)
    print(f"\n[Agent Autonomous Next Step Selection]:\n{agent_output}")
