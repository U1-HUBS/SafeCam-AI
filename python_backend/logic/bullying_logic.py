"""
SAFECAM — Bullying Logic (Deprecation Redirect)
================================================
This module has been refactored into the modular `python_backend/ai/` package.
Redirecting imports to `python_backend.ai.attack_engine`.
"""

try:
    from ai.attack_engine import AttackEngine as BullyingStateMachine, AttackEngineResult as BullyingResult
except ImportError:
    from python_backend.ai.attack_engine import AttackEngine as BullyingStateMachine, AttackEngineResult as BullyingResult
