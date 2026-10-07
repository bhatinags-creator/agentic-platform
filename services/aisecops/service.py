class AISecOpsMonitoringService:
    def inspect_prompt(self, prompt: str) -> dict:
        suspicious = any(term in prompt.lower() for term in ["ignore instructions", "jailbreak", "exfiltrate"])
        return {"signal": "prompt_attack" if suspicious else "none", "severity": "high" if suspicious else "none"}
