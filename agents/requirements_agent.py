"""
requirements_agent.py — Requirements Checker Agent
Lit REQUIREMENTS.md, vérifie chaque exigence contre le code réel,
et produit une matrice de conformité priorisée.

Deux niveaux d'analyse :
1. Statique : vérifications déterministes (présence de fichiers, patterns dans le code)
2. LLM     : vérification sémantique (l'exigence est-elle vraiment bien implémentée ?)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .base_agent import BaseAgent

# ------------------------------------------------------------------ #
#  Modèles de données                                                 #
# ------------------------------------------------------------------ #

class Status(str, Enum):
    MET       = "✅ Conforme"
    PARTIAL   = "⚠️  Partiel"
    MISSING   = "❌ Non conforme"
    UNKNOWN   = "❓ Non vérifié"
    DECLARED  = "📋 Déclaré fait"  # marqué [x] dans le fichier mais pas vérifié


@dataclass
class Requirement:
    """Représente une exigence extraite de REQUIREMENTS.md."""
    section: str          # ex: "2. SEO & Référencement"
    subsection: str       # ex: "2.1 Balises méta"
    text: str             # texte de l'exigence
    declared: bool        # True si marqué [x] dans le fichier
    status: Status = Status.UNKNOWN
    evidence: str = ""    # preuve de conformité ou d'absence
    notes: str = ""       # remarques supplémentaires

    @property
    def id(self) -> str:
        """Identifiant court pour les logs."""
        return self.text[:60].strip()


# ------------------------------------------------------------------ #
#  Vérificateurs statiques                                            #
# ------------------------------------------------------------------ #

class StaticChecker:
    """
    Ensemble de vérifications déterministes sur le projet.
    Chaque méthode retourne (Status, evidence: str).
    """

    def __init__(self, project: Path):
        self.project = project
        self._cache: dict[str, str] = {}  # path → contenu

    def _read(self, rel_path: str) -> str:
        if rel_path not in self._cache:
            p = self.project / rel_path
            self._cache[rel_path] = p.read_text("utf-8", errors="ignore") if p.exists() else ""
        return self._cache[rel_path]

    def _exists(self, rel_path: str) -> bool:
        return (self.project / rel_path).exists()

    def _contains(self, rel_path: str, pattern: str, flags: int = re.IGNORECASE) -> bool:
        return bool(re.search(pattern, self._read(rel_path), flags))

    def _grep(self, pattern: str, extensions: list[str], flags: int = re.IGNORECASE) -> list[str]:
        """Cherche un pattern dans tous les fichiers des extensions données."""
        matches = []
        for ext in extensions:
            for f in self.project.rglob(f"*{ext}"):
                if not BaseAgent._is_excluded(f):
                    content = self._cache.get(str(f.relative_to(self.project)), "")
                    if not content:
                        try:
                            content = f.read_text("utf-8", errors="ignore")
                            self._cache[str(f.relative_to(self.project))] = content
                        except Exception:
                            continue
                    if re.search(pattern, content, flags):
                        matches.append(str(f.relative_to(self.project)))
        return matches

    # ---------------------------------------------------------------- #
    #  Vérifications par exigence                                       #
    # ---------------------------------------------------------------- #

    CHECKS: dict[str, str] = {
        # clé = fragment de texte d'exigence (lowercase, partiel)
        # valeur = nom de méthode
        "image og créée": "check_og_image",
        "og-image.jpg":   "check_og_image",
        "gemfile présent": "check_gemfile",
        "robots.txt":      "check_robots_txt",
        "sitemap":         "check_sitemap",
        "lazy loading":    "check_lazy_loading",
        "preconnect":      "check_preconnect",
        "intersectionobserver": "check_intersection_observer",
        "vanilla js":      "check_vanilla_js",
        "fallback":        "check_fallback",
        "balise <title>":  "check_title_tag",
        "meta description": "check_meta_description",
        "open graph":      "check_og_tags",
        "twitter card":    "check_twitter_card",
        "lang=":           "check_lang",
        "canonical":       "check_canonical",
        "schema.org website": "check_schema_website",
        "schema.org faqpage": "check_schema_faqpage",
        "schema.org breadcrumb": "check_schema_breadcrumb",
        "navigation clavier": "check_keyboard_nav",
        "aria-label":      "check_aria_labels",
        "rel=\"noopener": "check_noopener",
        "nocookie":        "check_nocookie",
        "données séparées": "check_data_files",
        "composants réutilisables": "check_includes",
        "readme documenté": "check_readme",
        "escape":          "check_escape_key",
        "modale":          "check_modal",
        "menu mobile":     "check_mobile_menu",
        "barre de progression": "check_progress_bar",
        "navigation fixe": "check_sticky_nav",
        "kalam":           "check_content_kalam",
        "fine-tuning":     "check_content_finetuning",
        "bgv":             "check_content_bgv",
        "historicité":     "check_content_historicity",
        "résurrection":    "check_content_resurrection",
        "sources académiques": "check_academic_sources",
        "config.yml":      "check_config_yml",
        "_config.yml":     "check_config_yml",
        "github pages":    "check_github_pages",
        "jekyll":          "check_gemfile",
    }

    def check(self, req: Requirement) -> tuple[Status, str]:
        """Tente une vérification statique. Retourne (Status.UNKNOWN, "") si pas de checker."""
        text_lower = req.text.lower()
        for keyword, method_name in self.CHECKS.items():
            if keyword in text_lower:
                method = getattr(self, method_name, None)
                if method:
                    return method()
        return Status.UNKNOWN, ""

    # ---- Implémentations ---- #

    def check_og_image(self):
        if self._exists("assets/img/og-image.jpg") or self._exists("assets/img/og-image.png"):
            return Status.MET, "Fichier trouvé dans assets/img/"
        return Status.MISSING, "assets/img/og-image.jpg introuvable"

    def check_gemfile(self):
        if not self._exists("Gemfile"):
            return Status.MISSING, "Gemfile absent"
        content = self._read("Gemfile")
        plugins = ["jekyll-seo-tag", "jekyll-sitemap"]
        missing = [p for p in plugins if p not in content]
        if missing:
            return Status.PARTIAL, f"Gemfile présent mais manque : {', '.join(missing)}"
        return Status.MET, "Gemfile avec tous les plugins requis"

    def check_robots_txt(self):
        if self._exists("robots.txt"):
            return Status.MET, "robots.txt présent"
        return Status.MISSING, "robots.txt absent"

    def check_sitemap(self):
        has_plugin = self._contains("Gemfile", "jekyll-sitemap") or \
                     self._contains("_config.yml", "jekyll-sitemap")
        if has_plugin:
            return Status.MET, "Plugin jekyll-sitemap actif dans Gemfile/_config.yml"
        return Status.MISSING, "Plugin jekyll-sitemap non trouvé"

    def check_lazy_loading(self):
        if self._contains("assets/js/main.js", r"IntersectionObserver|lazy"):
            return Status.MET, "IntersectionObserver + lazy loading trouvés dans main.js"
        return Status.MISSING, "Lazy loading non trouvé dans main.js"

    def check_preconnect(self):
        layout = self._read("_layouts/default.html")
        if "rel=\"preconnect\"" in layout or "rel='preconnect'" in layout:
            return Status.MET, "Balises preconnect présentes dans default.html"
        return Status.MISSING, "Aucun preconnect dans le layout"

    def check_intersection_observer(self):
        if self._contains("assets/js/main.js", r"IntersectionObserver"):
            return Status.MET, "IntersectionObserver utilisé dans main.js"
        return Status.MISSING, "IntersectionObserver absent de main.js"

    def check_vanilla_js(self):
        # Pas d'import de framework dans le HTML/JS
        has_jquery = bool(self._grep(r"jquery|react|vue|angular", [".html", ".js"]))
        if not has_jquery:
            return Status.MET, "Aucun framework JS détecté — vanilla JS confirmé"
        return Status.PARTIAL, "Un framework JS externe détecté"

    def check_fallback(self):
        if self._contains("assets/js/main.js", r"else\s*\{|fallback|!.*IntersectionObserver"):
            return Status.MET, "Fallback trouvé dans main.js"
        return Status.PARTIAL, "Aucun fallback explicite détecté (à vérifier manuellement)"

    def check_title_tag(self):
        layout = self._read("_layouts/default.html")
        if re.search(r"<title|jekyll-seo-tag|{%-?\s*seo\s*-?%}", layout, re.IGNORECASE):
            return Status.MET, "Balise title ou jekyll-seo-tag dans default.html"
        return Status.MISSING, "Aucune balise title ni seo-tag dans le layout"

    def check_meta_description(self):
        has_seo = self._contains("_layouts/default.html", r"seo\s*-?%}|jekyll-seo")
        has_desc = self._contains("_config.yml", "description")
        if has_seo and has_desc:
            return Status.MET, "jekyll-seo-tag + description dans _config.yml"
        if has_desc:
            return Status.PARTIAL, "Description dans _config.yml mais vérifier le tag seo"
        return Status.MISSING, "Description absente de _config.yml"

    def check_og_tags(self):
        layout = self._read("_layouts/default.html")
        if "og:type" in layout or "og:title" in layout or "{%- seo" in layout:
            return Status.MET, "Open Graph via jekyll-seo-tag ou tags manuels"
        return Status.MISSING, "Balises OG non détectées dans le layout"

    def check_twitter_card(self):
        has_seo = self._contains("_layouts/default.html", r"seo|twitter")
        has_config = self._contains("_config.yml", "twitter")
        if has_config:
            return Status.MET, "Configuration Twitter dans _config.yml"
        return Status.PARTIAL, "Twitter Card : vérifier la config jekyll-seo-tag"

    def check_lang(self):
        layout = self._read("_layouts/default.html")
        config = self._read("_config.yml")
        if 'lang="fr"' in layout or "lang: fr" in config:
            return Status.MET, 'Attribut lang="fr" détecté'
        return Status.MISSING, "Attribut lang non défini"

    def check_canonical(self):
        layout = self._read("_layouts/default.html")
        if "canonical" in layout:
            return Status.MET, "Lien canonical dans le layout"
        return Status.MISSING, "Lien canonical absent du layout"

    def check_schema_website(self):
        combined = self._read("_layouts/default.html") + self._read("index.html")
        if '"@type": "WebSite"' in combined or '"WebSite"' in combined:
            return Status.MET, 'Schema.org WebSite trouvé'
        return Status.MISSING, "Schema.org WebSite absent"

    def check_schema_faqpage(self):
        combined = self._read("_layouts/default.html") + self._read("index.html")
        faq_items = combined.count('"@type": "Question"')
        if faq_items >= 5:
            return Status.MET, f"FAQPage avec {faq_items} questions"
        if faq_items > 0:
            return Status.PARTIAL, f"FAQPage avec seulement {faq_items} question(s) (min. 5)"
        return Status.MISSING, "Schema.org FAQPage absent"

    def check_schema_breadcrumb(self):
        combined = self._read("_layouts/default.html") + self._read("index.html")
        if "BreadcrumbList" in combined:
            return Status.MET, "Schema.org BreadcrumbList présent"
        return Status.MISSING, "Schema.org BreadcrumbList absent"

    def check_keyboard_nav(self):
        js = self._read("assets/js/main.js")
        has_keydown = "keydown" in js
        has_escape = "Escape" in js or "escape" in js.lower()
        if has_keydown and has_escape:
            return Status.MET, "Gestion clavier (keydown + Escape) dans main.js"
        if has_keydown:
            return Status.PARTIAL, "keydown trouvé mais vérifier la gestion complète"
        return Status.PARTIAL, "Navigation clavier à vérifier manuellement"

    def check_aria_labels(self):
        files = self._grep(r"aria-label|aria-expanded|aria-hidden", [".html"])
        if len(files) >= 3:
            return Status.MET, f"aria-label/expanded dans {len(files)} fichier(s) HTML"
        return Status.PARTIAL, "aria-labels présents mais couverture partielle"

    def check_noopener(self):
        # Vérifier que tous les target=_blank ont noopener
        files_with_blank = self._grep(r'target="_blank"', [".html"])
        files_without_noopener = self._grep(r'target="_blank"(?![^>]*noopener)', [".html"])
        if not files_with_blank:
            return Status.MET, "Aucun target=_blank trouvé"
        if not files_without_noopener:
            return Status.MET, "Tous les target=_blank ont rel=noopener"
        return Status.PARTIAL, f"target=_blank sans noopener dans : {', '.join(files_without_noopener)}"

    def check_nocookie(self):
        if self._grep(r"youtube-nocookie", [".html", ".js"]):
            return Status.MET, "youtube-nocookie.com utilisé"
        return Status.MISSING, "youtube-nocookie non trouvé (utilise youtube.com standard ?)"

    def check_data_files(self):
        data_dir = self.project / "_data"
        files = list(data_dir.glob("*.yml")) if data_dir.exists() else []
        if len(files) >= 4:
            names = [f.name for f in files]
            return Status.MET, f"_data/ avec {len(files)} fichiers : {', '.join(names)}"
        if files:
            return Status.PARTIAL, f"_data/ présent avec seulement {len(files)} fichier(s)"
        return Status.MISSING, "Dossier _data/ absent ou vide"

    def check_includes(self):
        inc_dir = self.project / "_includes"
        files = list(inc_dir.glob("*.html")) if inc_dir.exists() else []
        if len(files) >= 4:
            return Status.MET, f"_includes/ avec {len(files)} composants réutilisables"
        return Status.PARTIAL, f"_includes/ avec seulement {len(files)} fichier(s)"

    def check_readme(self):
        if self._exists("README.md") and len(self._read("README.md")) > 500:
            return Status.MET, "README.md présent et documenté"
        return Status.PARTIAL, "README.md absent ou trop court"

    def check_escape_key(self):
        if self._contains("assets/js/main.js", r"Escape|keydown"):
            return Status.MET, "Gestion de la touche Escape dans main.js"
        return Status.MISSING, "Escape key non gérée"

    def check_modal(self):
        has_html = bool(self._grep(r"modal|modale", [".html"]))
        has_js = self._contains("assets/js/main.js", r"modal|Modal")
        if has_html and has_js:
            return Status.MET, "Composant modal présent (HTML + JS)"
        return Status.PARTIAL, "Vérifier l'implémentation complète de la modale"

    def check_mobile_menu(self):
        has_html = bool(self._grep(r"mobile.nav|hamburger|menu.toggle", [".html"]))
        has_js = self._contains("assets/js/main.js", r"toggleMenu|mobile.nav|hamburger")
        if has_html or has_js:
            return Status.MET, "Menu mobile détecté (HTML/JS)"
        return Status.PARTIAL, "Menu mobile à vérifier manuellement"

    def check_progress_bar(self):
        if self._grep(r"progress.bar|progress_bar", [".html"]):
            return Status.MET, "Barre de progression présente dans le HTML"
        return Status.MISSING, "Barre de progression non trouvée"

    def check_sticky_nav(self):
        css = self._read("assets/css/main.css")
        if re.search(r"position\s*:\s*(?:sticky|fixed)", css):
            return Status.MET, "Navigation sticky/fixed dans main.css"
        return Status.PARTIAL, "Vérifier la navigation fixe dans le CSS"

    def check_content_kalam(self):
        if self._grep(r"kalam", [".html", ".yml"]):
            return Status.MET, "Argument de Kalam trouvé dans les fichiers de contenu"
        return Status.MISSING, "Argument de Kalam absent"

    def check_content_finetuning(self):
        if self._grep(r"fine.tun|r.glage.fin|constante|anthropi", [".html", ".yml"]):
            return Status.MET, "Contenu sur le fine-tuning trouvé"
        return Status.MISSING, "Fine-tuning non trouvé dans le contenu"

    def check_content_bgv(self):
        if self._grep(r"BGV|borde.guth|vilenkin", [".html", ".yml"], re.IGNORECASE):
            return Status.MET, "Théorème BGV trouvé dans le contenu"
        return Status.MISSING, "Théorème BGV absent du contenu"

    def check_content_historicity(self):
        if self._grep(r"histor|josèphe|tacite|flavius", [".html", ".yml"], re.IGNORECASE):
            return Status.MET, "Contenu sur l'historicité trouvé"
        return Status.MISSING, "Contenu sur l'historicité absent"

    def check_content_resurrection(self):
        if self._grep(r"r.surrection|pascal|licona|wright", [".html", ".yml"], re.IGNORECASE):
            return Status.MET, "Contenu sur la résurrection trouvé"
        return Status.MISSING, "Contenu sur la résurrection absent"

    def check_academic_sources(self):
        sources = self._read("_data/sources.yml")
        if len(sources) > 200 and re.search(r"Physical Review|Nature|Science|Cambridge|Oxford", sources):
            return Status.MET, "Sources académiques de qualité présentes dans _data/sources.yml"
        if sources:
            return Status.PARTIAL, "_data/sources.yml présent mais sources à enrichir"
        return Status.MISSING, "_data/sources.yml absent"

    def check_config_yml(self):
        config = self._read("_config.yml")
        required = ["title", "description", "url", "lang"]
        missing = [k for k in required if k not in config]
        if not missing:
            return Status.MET, f"_config.yml complet ({', '.join(required)})"
        return Status.PARTIAL, f"_config.yml manque : {', '.join(missing)}"

    def check_github_pages(self):
        if self._exists("Gemfile") and self._exists("_config.yml"):
            return Status.MET, "Structure Jekyll compatible GitHub Pages"
        return Status.PARTIAL, "Vérifier la compatibilité GitHub Pages"


# ------------------------------------------------------------------ #
#  Parser REQUIREMENTS.md                                             #
# ------------------------------------------------------------------ #

def parse_requirements(md_path: Path) -> list[Requirement]:
    """Parse REQUIREMENTS.md et extrait les exigences."""
    if not md_path.exists():
        return []

    content = md_path.read_text("utf-8", errors="ignore")
    requirements: list[Requirement] = []
    section = "Général"
    subsection = ""

    for line in content.splitlines():
        stripped = line.strip()

        # Section H2
        if stripped.startswith("## "):
            section = stripped[3:].strip()
            subsection = ""
            continue

        # Sous-section H3
        if stripped.startswith("### "):
            subsection = stripped[4:].strip()
            continue

        # Exigence cochée [x]
        m = re.match(r"-\s+\[([xX ])\]\s+(.+)", stripped)
        if m:
            declared = m.group(1).lower() == "x"
            text = m.group(2).strip()
            # Enlever les balises HTML et les commentaires
            text = re.sub(r"<[^>]+>", "", text).strip()
            if text:
                requirements.append(Requirement(
                    section=section,
                    subsection=subsection,
                    text=text,
                    declared=declared,
                ))

    return requirements


# ------------------------------------------------------------------ #
#  Agent principal                                                    #
# ------------------------------------------------------------------ #

SYSTEM_ROLE = """\
Tu es RequirementsChecker, expert en assurance qualité et conformité web.
Ta mission : vérifier si une exigence de projet est réellement implémentée dans le code fourni.

Réponds UNIQUEMENT avec un objet JSON ayant :
- "status"   : "met" | "partial" | "missing" | "unknown"
- "evidence" : phrase courte expliquant ton verdict (ce que tu as trouvé ou pas trouvé)
- "notes"    : recommandation actionable si partial ou missing (sinon "")
"""

VERIFY_PROMPT = """\
Exigence à vérifier : "{requirement}"

Extrait de code du projet (peut être tronqué) :
```
{code_sample}
```

Est-ce que cette exigence est satisfaite dans ce code ?
JSON :
"""


class RequirementsAgent(BaseAgent):
    """
    Agent Requirements Checker.
    Vérifie chaque exigence de REQUIREMENTS.md contre le code réel.
    Combine analyse statique (déterministe) + LLM (sémantique).
    """

    REQUIREMENTS_FILE = "REQUIREMENTS.md"

    def __init__(self, model: str = "llama3.1:8b", max_llm_calls: int = -1):
        super().__init__(
            name="RequirementsChecker",
            role=SYSTEM_ROLE,
            model=model,
            max_llm_calls=max_llm_calls,
        )
        self._checker: StaticChecker | None = None

    # ---------------------------------------------------------------- #
    #  Vérification LLM                                                #
    # ---------------------------------------------------------------- #

    def _verify_with_llm(self, req: Requirement, code_sample: str) -> tuple[Status, str, str]:
        """Vérifie une exigence avec le LLM. Retourne (status, evidence, notes)."""
        prompt = VERIFY_PROMPT.format(
            requirement=req.text,
            code_sample=code_sample[:3000],
        )
        result = self._chat_json(prompt, temperature=0.1)

        if not isinstance(result, dict):
            return Status.UNKNOWN, "LLM n'a pas retourné de JSON valide", ""

        status_map = {
            "met": Status.MET,
            "partial": Status.PARTIAL,
            "missing": Status.MISSING,
            "unknown": Status.UNKNOWN,
        }
        s = status_map.get(result.get("status", "unknown"), Status.UNKNOWN)
        evidence = result.get("evidence", "")
        notes = result.get("notes", "")
        return s, evidence, notes

    # ---------------------------------------------------------------- #
    #  Point d'entrée                                                  #
    # ---------------------------------------------------------------- #

    def run(self, project_path: Path) -> dict:
        print(f"\n{'='*50}")
        print(f"  Agent : {self.name}")
        print(f"  Rôle  : Conformité aux exigences projet")
        print(f"{'='*50}")

        req_file = project_path / self.REQUIREMENTS_FILE
        if not req_file.exists():
            print(f"  [ATTENTION] {self.REQUIREMENTS_FILE} introuvable.")
            print(f"  Crée ce fichier à la racine du projet pour définir tes exigences.")
            return {"agent": self.name, "error": f"{self.REQUIREMENTS_FILE} manquant", "requirements": []}

        requirements = parse_requirements(req_file)
        print(f"  Exigences lues : {len(requirements)}")

        self._checker = StaticChecker(project_path)

        # Préparer un échantillon de code global pour le LLM
        all_html = ""
        for f in list(project_path.rglob("*.html"))[:5]:
            if not BaseAgent._is_excluded(f):
                all_html += f.read_text("utf-8", errors="ignore")[:500] + "\n"

        all_code = all_html + "\n" + (project_path / "assets/js/main.js").read_text("utf-8", errors="ignore")[:2000]

        # Vérification de chaque exigence
        met = partial = missing = unknown = 0

        for i, req in enumerate(requirements, 1):
            # 1. Essayer la vérification statique
            static_status, static_evidence = self._checker.check(req)

            if static_status != Status.UNKNOWN:
                req.status = static_status
                req.evidence = static_evidence
            else:
                # 2. Vérification LLM pour les cas non gérés statiquement
                if len(req.text) > 10 and not self.llm_budget_exhausted:
                    llm_status, llm_evidence, llm_notes = self._verify_with_llm(req, all_code)
                    req.status = llm_status
                    req.evidence = llm_evidence
                    req.notes = llm_notes
                else:
                    # Budget épuisé ou exigence trop courte → fallback déclaratif
                    req.status = Status.DECLARED if req.declared else Status.UNKNOWN
                    req.evidence = "Marqué [x] dans REQUIREMENTS.md — vérification manuelle requise" if req.declared else "Non vérifié (budget LLM épuisé)"

            # Compteurs
            if req.status == Status.MET:
                met += 1
            elif req.status == Status.PARTIAL:
                partial += 1
            elif req.status == Status.MISSING:
                missing += 1
            else:
                unknown += 1

            icon = {"✅ Conforme": "✅", "⚠️  Partiel": "⚠️", "❌ Non conforme": "❌",
                    "❓ Non vérifié": "❓", "📋 Déclaré fait": "📋"}.get(req.status.value, "?")
            print(f"  [{i:02d}] {icon} {req.id}")

        self.findings = [
            {
                "section": r.section,
                "subsection": r.subsection,
                "text": r.text,
                "declared": r.declared,
                "status": r.status.value,
                "evidence": r.evidence,
                "notes": r.notes,
            }
            for r in requirements
        ]

        total = len(requirements)
        compliance_pct = round((met / total * 100) if total else 0)

        print(f"\n  Taux de conformité : {compliance_pct}% ({met}/{total})")
        print(f"    ✅ Conforme     : {met}")
        print(f"    ⚠️  Partiel      : {partial}")
        print(f"    ❌ Non conforme : {missing}")
        print(f"    ❓/📋 Autre     : {unknown}")

        # Grouper par section
        by_section: dict[str, list] = {}
        for req in requirements:
            key = f"{req.section} / {req.subsection}" if req.subsection else req.section
            by_section.setdefault(key, []).append({
                "text": req.text,
                "status": req.status.value,
                "evidence": req.evidence,
                "notes": req.notes,
                "declared": req.declared,
            })

        # Exigences manquantes en priorité
        missing_items = [r for r in requirements if r.status == Status.MISSING]
        partial_items = [r for r in requirements if r.status == Status.PARTIAL]

        return {
            "agent": self.name,
            "total": total,
            "met": met,
            "partial": partial,
            "missing": missing,
            "unknown": unknown,
            "compliance_pct": compliance_pct,
            "by_section": by_section,
            "missing_items": [{"text": r.text, "section": r.section, "evidence": r.evidence} for r in missing_items],
            "partial_items": [{"text": r.text, "section": r.section, "evidence": r.evidence, "notes": r.notes} for r in partial_items],
            "all_requirements": self.findings,
        }
