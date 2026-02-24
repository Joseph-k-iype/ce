"""
Cypher Template Engine
======================
Loads and manages parameterized Cypher query templates from .cypher files.
Templates are loaded once at startup and cached for performance.

Usage:
    from services.cypher_templates import CypherTemplates
    templates = CypherTemplates()
    query = templates.get('all_rules')
"""

import os
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / 'cypher_templates'


class CypherTemplates:
    """Load and cache Cypher query templates from .cypher files."""

    _instance: Optional['CypherTemplates'] = None
    _cache: Dict[str, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_all()
        return cls._instance

    def _load_all(self):
        """Load all .cypher files from the templates directory."""
        if not _TEMPLATES_DIR.exists():
            logger.warning(f"Cypher templates directory not found: {_TEMPLATES_DIR}")
            return

        for cypher_file in _TEMPLATES_DIR.glob('*.cypher'):
            name = cypher_file.stem  # e.g., 'all_rules'
            try:
                content = cypher_file.read_text(encoding='utf-8').strip()
                # Strip comment lines at the top (// lines)
                lines = content.split('\n')
                query_lines = []
                in_header = True
                for line in lines:
                    stripped = line.strip()
                    if in_header and (stripped.startswith('//') or stripped == ''):
                        continue
                    in_header = False
                    query_lines.append(line)
                self._cache[name] = '\n'.join(query_lines)
                logger.info(f"Loaded Cypher template: {name} ({len(query_lines)} lines)")
            except Exception as e:
                logger.error(f"Failed to load Cypher template {cypher_file}: {e}")

    def get(self, name: str) -> str:
        """Get a Cypher query template by name.

        Args:
            name: Template name (without .cypher extension)

        Returns:
            The Cypher query string

        Raises:
            KeyError: If template not found
        """
        if name not in self._cache:
            raise KeyError(
                f"Cypher template '{name}' not found. "
                f"Available: {list(self._cache.keys())}"
            )
        return self._cache[name]

    def has(self, name: str) -> bool:
        """Check if a template exists."""
        return name in self._cache

    @property
    def available(self) -> list:
        """List all available template names."""
        return sorted(self._cache.keys())

    def reload(self):
        """Force reload all templates (useful for development)."""
        self._cache.clear()
        self._load_all()


# Module-level accessor
_templates: Optional[CypherTemplates] = None


def get_cypher_templates() -> CypherTemplates:
    """Get the singleton CypherTemplates instance."""
    global _templates
    if _templates is None:
        _templates = CypherTemplates()
    return _templates
