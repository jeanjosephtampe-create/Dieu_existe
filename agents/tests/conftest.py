"""conftest.py — Configuration pytest pour les agents Jekyll."""

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: tests d'intégration qui appellent vraiment Ollama (lents, ~30-120s)"
    )
