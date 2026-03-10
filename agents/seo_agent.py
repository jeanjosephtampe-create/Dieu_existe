"""
seo_agent.py — SEO Agent (bonus)
Analyse le référencement naturel du projet Jekyll :
meta tags, Schema.org, Core Web Vitals, contenu et maillage.
"""

import re
from pathlib import Path

from .base_agent import BaseAgent

# ------------------------------------------------------------------ #
#  Constantes                                                          #
# ------------------------------------------------------------------ #

SYSTEM_ROLE = """\
Tu es SEOExpert, spécialiste en référencement naturel (SEO) pour les sites web.
Tu analyses le HTML, la configuration Jekyll et les données structurées pour identifier
des améliorations SEO concrètes et mesurables.

Domaines couverts : meta tags, Schema.org, Core Web Vitals, contenu, liens, performance.
Réponds UNIQUEMENT avec un tableau JSON valide.
"""

SEO_PROMPT = """\
Analyse ce site web pour des améliorations SEO.

Site : dieu-preuves.fr (apologétique chrétienne, audience française)

=== HTML head (extrait) ===
```html
{head_html}
```

=== Configuration Jekyll (_config.yml) ===
```yaml
{config_yaml}
```

=== Contenu principal (extrait) ===
```html
{body_html}
```

Identifie les problèmes et opportunités SEO.

Chaque objet JSON doit avoir :
- "category"       : "meta" | "schema" | "content" | "performance" | "technical" | "links"
- "priority"       : "high" | "medium" | "low"
- "issue"          : description du problème
- "impact"         : impact estimé sur le classement
- "recommendation" : action concrète
- "example"        : exemple de code ou null

Tableau JSON :
"""

SCHEMA_PROMPT = """\
Analyse ces données structurées Schema.org et identifie les améliorations possibles.

```json
{schema}
```

Site : apologétique chrétienne (dieu-preuves.fr)

Propose des améliorations ou types Schema.org supplémentaires pertinents.
Tableau JSON (même format que précédemment) :
"""


class SEOAgent(BaseAgent):
    """
    Agent SEO — Analyse et recommandations pour le référencement naturel.
    """

    def __init__(self, model: str = "llama3.1:8b", max_llm_calls: int = -1):
        super().__init__(
            name="SEOExpert",
            role=SYSTEM_ROLE,
            model=model,
            max_llm_calls=max_llm_calls,
        )

    # ------------------------------------------------------------------ #
    #  Analyse statique SEO                                               #
    # ------------------------------------------------------------------ #

    def _check_static_seo(self, html: str, filename: str) -> list[dict]:
        """Vérifie les éléments SEO basiques par regex."""
        issues = []

        # Title
        title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
        if not title_m:
            issues.append({
                "category": "meta", "priority": "high",
                "issue": "Balise <title> manquante",
                "impact": "Critique : affiché dans les résultats Google",
                "recommendation": "Ajouter <title>Titre descriptif | Site</title>",
                "example": None, "source": "static", "file": filename,
            })
        elif title_m:
            title_len = len(title_m.group(1).strip())
            if title_len > 60:
                issues.append({
                    "category": "meta", "priority": "medium",
                    "issue": f"Title trop long ({title_len} caractères, max recommandé : 60)",
                    "impact": "Tronqué dans les SERPs Google",
                    "recommendation": f"Réduire le title à moins de 60 caractères",
                    "example": None, "source": "static", "file": filename,
                })
            elif title_len < 30:
                issues.append({
                    "category": "meta", "priority": "low",
                    "issue": f"Title trop court ({title_len} caractères, min recommandé : 30)",
                    "impact": "Manque de mots-clés, moins attractif",
                    "recommendation": "Enrichir le title avec des mots-clés pertinents",
                    "example": None, "source": "static", "file": filename,
                })

        # Description
        if not re.search(r'<meta[^>]+name=["\']description["\']', html, re.IGNORECASE):
            issues.append({
                "category": "meta", "priority": "high",
                "issue": "Meta description manquante",
                "impact": "Google affiche un extrait aléatoire, moins de clics",
                "recommendation": "Ajouter <meta name='description' content='...'> (150-160 chars)",
                "example": None, "source": "static", "file": filename,
            })

        # H1
        h1_matches = re.findall(r"<h1\b[^>]*>", html, re.IGNORECASE)
        if len(h1_matches) == 0:
            issues.append({
                "category": "content", "priority": "high",
                "issue": "Aucun H1 sur la page",
                "impact": "Signal de pertinence manquant pour Google",
                "recommendation": "Ajouter un H1 unique décrivant le sujet principal de la page",
                "example": None, "source": "static", "file": filename,
            })
        elif len(h1_matches) > 1:
            issues.append({
                "category": "content", "priority": "medium",
                "issue": f"{len(h1_matches)} balises H1 sur la même page",
                "impact": "Dilution du signal de pertinence principal",
                "recommendation": "Conserver un seul H1, convertir les autres en H2/H3",
                "example": None, "source": "static", "file": filename,
            })

        # Open Graph
        if not re.search(r'<meta[^>]+property=["\']og:', html, re.IGNORECASE):
            issues.append({
                "category": "meta", "priority": "medium",
                "issue": "Balises Open Graph manquantes",
                "impact": "Partage réseaux sociaux sans aperçu visuellement attractif",
                "recommendation": "Ajouter og:title, og:description, og:image, og:url",
                "example": '<meta property="og:title" content="Dieu Existe — Les Preuves">',
                "source": "static", "file": filename,
            })

        # Images sans alt
        img_without_alt = re.findall(r"<img\b(?![^>]*\balt\s*=)[^>]*>", html, re.IGNORECASE)
        if img_without_alt:
            issues.append({
                "category": "content", "priority": "medium",
                "issue": f"{len(img_without_alt)} image(s) sans attribut alt",
                "impact": "Non indexées par Google Images, pénalité accessibilité",
                "recommendation": "Ajouter alt avec mots-clés pertinents sur chaque image",
                "example": '<img src="cosmos.jpg" alt="Univers et big bang - preuve cosmologique">',
                "source": "static", "file": filename,
            })

        # Canonical
        if not re.search(r"<link[^>]+rel=['\"]canonical['\"]", html, re.IGNORECASE):
            issues.append({
                "category": "technical", "priority": "medium",
                "issue": "Balise canonical manquante",
                "impact": "Risque de contenu dupliqué dans l'index Google",
                "recommendation": "Ajouter <link rel='canonical' href='URL absolue'>",
                "example": '<link rel="canonical" href="https://dieu-preuves.fr/">',
                "source": "static", "file": filename,
            })

        return issues

    # ------------------------------------------------------------------ #
    #  Analyse LLM                                                        #
    # ------------------------------------------------------------------ #

    def _analyze_with_llm(self, head_html: str, config: str, body_html: str) -> list[dict]:
        """Analyse SEO sémantique par le LLM."""
        prompt = SEO_PROMPT.format(
            head_html=head_html[:2000],
            config_yaml=config[:1000],
            body_html=body_html[:2000],
        )
        result = self._chat_json(prompt)
        if not isinstance(result, list):
            return []
        for item in result:
            item.setdefault("source", "llm")
        return result

    def _analyze_schema(self, html: str) -> list[dict]:
        """Analyse les données structurées Schema.org."""
        schemas = re.findall(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html, re.DOTALL | re.IGNORECASE
        )
        if not schemas:
            return [{
                "category": "schema", "priority": "high",
                "issue": "Aucune donnée structurée Schema.org détectée",
                "impact": "Pas d'enrichissement (rich snippets) dans les SERPs",
                "recommendation": "Ajouter Schema.org WebSite, FAQPage ou Article",
                "example": None, "source": "static",
            }]

        combined_schema = "\n".join(schemas[:3])
        prompt = SCHEMA_PROMPT.format(schema=combined_schema[:3000])
        result = self._chat_json(prompt)
        if not isinstance(result, list):
            return []
        for item in result:
            item.setdefault("source", "llm")
        return result

    # ------------------------------------------------------------------ #
    #  Point d'entrée                                                     #
    # ------------------------------------------------------------------ #

    def run(self, project_path: Path) -> dict:
        """Lance l'analyse SEO complète."""
        print(f"\n{'='*50}")
        print(f"  Agent : {self.name}")
        print(f"  Rôle  : Analyse SEO et référencement")
        print(f"{'='*50}")

        all_issues: list[dict] = []

        # Lecture du layout principal
        layout_file = project_path / "_layouts" / "default.html"
        index_file = project_path / "index.html"
        config_file = project_path / "_config.yml"

        layout_html = self._read_file(layout_file, 6000) if layout_file.exists() else ""
        index_html = self._read_file(index_file, 6000) if index_file.exists() else ""
        config_yaml = self._read_file(config_file, 2000) if config_file.exists() else ""

        combined_html = layout_html + "\n" + index_html

        # Extraction du head
        head_match = re.search(r"<head[^>]*>(.*?)</head>", combined_html, re.DOTALL | re.IGNORECASE)
        head_html = head_match.group(1) if head_match else combined_html[:3000]

        body_match = re.search(r"<body[^>]*>(.*?)</body>", combined_html, re.DOTALL | re.IGNORECASE)
        body_html = body_match.group(1)[:3000] if body_match else combined_html[3000:6000]

        # 1. Analyse statique
        print("\n  [1/3] Analyse statique SEO...")
        static = self._check_static_seo(combined_html, "index.html + default.html")
        all_issues.extend(static)

        # 2. Analyse Schema.org
        print("  [2/3] Analyse données structurées Schema.org...")
        schema_issues = self._analyze_schema(combined_html)
        all_issues.extend(schema_issues)

        # 3. Analyse LLM
        print("  [3/3] Analyse sémantique LLM (SEO)...")
        llm_issues = self._analyze_with_llm(head_html, config_yaml, body_html)
        all_issues.extend(llm_issues)

        self.findings = all_issues

        # Stats
        by_priority: dict[str, list] = {"high": [], "medium": [], "low": []}
        by_category: dict[str, list] = {}
        for issue in all_issues:
            p = issue.get("priority", "low")
            if p in by_priority:
                by_priority[p].append(issue)
            c = issue.get("category", "other")
            by_category.setdefault(c, []).append(issue)

        print(f"\n  Résultat : {len(all_issues)} point(s) SEO")
        for p in ("high", "medium", "low"):
            if by_priority[p]:
                print(f"    • {p}: {len(by_priority[p])}")

        return {
            "agent": self.name,
            "total": len(all_issues),
            "by_priority": by_priority,
            "by_category": by_category,
            "all_issues": all_issues,
        }
