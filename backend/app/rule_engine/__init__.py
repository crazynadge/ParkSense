"""Deterministic rule engine. Must never import from app.vision."""
from app.rule_engine.engine import evaluate

__all__ = ["evaluate"]
