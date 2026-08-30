"""
Shared configuration for AI model selection and pricing.

Multi-Model Architecture:
- Document, Fraud, Compliance agents: Gemini 3.5 Flash (complex multimodal reasoning)
- Investigation agent: Gemini 3.5 Flash-Lite (cost-efficient summarization)

This demonstrates strategic model selection based on task requirements.
"""

import os
from threading import Lock

_lock = Lock()
_model_id = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# Model pricing per 1M tokens (USD)
# Source: https://ai.google.dev/gemini-api/docs/pricing
PRICING = {
    "gemini-3.5-flash": {
        "input": 0.15,
        "output": 0.60,
        "name": "Gemini 3.5 Flash",
        "description": "Balanced - good for most tasks"
    },
    "gemini-3.5-flash-lite": {
        "input": 0.075,
        "output": 0.30,
        "name": "Gemini 3.5 Flash-Lite",
        "description": "Budget - high volume, cost-sensitive"
    },
    "gemini-3.6-flash": {
        "input": 0.15,
        "output": 0.60,
        "name": "Gemini 3.6 Flash",
        "description": "Enhanced - improved code & reasoning"
    },
    "gemini-3.7-flash": {
        "input": 0.15,
        "output": 0.60,
        "name": "Gemini 3.7 Flash",
        "description": "Latest - best multimodal reasoning"
    },
}

def get_model() -> str:
    """Get the current model ID."""
    return _model_id

def set_model(model: str) -> bool:
    """Set the model ID. Returns False if model is not in PRICING."""
    global _model_id
    if model not in PRICING:
        return False
    with _lock:
        _model_id = model
    return True

def get_pricing() -> dict:
    """Get pricing info for current model."""
    return PRICING.get(_model_id, PRICING["gemini-3.5-flash"])

def pricing_for(model: str | None) -> dict:
    """
    Get pricing for a specific model id.

    Cost must be computed per step, not per project: the investigation agent runs
    on Flash-Lite at half the Flash rate, so pricing every token at the currently
    selected model's rate would misreport the bill.
    """
    if not model:
        return PRICING["gemini-3.5-flash"]
    return PRICING.get(model, PRICING["gemini-3.5-flash"])

def get_all_models() -> list[dict]:
    """Get list of all available models with their info."""
    return [
        {"id": model_id, **info}
        for model_id, info in PRICING.items()
    ]
