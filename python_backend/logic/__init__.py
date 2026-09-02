# SAFECAM Logic Package (Redirects to python_backend/ai modular package)
try:
    from ai.attack_engine import AttackEngine, AttackEngineResult as BullyingResult
except ImportError:
    from python_backend.ai.attack_engine import AttackEngine, AttackEngineResult as BullyingResult
