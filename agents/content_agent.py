"""
content_agent.py — Agent de construction de contenu pour dieu-preuves.fr.

Lit les données enrichies (videos_enriched.yml, arguments_enriched.yml)
et génère des includes Jekyll HTML améliorés avec citations réelles + timestamps.
Aussi : refactoring de index.html → _includes/ (opération one-shot statique).
"""

import re
import yaml
from pathlib import Path

from .base_agent import BaseAgent

SYSTEM_ROLE = """\
Tu es un expert en rédaction web apologétique chrétienne. Tu génères du HTML Jekyll propre,
sémantique et accessible. Ton style est rigoureux, sourcé, et élégant.
Tu utilises les variables CSS existantes (--accent, --bg, --surface, etc.).
Réponds UNIQUEMENT avec le code HTML demandé, sans markdown ni explication.
"""

VIDEO_SECTION_PROMPT = """\
Génère un bloc HTML Jekyll pour la section "Vidéos recommandées" du site dieu-preuves.fr.
Le site a un thème sombre (fond #0a0e1a, accent or #c9a84c, texte #e8e8f0).

Voici les vidéos disponibles avec leurs moments clés :
{videos_data}

Génère un bloc HTML avec :
1. Un titre de section h2
2. Pour chaque vidéo : une card avec thumbnail YouTube (lazy-load), titre, auteur
3. Des boutons "Aller à [MM:SS]" pour les 2-3 moments clés les plus importants de chaque vidéo
4. Chaque bouton ouvre la vidéo à ce timestamp exact (attribut data-video-id et data-start)

Le HTML doit utiliser les classes CSS existantes du site.
HTML uniquement, pas de <html>/<body>/<style>.
"""

ARGUMENT_SECTION_PROMPT = """\
Génère un bloc HTML Jekyll pour la section "{argument_name}" du site dieu-preuves.fr.
Thème sombre : fond #0a0e1a, accent or #c9a84c.

Argument : {argument_name}
Description : {argument_desc}

Citations disponibles depuis les vidéos :
{citations}

Génère un include HTML avec :
1. Titre h3 de l'argument
2. Explication courte (2-3 phrases) rigoureuse et sourcée
3. Une ou deux citations encadrées avec leur source (auteur, vidéo, timestamp)
4. Un bouton "Voir la vidéo" vers le timestamp précis (data-video-id, data-start)

Utilise des balises <blockquote> pour les citations avec <cite> pour la source.
HTML uniquement, propre et accessible (ARIA si nécessaire).
"""

ARGUMENT_DESCRIPTIONS = {
    "cosmologique": "L'univers a eu un début (théorème BGV). Tout ce qui commence d'exister a une cause. Donc l'univers a une cause — transcendante, nécessaire et sans commencement.",
    "fine-tuning": "Les constantes physiques de l'univers sont réglées avec une précision de 1 sur 10^123 (Penrose) pour permettre la vie. Cette improbabilité pointe vers un Concepteur.",
    "mathematiques": "L'univers obéit à des structures mathématiques précises découvertes avant toute observation (équation de Dirac, géométrie de Calabi-Yau). C'est une preuve d'ordre rationnel sous-jacent.",
    "moral": "Les valeurs morales objectives existent (tortures d'innocents = objectivement mal). Or sans Dieu, il n'y a pas de fondement à des valeurs transcendantes.",
    "historique": "Cinq faits historiques établis concernant la résurrection : mort par crucifixion, tombeau de Joseph vide, apparitions aux apôtres, transformation radicale des apôtres, témoignage des femmes (contre-intuitif).",
    "ontologique": "Si Dieu est défini comme l'être le plus grand concevable, il doit exister dans la réalité — car un être existant est plus grand qu'un être purement conceptuel (Anselme, Plantinga).",
}


def _load_yaml_safe(path: Path) -> dict | list | None:
    """Charge un fichier YAML sans crasher."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return yaml.safe_load(text)
    except Exception:
        return None


def _format_citations_for_prompt(citations: list[dict]) -> str:
    """Formate les citations pour les inclure dans un prompt."""
    lines = []
    for c in citations[:4]:
        speaker = c.get("speaker") or "Intervenant"
        ts = c.get("timestamp", "0:00")
        vid_id = c.get("video_id", "")
        quote = c.get("quote", "")
        lines.append(f'- [{ts}] {speaker} (youtube.com/watch?v={vid_id}&t={c.get("start", 0)}s) : "{quote}"')
    return "\n".join(lines) if lines else "Aucune citation disponible."


class ContentBuilderAgent(BaseAgent):
    """
    Agent qui génère les includes Jekyll HTML enrichis
    en utilisant les données extraites par TranscriptMinerAgent.
    """

    def __init__(self, model: str = "llama3.1:8b", max_llm_calls: int = -1):
        super().__init__(
            name="ContentBuilder",
            role=SYSTEM_ROLE,
            model=model,
            max_llm_calls=max_llm_calls,
        )

    # ------------------------------------------------------------------ #
    #  Refactoring statique : index.html → _includes/                     #
    # ------------------------------------------------------------------ #

    def _refactor_index_to_includes(self, project_path: Path) -> list[Path]:
        """
        Découpe index.html en includes Jekyll propres.
        Opération idempotente : skip si les includes existent déjà.
        """
        includes_dir = project_path / "_includes"
        index_path = project_path / "index.html"

        # Skip si déjà fait (vérifie l'existence de hero.html)
        if (includes_dir / "hero.html").exists():
            print("  [skip] _includes/hero.html existe déjà — refactoring déjà effectué")
            return []

        if not index_path.exists():
            return []

        html = index_path.read_text(encoding="utf-8", errors="ignore")
        generated = []

        # Sections à extraire via leurs marqueurs HTML
        sections = {
            "hero.html": self._extract_section(html, r'<section[^>]*class="[^"]*hero[^"]*"', "</section>"),
            "section-philosophie.html": self._extract_section(html, r'<section[^>]*id="philosophy"', "</section>"),
            "section-science.html": self._extract_section(html, r'<section[^>]*id="science"', "</section>"),
            "section-histoire.html": self._extract_section(html, r'<section[^>]*id="(?:history|histoire)"', "</section>"),
            "section-videos.html": self._extract_section(html, r'<section[^>]*id="videos"', "</section>"),
            "section-scientists.html": self._extract_section(html, r'<section[^>]*id="scientists"', "</section>"),
            "section-sources.html": self._extract_section(html, r'<section[^>]*id="sources"', "</section>"),
        }

        for filename, content in sections.items():
            if content:
                path = self._write_file(includes_dir / filename, content)
                generated.append(path)

        # Créer le nouveau index.html minimal si on a extrait au moins 3 sections
        if len(generated) >= 3:
            new_index = self._build_minimal_index(project_path)
            self._write_file(index_path, new_index)
            generated.append(index_path)

        return generated

    def _extract_section(self, html: str, start_pattern: str, end_tag: str) -> str:
        """Extrait une section HTML par son pattern d'ouverture."""
        m = re.search(start_pattern, html, re.IGNORECASE | re.DOTALL)
        if not m:
            return ""
        start = m.start()
        # Trouve la fermeture correspondante (gère l'imbrication)
        depth = 0
        tag_name = end_tag.strip("</ >")
        i = start
        while i < len(html):
            open_m = re.search(rf"<{tag_name}[\s>]", html[i:], re.IGNORECASE)
            close_m = re.search(rf"</{tag_name}>", html[i:], re.IGNORECASE)
            if not close_m:
                break
            if open_m and open_m.start() < close_m.start():
                depth += 1
                i += open_m.start() + 1
            else:
                if depth == 0:
                    end = i + close_m.end()
                    return html[start:end]
                depth -= 1
                i += close_m.start() + 1
        return ""

    def _build_minimal_index(self, project_path: Path) -> str:
        """Génère le index.html minimal qui inclut tous les includes."""
        layout_file = project_path / "_layouts" / "default.html"
        has_layout = layout_file.exists()

        front_matter = "---\nlayout: default\ntitle: Dieu Existe — Les Preuves\n---\n\n" if has_layout else ""

        includes = [
            "{% include nav.html %}",
            "{% include hero.html %}",
            "{% include section-philosophie.html %}",
            "{% include section-science.html %}",
            "{% include section-histoire.html %}",
            "{% include section-videos.html %}",
            "{% include section-scientists.html %}",
            "{% include section-sources.html %}",
            "{% include footer.html %}",
        ]
        # Filtre les includes dont le fichier n'existe pas encore
        existing = [
            inc for inc in includes
            if re.search(r"include (\S+\.html)", inc) and
            (project_path / "_includes" / re.search(r"include (\S+\.html)", inc).group(1)).exists()
        ]
        return front_matter + "\n".join(existing) + "\n"

    # ------------------------------------------------------------------ #
    #  Génération LLM des includes enrichis                               #
    # ------------------------------------------------------------------ #

    def _generate_videos_include(self, project_path: Path, videos_data: list) -> Path | None:
        """Génère _includes/section-videos-enriched.html via LLM."""
        if not videos_data or self.llm_budget_exhausted:
            return None

        # Résumé concis des vidéos pour le prompt
        summary_lines = []
        for v in videos_data[:5]:  # max 5 vidéos dans le prompt
            vid_id = v.get("video_id", "")
            title = v.get("title", "")[:50]
            moments = v.get("quotes", [])[:3]
            summary_lines.append(f"Vidéo {vid_id} — {title}")
            for m in moments:
                ts = m.get("timestamp_str", "0:00")
                quote = m.get("quote", "")[:80]
                summary_lines.append(f"  [{ts}] {quote}")

        prompt = VIDEO_SECTION_PROMPT.format(videos_data="\n".join(summary_lines))
        html_content = self._chat(prompt, temperature=0.1)

        if not html_content or len(html_content) < 50:
            return None

        path = project_path / "_includes" / "section-videos-enriched.html"
        self._write_file(path, html_content)
        return path

    def _generate_argument_include(
        self, project_path: Path, arg_key: str, citations: list
    ) -> Path | None:
        """Génère un include HTML enrichi pour un argument via LLM."""
        if self.llm_budget_exhausted:
            return None

        arg_name = arg_key.replace("-", " ").title()
        arg_desc = ARGUMENT_DESCRIPTIONS.get(arg_key, "")
        citations_text = _format_citations_for_prompt(citations)

        prompt = ARGUMENT_SECTION_PROMPT.format(
            argument_name=arg_name,
            argument_desc=arg_desc,
            citations=citations_text,
        )
        html_content = self._chat(prompt, temperature=0.15)

        if not html_content or len(html_content) < 50:
            return None

        filename = f"citation-{arg_key}.html"
        path = project_path / "_includes" / filename
        self._write_file(path, html_content)
        return path

    # ------------------------------------------------------------------ #
    #  Point d'entrée                                                     #
    # ------------------------------------------------------------------ #

    def run(self, project_path: Path) -> dict:
        print(f"\n{'='*50}")
        print(f"  Agent : {self.name}")
        print(f"  Rôle  : Construction des includes Jekyll enrichis")
        print(f"{'='*50}")

        generated = []
        pending = self.read_pending_tasks(project_path)
        pending_ids = {t["id"] for t in pending}

        # 1. Refactoring index.html → _includes/ (TASK-002, statique)
        if "TASK-002" in pending_ids:
            print("\n  [TASK-002] Refactoring index.html → _includes/...")
            new_files = self._refactor_index_to_includes(project_path)
            generated.extend(new_files)
            if new_files:
                self.mark_task_done(project_path, "TASK-002", self.name)

        # 2. Chargement des données enrichies par TranscriptMinerAgent
        data_dir = project_path / "_data"
        videos_enriched = _load_yaml_safe(data_dir / "videos_enriched.yml")
        args_enriched = _load_yaml_safe(data_dir / "arguments_enriched.yml")

        # 3. Génération include vidéos (TASK-008)
        if "TASK-008" in pending_ids and isinstance(videos_enriched, list):
            print("\n  [TASK-008] Génération section-videos-enriched.html...")
            f = self._generate_videos_include(project_path, videos_enriched)
            if f:
                generated.append(f)
                self.mark_task_done(project_path, "TASK-008", self.name)

        # 4. Génération includes citations par argument (TASK-003, 004, 005, 009)
        task_arg_map = {
            "TASK-003": "fine-tuning",
            "TASK-004": "historique",
            "TASK-005": "fine-tuning",  # aussi fine-tuning (Penrose)
            "TASK-009": "mathematiques",
        }
        if isinstance(args_enriched, dict):
            for task_id, arg_key in task_arg_map.items():
                if task_id not in pending_ids:
                    continue
                citations = args_enriched.get(arg_key, [])
                if not citations:
                    continue
                print(f"\n  [{task_id}] Génération citation-{arg_key}.html...")
                f = self._generate_argument_include(project_path, arg_key, citations)
                if f:
                    generated.append(f)
                    self.mark_task_done(project_path, task_id, self.name)

        # 5. Findings pour rapport
        self.findings = [{"file": str(f), "type": "generated"} for f in self.generated_files]

        print(f"\n  Résultat : {len(self.generated_files)} fichier(s) généré(s)/mis à jour")
        for f in self.generated_files:
            print(f"    • {f.name}")

        return {
            "agent": self.name,
            "total": len(self.generated_files),
            "generated_files": [str(f) for f in self.generated_files],
        }
