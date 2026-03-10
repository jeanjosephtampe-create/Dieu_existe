"""
base_agent.py — Classe de base pour tous les agents.
Intègre Ollama (llama3.1:8b) pour l'inférence locale.
"""

import json
import re
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import ollama

# ------------------------------------------------------------------ #
#  Presets de vitesse                                                  #
# ------------------------------------------------------------------ #

SPEED_PRESETS: dict[str, dict] = {
    "fast": {
        "max_llm_calls": 0,
        "label": "Rapide — analyse statique uniquement (0 appel LLM)",
        "estimated_seconds": (5, 20),
    },
    "normal": {
        "max_llm_calls": 3,
        "label": "Normal — statique + LLM limité (3 appels/agent max)",
        "estimated_seconds": (90, 300),
    },
    "deep": {
        "max_llm_calls": -1,  # illimité
        "label": "Approfondi — analyse complète sans limite",
        "estimated_seconds": (600, 1500),
    },
}


def estimate_duration(speed: str, agents: list[str]) -> str:
    """Retourne une chaîne d'estimation de durée selon le mode et les agents."""
    preset = SPEED_PRESETS.get(speed, SPEED_PRESETS["normal"])
    lo, hi = preset["estimated_seconds"]
    # Ajustement selon le nombre d'agents
    factor = len(agents) / 4
    lo_adj = int(lo * factor)
    hi_adj = int(hi * factor)

    def fmt(s: int) -> str:
        if s < 60:
            return f"{s}s"
        return f"{s // 60}m{s % 60:02d}s"

    return f"{fmt(lo_adj)} – {fmt(hi_adj)}"


class BaseAgent(ABC):
    """
    Agent de base avec intégration Ollama et contrôle de la durée.

    Paramètre clé : max_llm_calls
      -1  → illimité (mode deep)
       0  → analyse statique uniquement (mode fast)
       N  → maximum N appels LLM (mode normal)
    """

    def __init__(
        self,
        name: str,
        role: str,
        model: str = "llama3.1:8b",
        max_llm_calls: int = -1,
    ):
        self.name = name
        self.role = role
        self.model = model
        self.max_llm_calls = max_llm_calls   # -1 = illimité
        self.findings: list[dict] = []
        self.generated_files: list[Path] = []  # fichiers écrits par cet agent
        self._call_count = 0
        self._skipped_calls = 0              # appels sautés à cause de la limite
        self._total_llm_time = 0.0           # secondes passées à attendre le LLM

    # ------------------------------------------------------------------ #
    #  Communication avec le LLM                                           #
    # ------------------------------------------------------------------ #

    @property
    def llm_budget_exhausted(self) -> bool:
        """True si le quota d'appels LLM est atteint."""
        return self.max_llm_calls >= 0 and self._call_count >= self.max_llm_calls

    def _chat(self, user_msg: str, temperature: float = 0.15) -> str:
        """
        Envoie un message au LLM et retourne la réponse texte.
        Retourne "[]" immédiatement si le quota max_llm_calls est atteint.
        """
        if self.llm_budget_exhausted:
            self._skipped_calls += 1
            return "[]"

        self._call_count += 1
        remaining = (
            f"{self.max_llm_calls - self._call_count} restant(s)"
            if self.max_llm_calls >= 0
            else "illimité"
        )
        print(f"    [LLM #{self._call_count}] {self.name} ({remaining})", flush=True)

        t0 = time.monotonic()
        full_content = ""
        try:
            stream = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.role},
                    {"role": "user", "content": user_msg},
                ],
                options={"temperature": temperature, "num_ctx": 4096},
                stream=True,
            )
            print("    ┌ ", end="", flush=True)
            for chunk in stream:
                token = chunk.message.content
                full_content += token
                # Indente chaque nouvelle ligne pour garder l'alignement
                token = token.replace("\n", "\n    │ ")
                print(token, end="", flush=True)

            elapsed = time.monotonic() - t0
            self._total_llm_time += elapsed
            print(f"\n    └─ {elapsed:.1f}s", flush=True)
            return full_content
        except Exception as exc:
            print(f"\n  [ERREUR LLM {self.name}] {exc}")
            return "[]"

    def _chat_json(self, user_msg: str, temperature: float = 0.1) -> Any:
        """Appelle le LLM et parse la réponse JSON. Retourne None si échec."""
        if self.llm_budget_exhausted:
            self._skipped_calls += 1
            return None

        raw = self._chat(user_msg, temperature)
        parsed = self._parse_json(raw)
        if parsed is None and not self.llm_budget_exhausted:
            # Deuxième tentative avec instruction explicite
            retry_msg = user_msg + "\n\nIMPORTANT: Réponds UNIQUEMENT avec du JSON valide, sans texte autour."
            raw = self._chat(retry_msg, temperature)
            parsed = self._parse_json(raw)

        # Résumé lisible des findings extraits
        if isinstance(parsed, list) and parsed:
            lines = []
            for item in parsed[:4]:
                if not isinstance(item, dict):
                    continue
                prio = item.get("priority", "?")
                issue = item.get("issue", item.get("text", "?"))[:60]
                lines.append(f"[{prio}] {issue}")
            more = f" + {len(parsed) - 4} autres" if len(parsed) > 4 else ""
            print(f"    → {len(parsed)} finding(s) :", flush=True)
            for line in lines:
                print(f"       • {line}", flush=True)
            if more:
                print(f"       {more}", flush=True)

        return parsed

    # ------------------------------------------------------------------ #
    #  Parsing JSON robuste                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_json(text: str) -> Any:
        """Extrait du JSON même si le LLM ajoute du texte autour."""
        if not text:
            return None

        # 1. Blocs ```json ... ```
        m = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 2. Blocs ``` ... ```
        m = re.search(r"```\s*([\s\S]*?)\s*```", text)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass

        # 3. Tableau JSON le plus externe [ ... ]
        start = text.find("[")
        if start != -1:
            depth = 0
            for i, ch in enumerate(text[start:], start):
                if ch == "[":
                    depth += 1
                elif ch == "]":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start : i + 1])
                        except json.JSONDecodeError:
                            break

        # 4. Objet JSON { ... }
        start = text.find("{")
        if start != -1:
            depth = 0
            for i, ch in enumerate(text[start:], start):
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            return json.loads(text[start : i + 1])
                        except json.JSONDecodeError:
                            break

        # 5. Texte brut
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return None

    # ------------------------------------------------------------------ #
    #  Interface obligatoire                                               #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def run(self, project_path: Path) -> dict:
        """Lance l'analyse et retourne un dict de résultats."""

    def summary(self) -> str:
        """Résumé court des findings."""
        skipped = f", {self._skipped_calls} sauté(s)" if self._skipped_calls else ""
        time_str = f" en {self._total_llm_time:.0f}s LLM" if self._total_llm_time else ""
        return (
            f"[{self.name}] {len(self.findings)} finding(s) — "
            f"{self._call_count} appel(s) LLM{skipped}{time_str}"
        )

    # ------------------------------------------------------------------ #
    #  Utilitaires fichiers                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _read_file(path: Path, max_chars: int = 5000) -> str:
        """Lit un fichier en tronquant si nécessaire."""
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            if len(content) > max_chars:
                return content[:max_chars] + "\n... [tronqué]"
            return content
        except Exception:
            return ""

    def _write_file(self, path: Path, content: str) -> Path:
        """Écrit un fichier et l'enregistre dans generated_files."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        self.generated_files.append(path)
        print(f"    ✎ Écrit : {path.relative_to(path.parents[2]) if path.parents[2].exists() else path.name}", flush=True)
        return path

    @staticmethod
    def _is_excluded(path: Path) -> bool:
        """Vérifie si le chemin est dans un dossier à ignorer."""
        excluded = {"node_modules", ".git", "_site", "vendor", "reports", "tests"}
        return any(part in excluded for part in path.parts)

    # ------------------------------------------------------------------ #
    #  Lecture du Master Prompt                                            #
    # ------------------------------------------------------------------ #

    @staticmethod
    def read_pending_tasks(project_path: Path) -> list[dict]:
        """
        Lit MASTER_PROMPT.md et retourne les tâches non cochées
        qui ne sont pas déjà dans task_log.json.

        Retourne une liste de dicts :
          {"id": "TASK-001", "description": "...", "line_idx": 12}
        """
        master = project_path / "MASTER_PROMPT.md"
        task_log = project_path / "agents" / "memory" / "task_log.json"

        if not master.exists():
            return []

        # Tâches déjà complétées
        done: set[str] = set()
        if task_log.exists():
            try:
                log = json.loads(task_log.read_text(encoding="utf-8"))
                done = {k for k, v in log.items() if v.get("status") == "done"}
            except Exception:
                pass

        pending = []
        lines = master.read_text(encoding="utf-8").splitlines()
        task_re = re.compile(r"^- \[ \]\s+(TASK-\w+)\s*:\s*(.+)$")
        for idx, line in enumerate(lines):
            m = task_re.match(line.strip())
            if m:
                task_id, desc = m.group(1), m.group(2).strip()
                if task_id not in done:
                    pending.append({"id": task_id, "description": desc, "line_idx": idx})
        return pending

    @staticmethod
    def mark_task_done(project_path: Path, task_id: str, agent_name: str) -> None:
        """Coche la tâche dans MASTER_PROMPT.md et la logue dans task_log.json."""
        import datetime

        # 1. Cocher dans MASTER_PROMPT.md
        master = project_path / "MASTER_PROMPT.md"
        if master.exists():
            text = master.read_text(encoding="utf-8")
            text = re.sub(
                rf"^(- )\[ \](\s+{re.escape(task_id)}\s*:)",
                r"\1[x]\2",
                text,
                flags=re.MULTILINE,
            )
            master.write_text(text, encoding="utf-8")

        # 2. Logger dans task_log.json
        task_log = project_path / "agents" / "memory" / "task_log.json"
        task_log.parent.mkdir(parents=True, exist_ok=True)
        log: dict = {}
        if task_log.exists():
            try:
                log = json.loads(task_log.read_text(encoding="utf-8"))
            except Exception:
                pass
        log[task_id] = {
            "status": "done",
            "executed_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "agent": agent_name,
        }
        task_log.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
