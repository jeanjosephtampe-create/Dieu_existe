"""
orchestrator.py — Orchestrateur de l'équipe d'agents
Coordonne tous les agents : analyse + construction + git push automatique.
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Literal

from .code_agent import CodeAgent
from .uiux_agent import UIUXAgent
from .seo_agent import SEOAgent
from .requirements_agent import RequirementsAgent
from .transcript_agent import TranscriptMinerAgent
from .content_agent import ContentBuilderAgent
from .base_agent import SPEED_PRESETS, estimate_duration

# ------------------------------------------------------------------ #
#  Types                                                              #
# ------------------------------------------------------------------ #

AgentName = Literal["code", "uiux", "seo", "req", "transcript", "content"]

AVAILABLE_AGENTS: dict[str, type] = {
    "transcript": TranscriptMinerAgent,
    "content": ContentBuilderAgent,
    "code": CodeAgent,
    "uiux": UIUXAgent,
    "seo": SEOAgent,
    "req": RequirementsAgent,
}

AGENT_LABELS = {
    "transcript": "TranscriptMiner — Citations & timestamps vidéo",
    "content": "ContentBuilder — Génération includes Jekyll",
    "code": "KeyCode — Qualité du code",
    "uiux": "UI/UX Designer — Expérience utilisateur",
    "seo": "SEO Expert — Référencement naturel",
    "req": "RequirementsChecker — Conformité aux exigences",
}


# ------------------------------------------------------------------ #
#  Orchestrateur                                                       #
# ------------------------------------------------------------------ #

class Orchestrator:
    """
    Orchestre l'équipe d'agents et consolide les résultats.

    Usage :
        orch = Orchestrator("/chemin/vers/projet", speed="normal")
        orch.run(agents=["code", "uiux", "seo", "req"])

    Modes de vitesse :
        "fast"   → analyse statique uniquement (~5-20s)
        "normal" → statique + LLM limité à 3 appels/agent (~2-5min)
        "deep"   → analyse complète sans limite (~10-25min)

    Override fin :
        max_llm_calls=N  → N appels LLM par agent, quel que soit le speed
    """

    def __init__(
        self,
        project_path: str | Path,
        model: str = "llama3.1:8b",
        speed: str = "normal",
        max_llm_calls: int | None = None,
        auto_push: bool = True,
    ):
        self.project_path = Path(project_path).resolve()
        self.model = model
        self.speed = speed if speed in SPEED_PRESETS else "normal"
        # max_llm_calls explicite prend la priorité sur le preset
        if max_llm_calls is not None:
            self.max_llm_calls = max_llm_calls
        else:
            self.max_llm_calls = SPEED_PRESETS[self.speed]["max_llm_calls"]
        self.auto_push = auto_push
        self.results: dict[str, dict] = {}
        self.started_at: datetime | None = None
        self.ended_at: datetime | None = None
        self._agent_summaries: list[str] = []
        self._generated_files: list[str] = []

        if not self.project_path.exists():
            raise FileNotFoundError(f"Projet introuvable : {self.project_path}")

    # ------------------------------------------------------------------ #
    #  Exécution                                                          #
    # ------------------------------------------------------------------ #

    def run(self, agents: list[AgentName] | None = None) -> str:
        """
        Lance les agents demandés (tous par défaut).
        Retourne le chemin vers le rapport généré.
        """
        self.started_at = datetime.now()
        agents = agents or list(AVAILABLE_AGENTS.keys())

        self._print_banner(agents)

        for name in agents:
            cls = AVAILABLE_AGENTS.get(name)
            if cls is None:
                print(f"  [SKIP] Agent inconnu : {name}")
                continue
            agent = cls(model=self.model, max_llm_calls=self.max_llm_calls)
            self.results[name] = agent.run(self.project_path)
            self._agent_summaries.append(agent.summary())
            # Collecte les fichiers générés
            if hasattr(agent, "generated_files"):
                self._generated_files.extend(str(f) for f in agent.generated_files)

        self.ended_at = datetime.now()

        report_content = self._build_report()
        report_path = self._save_report(report_content)
        self._print_summary(report_path)

        # Git push automatique
        if self.auto_push:
            self._git_push()

        return str(report_path)

    # ------------------------------------------------------------------ #
    #  Rapport Markdown                                                   #
    # ------------------------------------------------------------------ #

    def _build_report(self) -> str:
        """Construit le rapport Markdown consolidé."""
        duration = (self.ended_at - self.started_at).seconds if self.ended_at and self.started_at else 0
        lines: list[str] = []

        # En-tête
        lines += [
            "# Rapport d'amélioration — Jekyll Agent Team",
            "",
            f"> **Projet :** `{self.project_path.name}`  ",
            f"> **Généré le :** {self.started_at.strftime('%d/%m/%Y à %H:%M:%S')}  ",
            f"> **Durée :** {duration}s  ",
            f"> **LLM :** {self.model} (local, Ollama)  ",
            f"> **Mode :** {self.speed.upper()} — max {self.max_llm_calls if self.max_llm_calls >= 0 else '∞'} appel(s) LLM/agent  ",
            "",
            "---",
            "",
        ]

        # Résumé exécutif
        lines += ["## Résumé exécutif", ""]
        total_items = 0
        high_items = 0

        for name, result in self.results.items():
            if name == "req":
                continue  # géré séparément
            total = result.get("total_issues") or result.get("total") or 0
            total_items += total
            by_p = result.get("by_priority", {})
            high_items += len(by_p.get("high", []))

        req_result = self.results.get("req", {})
        compliance_pct = req_result.get("compliance_pct", "N/A")
        req_total = req_result.get("total", 0)
        req_met = req_result.get("met", 0)
        req_missing = req_result.get("missing", 0)

        lines += [
            f"| Métrique | Valeur |",
            f"|---|---|",
            f"| Agents exécutés | {len(self.results)} |",
            f"| Points qualité identifiés | {total_items} |",
            f"| Points priorité HAUTE | {high_items} |",
        ]
        if req_result:
            lines += [
                f"| Exigences vérifiées | {req_total} |",
                f"| Exigences conformes | {req_met} ✅ |",
                f"| Exigences manquantes | {req_missing} ❌ |",
                f"| **Taux de conformité** | **{compliance_pct}%** |",
            ]
        lines.append("")

        # Section par agent
        for name, result in self.results.items():
            label = AGENT_LABELS.get(name, name)
            lines += [f"---", "", f"## Agent : {label}", ""]

            if name == "code":
                lines += self._section_code(result)
            elif name == "uiux":
                lines += self._section_uiux(result)
            elif name == "seo":
                lines += self._section_seo(result)
            elif name == "req":
                lines += self._section_req(result)

        # Actions prioritaires consolidées (top 10)
        lines += ["---", "", "## Actions prioritaires (top 10)", ""]
        priority_actions = self._get_priority_actions(10)
        for i, action in enumerate(priority_actions, 1):
            lines += [
                f"### {i}. {action.get('what') or action.get('issue') or action.get('recommendation', 'N/A')}",
                "",
                f"- **Agent :** {action.get('_agent', 'N/A')}",
                f"- **Priorité :** {action.get('priority') or action.get('severity', 'N/A')}",
                f"- **Pourquoi :** {action.get('why') or action.get('impact', 'N/A')}",
                f"- **Action :** {action.get('fix') or action.get('recommendation', 'N/A')}",
                "",
            ]
            if action.get("code_fix") or action.get("fix") or action.get("example"):
                code = action.get("code_fix") or action.get("example")
                if code and len(str(code)) < 500:
                    lines += ["```", str(code), "```", ""]

        # JSON brut (optionnel pour debug)
        lines += ["---", "", "## Données brutes (JSON)", "", "```json"]
        try:
            lines.append(json.dumps(self.results, ensure_ascii=False, indent=2)[:8000])
        except Exception:
            lines.append("{}")
        lines += ["```", ""]

        return "\n".join(lines)

    def _section_code(self, result: dict) -> list[str]:
        lines = []
        files = result.get("files_analyzed", 0)
        total = result.get("total_issues", 0)
        counts = result.get("counts", {})

        lines += [
            f"**Fichiers analysés :** {files}  ",
            f"**Problèmes détectés :** {total}  ",
            "",
            "| Type | Nombre |",
            "|---|---|",
        ]
        for t, n in counts.items():
            if n:
                lines.append(f"| {t} | {n} |")
        lines.append("")

        by_file = result.get("by_file", {})
        for fname, issues in sorted(by_file.items()):
            lines += [f"### `{fname}`", ""]
            for issue in issues[:8]:  # max 8 par fichier
                sev = issue.get("severity", "?")
                what = issue.get("what", "Problème")
                fix = issue.get("fix", "")
                line_no = issue.get("line")
                loc = f"ligne {line_no}" if line_no else "général"
                lines.append(f"- **[{sev.upper()}]** {what} *({loc})*")
                if fix:
                    lines.append(f"  - *Fix :* `{fix[:120]}`")
            lines.append("")
        return lines

    def _section_uiux(self, result: dict) -> list[str]:
        lines = []
        total = result.get("total", 0)
        lines += [f"**Recommandations :** {total}  ", ""]

        by_priority = result.get("by_priority", {})
        for priority in ("high", "medium", "low"):
            recs = by_priority.get(priority, [])
            if not recs:
                continue
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "")
            lines += [f"### {emoji} Priorité {priority.upper()} ({len(recs)})", ""]
            for rec in recs[:6]:
                cat = rec.get("category", "?")
                issue = rec.get("issue", "?")
                reco = rec.get("recommendation", "")
                lines.append(f"- **[{cat}]** {issue}")
                if reco:
                    lines.append(f"  - *Action :* {reco}")
                code = rec.get("code_fix")
                if code and len(str(code)) < 200:
                    lines += [f"  ```css", f"  {code}", f"  ```"]
            lines.append("")
        return lines

    def _section_seo(self, result: dict) -> list[str]:
        lines = []
        total = result.get("total", 0)
        lines += [f"**Points SEO :** {total}  ", ""]

        by_priority = result.get("by_priority", {})
        for priority in ("high", "medium", "low"):
            issues = by_priority.get(priority, [])
            if not issues:
                continue
            emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "")
            lines += [f"### {emoji} Priorité {priority.upper()} ({len(issues)})", ""]
            for issue in issues[:6]:
                cat = issue.get("category", "?")
                desc = issue.get("issue", "?")
                impact = issue.get("impact", "")
                reco = issue.get("recommendation", "")
                lines.append(f"- **[{cat}]** {desc}")
                if impact:
                    lines.append(f"  - *Impact :* {impact}")
                if reco:
                    lines.append(f"  - *Action :* {reco}")
            lines.append("")
        return lines

    def _section_req(self, result: dict) -> list[str]:
        lines = []
        total = result.get("total", 0)
        met = result.get("met", 0)
        missing = result.get("missing", 0)
        partial = result.get("partial", 0)
        pct = result.get("compliance_pct", 0)

        if result.get("error"):
            lines += [f"> ⚠️ {result['error']}", ""]
            return lines

        lines += [
            f"**Exigences vérifiées :** {total}  ",
            f"**Taux de conformité :** {pct}%  ",
            "",
            "| Statut | Nombre |",
            "|---|---|",
            f"| ✅ Conforme | {met} |",
            f"| ⚠️ Partiel | {partial} |",
            f"| ❌ Non conforme | {missing} |",
            "",
        ]

        # Exigences manquantes en premier
        missing_items = result.get("missing_items", [])
        if missing_items:
            lines += ["### ❌ Exigences non satisfaites", ""]
            for item in missing_items:
                text = item.get("text", "?")
                evidence = item.get("evidence", "")
                section = item.get("section", "")
                lines.append(f"- **{text}**")
                if section:
                    lines.append(f"  - *Section :* {section}")
                if evidence:
                    lines.append(f"  - *Constat :* {evidence}")
            lines.append("")

        partial_items = result.get("partial_items", [])
        if partial_items:
            lines += ["### ⚠️ Exigences partiellement satisfaites", ""]
            for item in partial_items:
                text = item.get("text", "?")
                evidence = item.get("evidence", "")
                notes = item.get("notes", "")
                lines.append(f"- **{text}**")
                if evidence:
                    lines.append(f"  - *Constat :* {evidence}")
                if notes:
                    lines.append(f"  - *Action :* {notes}")
            lines.append("")

        # Matrice complète par section
        lines += ["### Matrice de conformité complète", ""]
        by_section = result.get("by_section", {})
        for section_name, items in by_section.items():
            lines += [f"**{section_name}**", ""]
            for item in items:
                status = item.get("status", "❓ Non vérifié")
                text = item.get("text", "?")
                lines.append(f"- {status} — {text}")
            lines.append("")

        return lines

    # ------------------------------------------------------------------ #
    #  Actions prioritaires cross-agent                                   #
    # ------------------------------------------------------------------ #

    def _get_priority_actions(self, top_n: int = 10) -> list[dict]:
        """Collecte les actions haute priorité de tous les agents."""
        actions: list[dict] = []
        priority_order = {"high": 0, "medium": 1, "low": 2}

        for name, result in self.results.items():
            # Code agent
            if name == "code":
                for issue in result.get("all_issues", []):
                    sev = issue.get("severity", "low")
                    if sev in ("high", "medium"):
                        item = dict(issue)
                        item["_agent"] = AGENT_LABELS.get(name, name)
                        item["priority"] = sev
                        actions.append(item)

            # UIUX + SEO agents
            for key in ("all_recommendations", "all_issues"):
                for item in result.get(key, []):
                    p = item.get("priority", "low")
                    if p in ("high", "medium"):
                        enriched = dict(item)
                        enriched["_agent"] = AGENT_LABELS.get(name, name)
                        actions.append(enriched)

        # Trier : high avant medium
        actions.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 2))
        return actions[:top_n]

    # ------------------------------------------------------------------ #
    #  Sauvegarde                                                         #
    # ------------------------------------------------------------------ #

    def _save_report(self, content: str) -> Path:
        """Sauvegarde le rapport dans agents/reports/."""
        reports_dir = self.project_path / "agents" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        timestamp = self.started_at.strftime("%Y%m%d_%H%M%S")
        report_path = reports_dir / f"rapport_{timestamp}.md"
        report_path.write_text(content, encoding="utf-8")
        return report_path

    # ------------------------------------------------------------------ #
    #  Git push automatique                                               #
    # ------------------------------------------------------------------ #

    def _git_push(self) -> None:
        """Committe les modifications et pousse sur une branche improvements/."""
        ts = self.started_at.strftime("%Y%m%d-%H%M%S")
        branch = f"improvements/{ts}"

        # Vérifie qu'on est bien dans un repo git
        check = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=self.project_path,
            capture_output=True,
            text=True,
        )
        if check.returncode != 0:
            print("\n  [GIT] Pas de dépôt git — push ignoré.")
            return

        # Vérifie s'il y a des changements à committer
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.project_path,
            capture_output=True,
            text=True,
        )
        if not status.stdout.strip():
            print("\n  [GIT] Aucun changement à committer.")
            return

        print(f"\n  [GIT] Création branche : {branch}")
        try:
            steps = [
                ["git", "checkout", "-b", branch],
                ["git", "add", "-A", "--",
                 ":!agents/reports/", ":!agents/__pycache__/", ":!__pycache__/"],
                ["git", "commit", "-m",
                 f"agents: amélioration automatique {self.started_at.strftime('%Y-%m-%d %H:%M')} [{', '.join(self.results.keys())}]"],
                ["git", "push", "-u", "origin", branch],
            ]
            for cmd in steps:
                result = subprocess.run(
                    cmd, cwd=self.project_path,
                    capture_output=True, text=True,
                )
                if result.returncode != 0:
                    # git add avec pathspec négatif échoue parfois — fallback
                    if "add" in cmd and result.returncode != 0:
                        subprocess.run(
                            ["git", "add", "_data/", "_includes/", "MASTER_PROMPT.md",
                             "REQUIREMENTS.md", "agents/memory/"],
                            cwd=self.project_path, check=False,
                        )
                        subprocess.run(
                            ["git", "commit", "-m",
                             f"agents: amélioration automatique {self.started_at.strftime('%Y-%m-%d %H:%M')}"],
                            cwd=self.project_path, check=False,
                        )
                        subprocess.run(
                            ["git", "push", "-u", "origin", branch],
                            cwd=self.project_path, check=False,
                        )
                        break
                    print(f"  [GIT] Erreur : {result.stderr.strip()}")
                    return
            print(f"  [GIT] ✓ Poussé sur origin/{branch}")
        except Exception as e:
            print(f"  [GIT] Erreur inattendue : {e}")

    # ------------------------------------------------------------------ #
    #  Affichage                                                          #
    # ------------------------------------------------------------------ #

    def _print_banner(self, agents: list[str]) -> None:
        preset = SPEED_PRESETS[self.speed]
        calls_label = str(self.max_llm_calls) if self.max_llm_calls >= 0 else "illimité"
        estimated = estimate_duration(self.speed, agents)

        print("\n" + "=" * 60)
        print("   JEKYLL AGENT TEAM — Amélioration automatique")
        print("=" * 60)
        print(f"  Projet    : {self.project_path}")
        print(f"  LLM       : {self.model} (Ollama local)")
        print(f"  Agents    : {', '.join(agents)}")
        print(f"  Mode      : {self.speed.upper()} — {preset['label']}")
        print(f"  Max appels: {calls_label} par agent")
        print(f"  Durée est.: {estimated}")
        print("=" * 60)

    def _print_summary(self, report_path: Path) -> None:
        duration = (self.ended_at - self.started_at).seconds
        total_calls = sum(
            int(s.split("appel")[0].split("—")[-1].strip())
            for s in self._agent_summaries
            if "appel" in s
        )
        print(f"\n{'='*60}")
        print(f"  TERMINÉ en {duration}s  (estimé : {estimate_duration(self.speed, list(self.results.keys()))})")
        print(f"  Appels LLM réels : {total_calls} au total")
        for s in self._agent_summaries:
            print(f"    • {s}")
        print(f"  Rapport : {report_path}")
        print("=" * 60)
        print("\nOuvre le rapport avec :")
        print(f"  start {report_path}")
