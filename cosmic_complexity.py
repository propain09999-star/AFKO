import os
import json
import math
import numpy as np

class ComplexityGovernor:
    def __init__(self):
        self.state_file = "complexity_state.json"
        self.dashboard_file = "cosmic_dashboard_view.json"
        print("[+] Complexity Management System (CMS) Online.")

    def calculate_shannon_entropy(self, data_string: str) -> float:
        """
        Measures the operational randomness/chaos of system metrics.
        Higher entropy = system is behaving unpredictably or failing.
        """
        if not data_string:
            return 0.0
        entropy = 0.0
        # Calculate frequency of characters in the system metrics log
        data_len = len(data_string)
        frequencies = {}
        for char in data_string:
            frequencies[char] = frequencies.get(char, 0) + 1
        
        # Shannon Entropy Formula: -Sum(p_i * log2(p_i))
        for count in frequencies.values():
            p = count / data_len
            entropy -= p * math.log2(p)
        return entropy

    def assess_system_chaos(self) -> dict:
        """Reads the diagnostic dashboard data to evaluate current system load."""
        if not os.path.exists(self.dashboard_file):
            return {"chaos_score": 0.5, "recommended_mode": "COHERENCE_STABLE"}

        with open(self.dashboard_file, "r") as f:
            dashboard_data = json.load(f)

        # Convert dashboard metrics into a single string to calculate entropy
        serialized_state = json.dumps(dashboard_data)
        entropy_score = self.calculate_shannon_entropy(serialized_state)
        
        # Max theoretical Shannon entropy for text is ~8.0. Normalizing it here.
        normalized_chaos = min(entropy_score / 5.0, 1.0)
        
        # Determine the systemic threshold action
        if normalized_chaos > 0.75:
            mode = "DISSONANCE_THROTTLE"  # System is too chaotic, slow down execution
        elif normalized_chaos < 0.30:
            mode = "STAGNANT_IDLE"        # System is idle, conserve power
        else:
            mode = "COHERENCE_OPTIMAL"    # System is perfectly balanced
            
        return {
            "chaos_score": round(normalized_chaos, 4),
            "system_entropy_bits": round(entropy_score, 4),
            "recommended_mode": mode
        }

    def enforce_complexity_bounds(self) -> str:
        """Writes the operational instructions that other scripts read to adapt their speed."""
        assessment = self.assess_system_chaos()
        
        complexity_rules = {
            "timestamp": math.trunc(np.datetime64('now').astype(int)),
            "governor_mode": assessment["recommended_mode"],
            "execution_delay_multiplier": 1.0,
            "ai_context_limit": 4096
        }
        
        # Adjust execution rules based on system complexity
        if assessment["recommended_mode"] == "DISSONANCE_THROTTLE":
            print("[⚠️] System complexity threshold crossed! Enforcing architectural throttle.")
            complexity_rules["execution_delay_multiplier"] = 2.5 # Slow down background loops
            complexity_rules["ai_context_limit"] = 1024          # Lower memory footprints for Ollama
        elif assessment["recommended_mode"] == "STAGNANT_IDLE":
            complexity_rules["execution_delay_multiplier"] = 5.0 # Sleep longer to save battery
        else:
            print("[#] System complexity within healthy boundaries. Maintaining optimal performance.")

        with open(self.state_file, "w") as f:
            json.dump(complexity_rules, f, indent=4)
            
        return assessment["recommended_mode"]

if __name__ == "__main__":
    governor = ComplexityGovernor()
    current_mode = governor.enforce_complexity_bounds()
    print(f"[+] Complexity Enforcement Complete. Current System Vector: {current_mode}")
