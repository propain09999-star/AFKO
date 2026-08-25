# File: local_router.py
# Purpose: Real-world conditional routing script based on hardware resource limits

import os
import psutil
import requests

class LocalModelRouter:
    def __init__(self):
        self.ollama_url = "http://localhost:11434/api/generate"
        # 40°C is a standard threshold where mobile processors begin to thermal throttle
        self.thermal_ceiling_celsius = 40.0 

    def get_battery_temperature(self):
        # Reads the standard Android battery thermal sensor path via psutil
        try:
            sensors = psutil.sensors_temperatures()
            if 'battery' in sensors:
                return sensors['battery'][0].current
        except Exception:
            pass
        return 35.0  # Room temperature fallback estimate

    def select_model_by_resource_limits(self):
        current_temp = self.get_battery_temperature()
        # Calculate exactly how much physical RAM is left over in Gigabytes
        free_ram_gb = psutil.virtual_memory().available / (1024**3)
        
        print(f"[Diagnostics] Temp: {current_temp}°C | Available RAM: {free_ram_gb:.2f}GB")

        # Basic conditional routing logic based on physical hardware states
        if current_temp > self.thermal_ceiling_celsius:
            # Overheating mitigation: Use the smallest possible model footprint
            print("[-] High temperature detected. Selecting low-overhead model.")
            return "tinyllama:latest"
        elif free_ram_gb < 2.0:
            # Memory safety mitigation: Avoid an OOM process crash
            print("[-] Low memory margin. Selecting intermediate model.")
            return "orca-mini:3b"
        else:
            # Baseline execution: Sufficient resources are available for the larger model
            print("[+] Resource space stable. Selecting primary model.")
            return "phi3:mini"

    def send_inference_request(self, user_prompt):
        selected_model = self.select_model_by_resource_limits()
        
        payload = {
            "model": selected_model,
            "prompt": user_prompt,
            "stream": False
        }

        try:
            response = requests.post(self.ollama_url, json=payload, timeout=30)
            return response.json().get("response", "")
        except Exception as e:
            return f"[-] Connection Error: Ensure 'ollama serve' is running locally. Details: {e}"

if __name__ == "__main__":
    router = LocalModelRouter()
    query = "Summarize the basic configuration steps for local package databases."
    output = router.send_inference_request(query)
    print(f"\n[Model Response ({router.select_model_by_resource_limits()})]:\n{output}")
