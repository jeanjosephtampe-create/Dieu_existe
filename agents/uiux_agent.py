"""
uiux_agent.py — UI/UX Agent
Analyse l'interface et l'expérience utilisateur du projet Jekyll.
Couvre : accessibilité, hiérarchie visuelle, responsive, interactions, performance.
"""

import re
from pathlib import Path

from .base_agent import BaseAgent

# ------------------------------------------------------------------ #
#  Constantes                                                          #
# ------------------------------------------------------------------ #

MAX_HTML_CHARS = 4000
MAX_CSS_CHARS = 4000

SYSTEM_ROLE = """\
Tu es UXDesigner, expert en UI/UX web, accessibilité WCAG 2.1 et design responsive.
Ta mission : analyser le code HTML et CSS pour identifier des problèmes d'expérience utilisateur
et proposer des améliorations concrètes et actionables.

Catégories :
- "accessibility" : WCAG, ARIA, contraste, navigation clavier, lecteurs d'écran
- "visual"        : hiérarchie, typographie, espacement, cohérence visuelle
- "responsive"    : adaptation mobile, breakpoints, tailles tactiles
- "interaction"   : états hover/focus/active, feedback utilisateur, micro-interactions
- "performance"   : animations coûteuses, layout thrashing, chargement perçu

Réponds UNIQUEMENT avec un tableau JSON valide.
"""

UX_PROMPT = """\
Analyse l'interface de ce site web (apologétique chrétienne en français).

=== HTML (extrait) ===
```html
{html}
```

=== CSS (extrait) ===
```css
{css}
```

Identifie les problèmes UI/UX les plus importants.

Chaque objet du tableau JSON doit avoir :
- "category"        : "accessibility" | "visual" | "responsive" | "interaction" | "performance"
- "priority"        : "high" | "medium" | "low"
- "element"         : sélecteur CSS ou nom de composant concerné
- "issue"           : description du problème
- "impact"          : qui est impacté et comment
- "recommendation"  : action concrète à effectuer
- "code_fix"        : exemple CSS ou HTML de correction (optionnel, string ou null)

Tableau JSON uniquement :
"""

COMPONENT_PROMPT = """\
Évalue ce composant HTML spécifique pour l'UX.

Composant : {component_name}
```html
{html}
```

Donne des recommandations UI/UX spécifiques à ce composant.
Chaque objet JSON :
- "category" : catégorie UX
- "priority" : "high" | "medium" | "low"
- "issue" : problème identifié
- "recommendation" : amélioration concrète
- "code_fix" : exemple de code ou null

Tableau JSON :
"""


class UIUXAgent(BaseAgent):
    """
    Agent UI/UX — Analyse et amélioration de l'interface utilisateur.

    Analyse statique des patterns d'accessibilité + analyse sémantique LLM
    pour produire des recommandations UX priorisées.
    """

    def __init__(self, model: str = "llama3.1:8b", max_llm_calls: int = -1):
        super().__init__(
            name="UXDesigner",
            role=SYSTEM_ROLE,
            model=model,
            max_llm_calls=max_llm_calls,
        )

    # ------------------------------------------------------------------ #
    #  Analyse statique d'accessibilité                                   #
    # ------------------------------------------------------------------ #

    def _check_static_a11y(self, html: str, filename: str) -> list[dict]:
        """Vérifie les patterns d'accessibilité par regex."""
        issues = []
        lines = html.splitlines()

        for i, line in enumerate(lines, 1):
            # Bouton sans texte ni aria-label
            if re.search(r"<button\b[^>]*>(\s*|<[^>]+>)*</button>", line, re.IGNORECASE):
                issues.append({
                    "category": "accessibility", "priority": "high",
                    "element": "button", "file": filename, "line": i,
                    "issue": "Bouton sans texte visible ni aria-label",
                    "impact": "Incompréhensible pour les lecteurs d'écran et la navigation clavier",
                    "recommendation": "Ajouter un texte ou aria-label décrivant l'action",
                    "code_fix": '<button aria-label="Fermer la modale">×</button>',
                    "source": "static",
                })

            # Link sans texte (lien icône)
            if re.search(r"<a\b[^>]*>\s*</a>", line, re.IGNORECASE):
                issues.append({
                    "category": "accessibility", "priority": "high",
                    "element": "a", "file": filename, "line": i,
                    "issue": "Lien vide sans texte ni aria-label",
                    "impact": "Non accessible aux lecteurs d'écran",
                    "recommendation": 'Ajouter aria-label ou span.sr-only avec texte descriptif',
                    "code_fix": None,
                    "source": "static",
                })

            # tabindex positif (anti-pattern)
            m = re.search(r'tabindex\s*=\s*"([1-9]\d*)"', line)
            if m:
                issues.append({
                    "category": "accessibility", "priority": "medium",
                    "element": "tabindex", "file": filename, "line": i,
                    "issue": f"tabindex={m.group(1)} perturbe l'ordre de navigation clavier",
                    "impact": "Navigation clavier confuse, particulièrement pour les utilisateurs de lecteurs d'écran",
                    "recommendation": "Utiliser tabindex=0 ou -1 uniquement. Revoir l'ordre du DOM.",
                    "code_fix": None,
                    "source": "static",
                })

            # Input sans label associé
            if re.search(r"<input\b(?![^>]*\baria-label)", line, re.IGNORECASE):
                if not re.search(r'type\s*=\s*"(?:hidden|submit|button|reset)"', line, re.IGNORECASE):
                    issues.append({
                        "category": "accessibility", "priority": "high",
                        "element": "input", "file": filename, "line": i,
                        "issue": "Input sans aria-label ni label associé visible",
                        "impact": "Incompréhensible pour les lecteurs d'écran",
                        "recommendation": "Ajouter <label for='id'> ou aria-label",
                        "code_fix": None,
                        "source": "static",
                    })

        return issues

    def _check_static_css(self, css: str, filename: str) -> list[dict]:
        """Vérifie les patterns CSS problématiques pour l'UX."""
        issues = []

        # Pas de :focus visible
        has_focus = ":focus" in css
        has_focus_visible = ":focus-visible" in css
        if not has_focus and not has_focus_visible:
            issues.append({
                "category": "accessibility", "priority": "high",
                "element": ":focus / :focus-visible", "file": filename, "line": None,
                "issue": "Aucun style :focus ou :focus-visible défini",
                "impact": "Navigation clavier invisible pour les utilisateurs qui n'utilisent pas la souris",
                "recommendation": "Ajouter :focus-visible { outline: 2px solid #accent; outline-offset: 2px; }",
                "code_fix": ":focus-visible { outline: 2px solid var(--accent, #4f8ef7); outline-offset: 3px; }",
                "source": "static",
            })

        # Transition sur all (performance)
        if re.search(r"transition\s*:\s*all\b", css):
            issues.append({
                "category": "performance", "priority": "medium",
                "element": "transition: all", "file": filename, "line": None,
                "issue": "Utilisation de 'transition: all' au lieu de propriétés spécifiques",
                "impact": "Déclenche des recalculs de layout inutiles, janks sur appareils bas de gamme",
                "recommendation": "Spécifier uniquement les propriétés animées (ex: transform, opacity)",
                "code_fix": "transition: transform 0.2s ease, opacity 0.2s ease;",
                "source": "static",
            })

        # Pas de media query mobile détectée
        if "@media" not in css:
            issues.append({
                "category": "responsive", "priority": "high",
                "element": "@media", "file": filename, "line": None,
                "issue": "Aucune media query détectée",
                "impact": "Le site peut être inutilisable sur mobile (40-60% du trafic web)",
                "recommendation": "Ajouter des breakpoints pour mobile (max-width: 768px) et tablette",
                "code_fix": "@media (max-width: 768px) { /* styles mobiles */ }",
                "source": "static",
            })

        # Taille de clic trop petite (boutons < 44px recommandé par WCAG)
        for m in re.finditer(r"(button|\.btn|\.cta)[^{]*\{[^}]*height\s*:\s*(\d+)px", css, re.DOTALL):
            size = int(m.group(2))
            if size < 44:
                issues.append({
                    "category": "responsive", "priority": "medium",
                    "element": m.group(1), "file": filename, "line": None,
                    "issue": f"Zone de clic trop petite : {size}px (WCAG recommande ≥44px)",
                    "impact": "Difficile à tapper sur mobile / pour les utilisateurs avec tremblements",
                    "recommendation": "Augmenter la taille minimale à 44×44px (peut utiliser padding)",
                    "code_fix": f"min-height: 44px; padding: 0.75rem 1.25rem;",
                    "source": "static",
                })

        return issues

    # ------------------------------------------------------------------ #
    #  Analyse LLM                                                        #
    # ------------------------------------------------------------------ #

    def _analyze_global(self, html: str, css: str) -> list[dict]:
        """Analyse globale HTML+CSS par le LLM."""
        prompt = UX_PROMPT.format(html=html[:MAX_HTML_CHARS], css=css[:MAX_CSS_CHARS])
        result = self._chat_json(prompt)
        if not isinstance(result, list):
            return []
        for item in result:
            item.setdefault("source", "llm")
        return result

    def _analyze_component(self, name: str, html: str) -> list[dict]:
        """Analyse un composant spécifique."""
        if not html.strip():
            return []
        prompt = COMPONENT_PROMPT.format(component_name=name, html=html[:2000])
        result = self._chat_json(prompt)
        if not isinstance(result, list):
            return []
        for item in result:
            item.setdefault("source", "llm")
            item.setdefault("element", name)
        return result

    # ------------------------------------------------------------------ #
    #  Point d'entrée                                                     #
    # ------------------------------------------------------------------ #

    def run(self, project_path: Path) -> dict:
        """Lance l'analyse UI/UX complète."""
        print(f"\n{'='*50}")
        print(f"  Agent : {self.name}")
        print(f"  Rôle  : Analyse UI/UX et accessibilité")
        print(f"{'='*50}")

        # Lecture des fichiers
        html_parts: list[str] = []
        components: dict[str, str] = {}

        for html_file in sorted(project_path.rglob("*.html")):
            if self._is_excluded(html_file):
                continue
            rel = html_file.relative_to(project_path)
            print(f"  → HTML: {rel}")
            content = self._read_file(html_file, 3000)
            html_parts.append(f"<!-- {rel} -->\n{content}")

            # Extraire les composants _includes
            if "_includes" in str(html_file):
                components[html_file.stem] = content

        css_content = ""
        for css_file in sorted(project_path.rglob("*.css")):
            if self._is_excluded(css_file):
                continue
            rel = css_file.relative_to(project_path)
            print(f"  → CSS : {rel}")
            css_content = self._read_file(css_file, MAX_CSS_CHARS)
            break  # On prend le premier CSS principal

        combined_html = "\n\n".join(html_parts)

        all_recs: list[dict] = []

        # 1. Analyse statique d'accessibilité
        print("\n  [1/3] Analyse statique accessibilité...")
        for html_file in project_path.rglob("*.html"):
            if not self._is_excluded(html_file):
                content = self._read_file(html_file)
                static_a11y = self._check_static_a11y(content, html_file.name)
                all_recs.extend(static_a11y)

        # 2. Analyse statique CSS
        print("  [2/3] Analyse statique CSS...")
        if css_content:
            css_issues = self._check_static_css(css_content, "main.css")
            all_recs.extend(css_issues)

        # 3. Analyse LLM globale
        print("  [3/3] Analyse sémantique LLM (UX/design)...")
        llm_global = self._analyze_global(combined_html, css_content)
        all_recs.extend(llm_global)

        # Analyse des composants clés par le LLM
        key_components = ["nav", "footer", "arg-card", "video-card"]
        for comp_name in key_components:
            if comp_name in components:
                print(f"  → Composant : {comp_name}")
                comp_recs = self._analyze_component(comp_name, components[comp_name])
                all_recs.extend(comp_recs)

        self.findings = all_recs

        # Organisation par priorité
        by_priority: dict[str, list] = {"high": [], "medium": [], "low": []}
        by_category: dict[str, list] = {}
        for rec in all_recs:
            p = rec.get("priority", "low")
            if p in by_priority:
                by_priority[p].append(rec)
            c = rec.get("category", "other")
            by_category.setdefault(c, []).append(rec)

        print(f"\n  Résultat : {len(all_recs)} recommandation(s)")
        for p in ("high", "medium", "low"):
            if by_priority[p]:
                print(f"    • {p}: {len(by_priority[p])}")

        return {
            "agent": self.name,
            "total": len(all_recs),
            "by_priority": by_priority,
            "by_category": by_category,
            "all_recommendations": all_recs,
        }
