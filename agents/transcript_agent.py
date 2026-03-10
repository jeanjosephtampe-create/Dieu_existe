"""
transcript_agent.py — Agent d'extraction de citations depuis les transcripts vidéo.

Lit les fichiers NoteGPT_TRANSCRIPT_*.txt, extrait les citations clés avec timestamps,
et enrichit _data/videos.yml et _data/arguments.yml avec des données précises.
"""

import re
import yaml
from pathlib import Path

from .base_agent import BaseAgent

# ------------------------------------------------------------------ #
#  Mapping vidéo → ID YouTube                                         #
# ------------------------------------------------------------------ #

VIDEO_ID_MAP = {
    "Bonnassies": "ZWzys1gojtA",
    "Guénolé": "ZWzys1gojtA",
    "Lennox": "otrqzITuSqE",
    "God DOES": "otrqzITuSqE",
    "Lavagna": "fYgRGBczRHk",
    "Paul-Adrien": "fYgRGBczRHk",
    "Raffray": "7IA4XriGeZY",
    "prouve l": "7IA4XriGeZY",
    "100 fois": "ZiNRN20tEQI",
    "Catho": "ZiNRN20tEQI",
    "Jésus": "UnaAFhybsDk",
    "ONFRAY": "UnaAFhybsDk",
    "Mathematics": "TSZXlVF-qVI",
    "Willie": "TSZXlVF-qVI",
    "Soon": "TSZXlVF-qVI",
}

ARGUMENT_KEYWORDS = {
    "cosmologique": ["kalam", "cosmolog", "contingence", "raison suffisante", "cause", "infini", "hilbert", "bgv", "borde", "guth", "vilenkin"],
    "fine-tuning": ["réglage fin", "fine-tuning", "constante", "10^123", "penrose", "probabilité", "univers", "calibrage"],
    "mathematiques": ["mathémat", "dirac", "calabi", "équation", "géométrie", "science", "unreasonable"],
    "moral": ["moral", "objectif", "éthique", "bien", "mal", "dieu moral"],
    "historique": ["résurrection", "jésus", "historique", "vide", "apôtre", "tacite", "josèphe", "croix", "crucifi"],
    "ontologique": ["ontologique", "anselme", "plantinga", "être parfait", "définition"],
}

SYSTEM_ROLE = """\
Tu es un expert en apologétique chrétienne. Tu analyses des transcripts de vidéos YouTube
pour extraire les citations les plus percutantes avec leurs timestamps exacts.
Réponds UNIQUEMENT avec un tableau JSON valide.
"""

EXTRACT_PROMPT = """\
Voici un extrait de transcript vidéo (apologétique chrétienne) :

=== TRANSCRIPT ===
{transcript}
==================

Vidéo : {title}

Extrais les 5 à 8 citations les plus percutantes et rigoureuses de ce transcript.
Pour chaque citation, retourne un objet JSON avec :
- "timestamp_str" : le timestamp tel qu'il apparaît dans le transcript (ex: "0:03:19")
- "timestamp_sec" : le timestamp converti en secondes (entier)
- "speaker"       : le nom du locuteur si identifiable, sinon null
- "quote"         : la citation exacte en français (traduis si en anglais), max 120 caractères
- "quote_original": la citation originale si en anglais, sinon null
- "argument"      : catégorie parmi "cosmologique" | "fine-tuning" | "mathematiques" | "moral" | "historique" | "ontologique" | "autre"

Tableau JSON :
"""


def _ts_to_sec(ts: str) -> int:
    """Convertit MM:SS ou H:MM:SS en secondes."""
    parts = ts.strip().split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        pass
    return 0


def _static_extract(text: str, max_quotes: int = 6) -> list[dict]:
    """Extraction statique : cherche des timestamps + phrases clés sans LLM."""
    quotes = []
    # Timestamps format 0:00:00 ou 00:00
    ts_pattern = re.compile(r"\b(\d{1,2}:\d{2}(?::\d{2})?)\b")
    sentences = re.split(r"[.!?]\s+", text)

    for sent in sentences:
        m = ts_pattern.search(sent)
        if not m:
            continue
        ts_str = m.group(1)
        ts_sec = _ts_to_sec(ts_str)
        # Phrase sans le timestamp
        quote = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", "", sent).strip()
        quote = re.sub(r"\s+", " ", quote)[:120]
        if len(quote) < 20:
            continue

        # Catégorie par mots-clés
        arg = "autre"
        lower = quote.lower()
        for cat, kws in ARGUMENT_KEYWORDS.items():
            if any(kw in lower for kw in kws):
                arg = cat
                break

        quotes.append({
            "timestamp_str": ts_str,
            "timestamp_sec": ts_sec,
            "speaker": None,
            "quote": quote,
            "quote_original": None,
            "argument": arg,
        })
        if len(quotes) >= max_quotes:
            break

    return quotes


def _guess_video_id(filename: str) -> str | None:
    """Devine l'ID YouTube depuis le nom de fichier du transcript."""
    for keyword, vid_id in VIDEO_ID_MAP.items():
        if keyword.lower() in filename.lower():
            return vid_id
    return None


class TranscriptMinerAgent(BaseAgent):
    """
    Agent qui lit les transcripts vidéo et enrichit les données YAML
    avec des citations précises et des timestamps exploitables.
    """

    def __init__(
        self,
        model: str = "llama3.1:8b",
        max_llm_calls: int = -1,
        transcripts_path: Path | None = None,
    ):
        super().__init__(
            name="TranscriptMiner",
            role=SYSTEM_ROLE,
            model=model,
            max_llm_calls=max_llm_calls,
        )
        self.transcripts_path = transcripts_path  # résolu dans run()

    # ------------------------------------------------------------------ #
    #  Lecture des transcripts                                             #
    # ------------------------------------------------------------------ #

    def _find_transcripts(self, project_path: Path) -> list[Path]:
        """Trouve les fichiers NoteGPT_TRANSCRIPT_*.txt."""
        # D'abord chemin explicite, sinon dossier parent du projet
        base = self.transcripts_path or project_path.parent
        found = list(base.glob("NoteGPT_TRANSCRIPT_*.txt"))
        if not found:
            # Cherche aussi dans le projet lui-même
            found = list(project_path.glob("**/NoteGPT_TRANSCRIPT_*.txt"))
        return found

    def _process_transcript(self, path: Path) -> dict:
        """Traite un transcript et retourne les citations extraites."""
        filename = path.stem
        vid_id = _guess_video_id(filename)
        # Titre lisible depuis le nom de fichier
        title = re.sub(r"^NoteGPT_TRANSCRIPT_", "", filename).strip()

        # Lecture (les transcripts peuvent être longs → 12 000 chars max)
        full_text = self._read_file(path, max_chars=12000)

        # Extraction statique (toujours)
        static_quotes = _static_extract(full_text)

        # Extraction LLM si budget disponible
        llm_quotes = []
        if not self.llm_budget_exhausted and full_text:
            # Utilise le milieu du transcript (souvent le plus riche)
            excerpt = full_text[2000:6000] if len(full_text) > 6000 else full_text
            prompt = EXTRACT_PROMPT.format(transcript=excerpt, title=title)
            result = self._chat_json(prompt)
            if isinstance(result, list):
                for item in result:
                    if not isinstance(item, dict):
                        continue
                    # Normalise timestamp_sec
                    if "timestamp_str" in item and "timestamp_sec" not in item:
                        item["timestamp_sec"] = _ts_to_sec(item.get("timestamp_str", "0:00"))
                    elif "timestamp_sec" not in item:
                        item["timestamp_sec"] = 0
                    llm_quotes.append(item)

        # Fusion : LLM en priorité, statique en complément
        quotes = llm_quotes if llm_quotes else static_quotes
        # Dédoublonnage par timestamp_sec
        seen: set[int] = set()
        unique = []
        for q in quotes:
            sec = q.get("timestamp_sec", 0)
            if sec not in seen:
                seen.add(sec)
                unique.append(q)

        return {
            "video_id": vid_id,
            "title": title,
            "filename": path.name,
            "quotes": unique[:8],  # max 8 par vidéo
        }

    # ------------------------------------------------------------------ #
    #  Génération des fichiers YAML enrichis                              #
    # ------------------------------------------------------------------ #

    def _build_videos_enriched(self, results: list[dict]) -> str:
        """Génère le contenu YAML pour videos_enriched.yml."""
        lines = ["# videos_enriched.yml — Généré automatiquement par TranscriptMinerAgent",
                 "# Timestamps et citations extraits des transcripts NoteGPT",
                 ""]
        for r in results:
            vid_id = r["video_id"] or "UNKNOWN"
            lines.append(f"- id: {vid_id}")
            lines.append(f"  title: \"{r['title'][:80]}\"")
            lines.append(f"  source_file: \"{r['filename']}\"")
            lines.append("  moments:")
            for q in r["quotes"]:
                ts_str = q.get("timestamp_str", "0:00")
                ts_sec = q.get("timestamp_sec", 0)
                quote = q.get("quote", "")[:120].replace('"', "'")
                speaker = q.get("speaker") or ""
                arg = q.get("argument", "autre")
                lines.append(f"    - timestamp: \"{ts_str}\"")
                lines.append(f"      start: {ts_sec}")
                lines.append(f"      argument: {arg}")
                if speaker:
                    lines.append(f"      speaker: \"{speaker}\"")
                lines.append(f"      quote: \"{quote}\"")
            lines.append("")
        return "\n".join(lines)

    def _build_arguments_enriched(self, results: list[dict]) -> str:
        """Génère citations groupées par catégorie d'argument."""
        by_arg: dict[str, list] = {}
        for r in results:
            for q in r["quotes"]:
                arg = q.get("argument", "autre")
                by_arg.setdefault(arg, []).append({
                    "video_id": r["video_id"],
                    "video_title": r["title"][:60],
                    **q,
                })

        lines = ["# arguments_enriched.yml — Généré automatiquement par TranscriptMinerAgent",
                 "# Citations groupées par argument apologétique",
                 ""]
        for arg, citations in sorted(by_arg.items()):
            lines.append(f"{arg}:")
            for c in citations[:5]:  # max 5 citations par argument
                ts_str = c.get("timestamp_str", "0:00")
                ts_sec = c.get("timestamp_sec", 0)
                vid_id = c.get("video_id") or "UNKNOWN"
                quote = c.get("quote", "")[:120].replace('"', "'")
                speaker = c.get("speaker") or ""
                lines.append(f"  - video_id: {vid_id}")
                lines.append(f"    timestamp: \"{ts_str}\"")
                lines.append(f"    start: {ts_sec}")
                if speaker:
                    lines.append(f"    speaker: \"{speaker}\"")
                lines.append(f"    quote: \"{quote}\"")
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Point d'entrée                                                     #
    # ------------------------------------------------------------------ #

    def run(self, project_path: Path) -> dict:
        print(f"\n{'='*50}")
        print(f"  Agent : {self.name}")
        print(f"  Rôle  : Extraction citations + timestamps des transcripts")
        print(f"{'='*50}")

        # 1. Tâches prioritaires du MASTER_PROMPT
        pending = self.read_pending_tasks(project_path)
        task_ids = [t["id"] for t in pending if "transcript" in t["description"].lower()
                    or "TASK-001" in t["id"]]

        # 2. Trouver les transcripts
        transcript_files = self._find_transcripts(project_path)
        if not transcript_files:
            print("  [ATTENTION] Aucun transcript NoteGPT_TRANSCRIPT_*.txt trouvé.")
            print(f"  Cherché dans : {self.transcripts_path or project_path.parent}")
            self.findings = []
            return {"agent": self.name, "total": 0, "videos": [], "generated_files": []}

        print(f"\n  {len(transcript_files)} transcript(s) trouvé(s)")

        # 3. Traitement de chaque transcript
        results = []
        for i, tf in enumerate(transcript_files, 1):
            print(f"\n  [{i}/{len(transcript_files)}] {tf.name[:60]}")
            r = self._process_transcript(tf)
            results.append(r)
            print(f"    → {len(r['quotes'])} citation(s) extraite(s) | vidéo: {r['video_id'] or 'inconnue'}")

        # 4. Génération des fichiers YAML enrichis
        print("\n  Génération des fichiers YAML enrichis...")
        data_dir = project_path / "_data"

        videos_yaml = self._build_videos_enriched(results)
        self._write_file(data_dir / "videos_enriched.yml", videos_yaml)

        args_yaml = self._build_arguments_enriched(results)
        self._write_file(data_dir / "arguments_enriched.yml", args_yaml)

        # 5. Complétion des tâches MASTER_PROMPT
        if "TASK-001" in [t["id"] for t in pending]:
            self.mark_task_done(project_path, "TASK-001", self.name)

        # 6. Findings pour le rapport
        self.findings = [
            {
                "video_id": r["video_id"],
                "title": r["title"][:60],
                "quotes_count": len(r["quotes"]),
            }
            for r in results
        ]

        total_quotes = sum(len(r["quotes"]) for r in results)
        print(f"\n  Résultat : {len(results)} vidéo(s), {total_quotes} citation(s) extraite(s)")

        return {
            "agent": self.name,
            "total": total_quotes,
            "videos": results,
            "generated_files": [str(f) for f in self.generated_files],
        }
