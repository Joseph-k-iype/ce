"""
Compliance Engine
==================
Scalable compliance engine for cross-border data transfer evaluation.

Features:
- Two sets of rules: Case-matching and Generic (Transfer + Attribute)
- AI-powered rule generation from natural language
- FalkorDB graph database for high-performance queries
- Configuration-driven extensibility
- RESTful API with FastAPI

Usage:
    from compliance_engine import run_server
    run_server()

Or from command line:
    python -m compliance_engine

Version: 5.0.0
"""

__version__ = "5.0.0"
__author__ = "Compliance Engine Team"

from api.main import app, run

__all__ = ["app", "run", "__version__"]
