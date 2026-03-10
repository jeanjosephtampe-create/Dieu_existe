"""
code_agent.py — KeyCode Agent
Analyse la qualité du code HTML, CSS, JS et YAML du projet Jekyll.
Détecte les bugs, anti-patterns, problèmes d'accessibilité et de performance.
"""

import re
from pathlib import Path

from .base_agent import BaseAgent

# ------------------------------------------------------------------ #
#  Constantes                                                          #
# ------------------------------------------------------------------ #

EXTENSIONS = {
    ".html": "HTML/Liquid",
    ".css": "CSS",
    ".js": "JavaScript",
    ".yml": "YAML",
    ".yaml": "YAML",
}

MAX_CHARS_PER_FILE = 4500

SYSTEM_ROLE = """\
Tu es CodeReviewer, expert en développement web (HTML5, CSS3, JavaScript, Jekyll/Liquid).
Ta mission : détecter les problèmes réels dans le code fourni.

Catégories de problèmes :
- "bug"        : erreur qui casse le comportement attendu
- "warning"    : code qui fonctionne mais est risqué ou fragile
- "improvement": bonne pratique non respectée, optimisation possible
- "a11y"       : accessibilité (ARIA, contraste, navigation clavier)

Pour chaque problème, donne un exemple de correction concret.
Réponds UNIQUEMENT avec un tableau JSON valide. Si aucun problème, réponds [].
"""

ANALYSIS_PROMPT = """\
Analyse ce fichier {lang} pour trouver des problèmes de qualité de code.

Fichier : {filename}
```{ext}
{content}
```

Réponds avec un tableau JSON. Chaque objet doit avoir :
- "type"       : "bug" | "warning" | "improvement" | "a11y"
- "severity"   : "high" | "medium" | "low"
- "line"       : numéro de ligne approximatif (entier ou null)
- "what"       : description courte du problème
- "why"        : explication de l'impact
- "fix"        : correction suggérée (code si possible)

Tableau JSON uniquement :
"""


class CodeAgent(BaseAgent):
    """
    Agent KeyCode — Révision de la qualité du code.

    Combine une analyse statique (regex) rapide + analyse sémantique LLM
    pour donner des recommandations actionables.
    """

    def __init__(self, model: str = "llama3.1:8b", max_llm_calls: int = -1):
        super().__init__(
            name="CodeReviewer",
            role=SYSTEM_ROLE,
            model=model,
            max_llm_calls=max_llm_calls,
        )
        self._static_issues: list[dict] = []

    # ------------------------------------------------------------------ #
    #  Analyse statique (sans LLM)                                        #
    # ------------------------------------------------------------------ #

    def _static_html(self, content: str, filename: str) -> list[dict]:
        """Détecte les problèmes HTML courants par regex."""
        issues = []
        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            # img sans alt
            if re.search(r"<img\b(?![^>]*\balt\s*=)", line, re.IGNORECASE):
                issues.append({
                    "type": "a11y", "severity": "high",
                    "line": i, "file": filename,
                    "what": "Attribut alt manquant sur <img>",
                    "why": "Les lecteurs d'écran ne peuvent pas décrire l'image",
                    "fix": 'Ajouter alt="description de l\'image"',
                    "source": "static",
                })

            # onclick inline (mauvaise pratique)
            if re.search(r'\bonclick\s*=\s*"[^"]*"', line) and "return false" not in line:
                issues.append({
                    "type": "warning", "severity": "low",
                    "line": i, "file": filename,
                    "what": "Handler onclick inline",
                    "why": "Difficile à maintenir et tester, préférer addEventListener",
                    "fix": "Déplacer le handler dans main.js avec addEventListener",
                    "source": "static",
                })

            # target="_blank" sans rel="noopener"
            if re.search(r'target="_blank"', line) and "noopener" not in line:
                issues.append({
                    "type": "warning", "severity": "medium",
                    "line": i, "file": filename,
                    "what": 'target="_blank" sans rel="noopener noreferrer"',
                    "why": "Faille de sécurité (tabnapping) et fuite d'informations",
                    "fix": 'Ajouter rel="noopener noreferrer"',
                    "source": "static",
                })

        return issues

    def _static_css(self, content: str, filename: str) -> list[dict]:
        """Détecte les problèmes CSS courants."""
        issues = []
        lines = content.splitlines()
        important_count = 0

        for i, line in enumerate(lines, 1):
            if "!important" in line:
                important_count += 1
            # px sur font-size (accessibilité zoom navigateur)
            if re.search(r"\bfont-size\s*:\s*\d+px\b", line):
                issues.append({
                    "type": "a11y", "severity": "medium",
                    "line": i, "file": filename,
                    "what": "font-size en px bloque le zoom navigateur",
                    "why": "Les utilisateurs avec besoin d'accessibilité ne peuvent pas zoomer le texte",
                    "fix": "Utiliser rem ou em à la place (ex: 1rem = 16px)",
                    "source": "static",
                })

        if important_count >= 5:
            issues.append({
                "type": "warning", "severity": "medium",
                "line": None, "file": filename,
                "what": f"{important_count} occurrences de !important",
                "why": "Surcharge la cascade CSS et rend le code fragile",
                "fix": "Augmenter la spécificité des sélecteurs ou revoir l'architecture CSS",
                "source": "static",
            })

        return issues

    def _static_js(self, content: str, filename: str) -> list[dict]:
        """Détecte les problèmes JS courants."""
        issues = []
        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # var au lieu de let/const
            if re.match(r"^\s*var\s+\w+", line):
                issues.append({
                    "type": "improvement", "severity": "low",
                    "line": i, "file": filename,
                    "what": "Utilisation de var au lieu de let/const",
                    "why": "var a une portée de fonction et peut causer des bugs subtils",
                    "fix": "Remplacer par const (valeur fixe) ou let (valeur variable)",
                    "source": "static",
                })

            # innerHTML (risque XSS)
            if "innerHTML" in stripped and "=" in stripped and not stripped.startswith("//"):
                issues.append({
                    "type": "warning", "severity": "medium",
                    "line": i, "file": filename,
                    "what": "Utilisation de innerHTML pour insérer du contenu",
                    "why": "Risque XSS si le contenu vient d'une source externe",
                    "fix": "Si données externes: utiliser textContent ou DOMParser. Si HTML statique: acceptable.",
                    "source": "static",
                })

        return issues

    def _run_static_analysis(self, path: Path, content: str) -> list[dict]:
        """Dispatch vers l'analyseur statique selon l'extension."""
        ext = path.suffix.lower()
        fname = path.name
        if ext == ".html":
            return self._static_html(content, fname)
        if ext == ".css":
            return self._static_css(content, fname)
        if ext == ".js":
            return self._static_js(content, fname)
        return []

    # ------------------------------------------------------------------ #
    #  Analyse LLM                                                        #
    # ------------------------------------------------------------------ #

    def _analyze_with_llm(self, path: Path, content: str) -> list[dict]:
        """Envoie le fichier au LLM pour analyse sémantique."""
        ext = path.suffix.lower()
        lang = EXTENSIONS.get(ext, ext[1:].upper())

        prompt = ANALYSIS_PROMPT.format(
            lang=lang,
            filename=path.name,
            ext=ext[1:],
            content=content,
        )

        result = self._chat_json(prompt)
        if not isinstance(result, list):
            return []

        # Enrichir chaque issue avec le nom du fichier
        for item in result:
            item.setdefault("file", path.name)
            item.setdefault("source", "llm")

        return result

    # ------------------------------------------------------------------ #
    #  Point d'entrée                                                     #
    # ------------------------------------------------------------------ #

    def run(self, project_path: Path) -> dict:
        """Lance l'analyse complète du projet."""
        print(f"\n{'='*50}")
        print(f"  Agent : {self.name}")
        print(f"  Rôle  : Révision qualité du code (KeyCode)")
        print(f"{'='*50}")

        # Collecte des fichiers
        files: list[Path] = []
        for ext in EXTENSIONS:
            for f in project_path.rglob(f"*{ext}"):
                if not self._is_excluded(f):
                    files.append(f)

        print(f"  Fichiers à analyser : {len(files)}")

        all_issues: list[dict] = []
        by_file: dict[str, list] = {}

        for f in sorted(files):
            rel = str(f.relative_to(project_path))
            print(f"  → {rel}")
            content = self._read_file(f, MAX_CHARS_PER_FILE)
            if not content.strip():
                continue

            # Analyse statique (rapide, pas de LLM)
            static = self._run_static_analysis(f, content)

            # Analyse LLM (sémantique)
            llm = self._analyze_with_llm(f, content)

            file_issues = static + llm
            if file_issues:
                all_issues.extend(file_issues)
                by_file[rel] = file_issues

        self.findings = all_issues

        # Statistiques
        counts = {"bug": 0, "warning": 0, "improvement": 0, "a11y": 0}
        for issue in all_issues:
            t = issue.get("type", "improvement")
            if t in counts:
                counts[t] += 1

        print(f"\n  Résultat : {len(all_issues)} problème(s) détecté(s)")
        for k, v in counts.items():
            if v > 0:
                print(f"    • {k}: {v}")

        return {
            "agent": self.name,
            "files_analyzed": len(files),
            "total_issues": len(all_issues),
            "counts": counts,
            "by_file": by_file,
            "all_issues": all_issues,
        }
