"""
main.py — Point d'entrée CLI pour l'équipe d'agents Jekyll.

Utilisation :
    python -m agents.main                            # Tous les agents, mode normal
    python -m agents.main --speed fast               # Analyse statique uniquement (~10s)
    python -m agents.main --speed deep               # Analyse complète (~15-30min)
    python -m agents.main --max-calls 5              # 5 appels LLM par agent max
    python -m agents.main --agents code uiux         # Agents spécifiques
    python -m agents.main --model llama3.1:8b        # Modèle personnalisé

Depuis la racine du projet Jekyll :
    python -m agents.main
"""

import argparse
import sys
from pathlib import Path

# Chemin par défaut = dossier parent du dossier agents/
DEFAULT_PROJECT = Path(__file__).parent.parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="jekyll-agents",
        description="Équipe d'agents IA pour améliorer un projet Jekyll (100% local via Ollama).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Agents disponibles :
  code   — KeyCode : qualité du code HTML/CSS/JS/YAML
  uiux   — UI/UX Designer : accessibilité, design, responsive
  seo    — SEO Expert : référencement, meta tags, Schema.org
  req    — RequirementsChecker : conformité aux exigences (REQUIREMENTS.md)

Modes de vitesse :
  fast   — Analyse statique uniquement, 0 appel LLM        (~5-20s)
  normal — Statique + LLM limité à 3 appels/agent          (~2-5min) [défaut]
  deep   — Analyse complète, appels LLM illimités           (~10-25min)

Exemples :
  python -m agents.main                          # tout, mode normal
  python -m agents.main --speed fast             # résultat instantané
  python -m agents.main --speed deep             # analyse maximale
  python -m agents.main --max-calls 10           # 10 appels LLM/agent
  python -m agents.main --agents code --speed fast
  python -m agents.main --agents req             # seulement les exigences
        """,
    )

    parser.add_argument(
        "--project",
        type=Path,
        default=DEFAULT_PROJECT,
        metavar="CHEMIN",
        help=f"Chemin vers le projet Jekyll (défaut : {DEFAULT_PROJECT})",
    )
    parser.add_argument(
        "--agents",
        nargs="+",
        choices=["code", "uiux", "seo", "req"],
        default=["code", "uiux", "seo", "req"],
        metavar="AGENT",
        help="Agents à exécuter : code, uiux, seo, req (défaut : tous)",
    )
    parser.add_argument(
        "--speed",
        choices=["fast", "normal", "deep"],
        default="normal",
        help="Vitesse d'exécution : fast (~10s) | normal (~3min) | deep (~20min) [défaut: normal]",
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=None,
        metavar="N",
        dest="max_calls",
        help="Nombre max d'appels LLM par agent (écrase --speed). -1 = illimité",
    )
    parser.add_argument(
        "--model",
        default="llama3.1:8b",
        metavar="MODELE",
        help="Modèle Ollama à utiliser (défaut : llama3.1:8b)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Lister les agents disponibles et quitter",
    )

    return parser.parse_args()


def check_ollama(model: str, speed: str) -> bool:
    """Vérifie que Ollama est disponible (sauf en mode fast qui n'en a pas besoin)."""
    if speed == "fast":
        return True  # mode fast = 0 appel LLM, pas besoin d'Ollama

    try:
        import ollama
        models = ollama.list()
        model_names = [m.model for m in models.models]
        base = model.split(":")[0]
        found = any(base in name for name in model_names)
        if not found:
            print(f"  [ATTENTION] Modèle '{model}' non trouvé dans Ollama.")
            print(f"  Modèles disponibles : {', '.join(model_names)}")
            print(f"  Pour installer : ollama pull {model}")
            return False
        return True
    except Exception as e:
        print(f"  [ERREUR] Ollama non accessible : {e}")
        print("  Vérifie que Ollama est lancé : ollama serve")
        print("  Astuce : utilise --speed fast pour analyser sans LLM")
        return False


def main() -> int:
    from .base_agent import SPEED_PRESETS, estimate_duration

    args = parse_args()

    # --list
    if args.list:
        print("\nAgents disponibles :")
        print("  code  — KeyCode : révision qualité HTML/CSS/JS/YAML")
        print("  uiux  — UI/UX Designer : accessibilité, design, responsive")
        print("  seo   — SEO Expert : référencement, meta tags, Schema.org")
        print("  req   — RequirementsChecker : conformité aux exigences (REQUIREMENTS.md)")
        print("\nModes de vitesse :")
        for name, preset in SPEED_PRESETS.items():
            lo, hi = preset["estimated_seconds"]
            calls = preset["max_llm_calls"]
            calls_str = "illimité" if calls < 0 else str(calls)
            print(f"  {name:<8} {preset['label']}")
            print(f"           Max appels : {calls_str}/agent  |  Durée estimée : {lo//60}m–{hi//60}m")
        return 0

    # Résolution du max_calls final
    speed = args.speed
    max_calls_override = args.max_calls

    # Affichage du plan
    preset = SPEED_PRESETS[speed]
    effective_max = max_calls_override if max_calls_override is not None else preset["max_llm_calls"]
    estimated = estimate_duration(speed, args.agents)
    if max_calls_override is not None:
        effective_estimated = f"variable (max {effective_max} appels/agent)"
    else:
        effective_estimated = estimated

    print(f"\n  Projet    : {args.project}")
    print(f"  LLM       : {args.model}")
    print(f"  Agents    : {', '.join(args.agents)}")
    print(f"  Mode      : {speed.upper()} — {preset['label']}")
    print(f"  Max appels: {effective_max if effective_max >= 0 else 'illimité'} par agent")
    print(f"  Durée est.: {effective_estimated}")

    # Vérification Ollama (inutile en mode fast)
    if effective_max != 0:
        print("\n  Vérification d'Ollama...")
        if not check_ollama(args.model, speed):
            print("\n  Abandon. Corrige le problème Ollama ou utilise --speed fast.")
            return 1
        print("  OK — Ollama opérationnel")
    else:
        print("\n  Mode fast : Ollama non requis (0 appel LLM)")

    # Import et lancement de l'orchestrateur
    from .orchestrator import Orchestrator

    try:
        orch = Orchestrator(
            project_path=args.project,
            model=args.model,
            speed=speed,
            max_llm_calls=max_calls_override,
        )
        report_path = orch.run(agents=args.agents)
        print(f"\n  Rapport disponible : {report_path}")
        return 0
    except FileNotFoundError as e:
        print(f"\n  [ERREUR] {e}")
        return 1
    except KeyboardInterrupt:
        print("\n\n  Interruption par l'utilisateur.")
        return 130
    except Exception as e:
        print(f"\n  [ERREUR INATTENDUE] {e}")
        raise


if __name__ == "__main__":
    sys.exit(main())
