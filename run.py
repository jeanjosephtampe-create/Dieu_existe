"""
run.py — Script de lancement des agents Jekyll depuis n'importe quel répertoire.

Usage (depuis n'importe où) :
    python run.py                        # Tous les agents, mode normal
    python run.py --speed fast           # Analyse statique seulement (~10s)
    python run.py --speed deep           # Analyse complète (~15-30min)
    python run.py --max-calls 5          # 5 appels LLM par agent max
    python run.py --agents code uiux     # Agents spécifiques
    python run.py --list                 # Lister les agents disponibles
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

result = subprocess.run(
    [sys.executable, "-m", "agents.main"] + sys.argv[1:],
    cwd=PROJECT_ROOT,
)
sys.exit(result.returncode)
