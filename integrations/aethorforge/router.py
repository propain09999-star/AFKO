import os
import platform


class HybridPolymathRouter:
    """Select a processing profile from query shape and local capabilities."""

    def assess_hardware_extensions(self) -> dict:
        machine = platform.machine().lower()
        is_arm = machine.startswith(("aarch64", "arm64", "armv8", "armv7"))
        return {
            "architecture": machine or "unknown",
            "has_sme2": is_arm and os.getenv("AETHORFORGE_HAS_SME2", "false").lower()
            in {"1", "true", "yes"},
            "has_neon": is_arm,
            "has_i8mm": is_arm and os.getenv("AETHORFORGE_HAS_I8MM", "false").lower()
            in {"1", "true", "yes"},
            "xnnpack_delegate": os.getenv("AETHORFORGE_XNNPACK", "false").lower()
            in {"1", "true", "yes"},
        }

    def evaluate(self, input_query: str) -> dict:
        estimated_tokens = len(input_query.split())
        hardware = self.assess_hardware_extensions()

        if estimated_tokens > 2048 or any(
            marker in input_query.lower() for marker in ("rag", "tool", "memory")
        ):
            return {
                "engine": "LIQUID_LFM2.5_HYBRID",
                "kv_cache_savings_pct": 90.0,
                "active_kernel": "DOUBLE_GATED_LIV_CONVOLUTION_BLOCK",
                "reasoning": "High structural mass detected; routed to the hybrid profile.",
                "hardware": hardware,
            }

        if hardware["has_sme2"] and hardware["xnnpack_delegate"]:
            kernel = "XNNPACK_KLEIDIAI_SME2_iGeMM"
            reason = "Short context detected; SME2 accelerated profile selected."
        elif hardware["has_neon"]:
            kernel = "XNNPACK_NEON_MAPPED"
            reason = "Short context detected; NEON profile selected."
        else:
            kernel = "DEFAULT_FP32"
            reason = "Short context detected; portable CPU profile selected."

        return {
            "engine": "GOOGLE_LITERT_EDGE",
            "kv_cache_savings_pct": 0.0,
            "active_kernel": kernel,
            "reasoning": reason,
            "hardware": hardware,
        }