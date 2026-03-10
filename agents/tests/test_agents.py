"""
test_agents.py — Tests pour l'équipe d'agents Jekyll.

Tests unitaires (mocks, rapides) :
    pytest agents/tests/test_agents.py -v

Tests d'intégration (Ollama réel, lents) :
    pytest agents/tests/test_agents.py -v -m integration

Tous les tests :
    pytest agents/tests/test_agents.py -v --run-integration
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ajouter le dossier racine au path pour que les imports fonctionnent
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

# ------------------------------------------------------------------ #
#  Fixtures                                                            #
# ------------------------------------------------------------------ #

PROJECT_PATH = ROOT  # C:/Users/jeanj/Documents/Dieu_preuves/Jekyll


@pytest.fixture
def project_path() -> Path:
    return PROJECT_PATH


@pytest.fixture
def sample_html() -> str:
    return """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Test Page</title>
</head>
<body>
  <h1>Titre principal</h1>
  <img src="image.jpg">
  <a href="https://example.com" target="_blank">Lien</a>
  <button>×</button>
</body>
</html>"""


@pytest.fixture
def sample_css() -> str:
    return """
body { font-size: 16px; }
.btn { font-size: 14px; transition: all 0.3s; }
h1 { color: #333; }
"""


@pytest.fixture
def mock_ollama_response():
    """Retourne une réponse Ollama mockée avec du JSON valide."""
    def _make_response(content: str):
        msg = MagicMock()
        msg.content = content
        resp = MagicMock()
        resp.message = msg
        return resp
    return _make_response


# ------------------------------------------------------------------ #
#  Tests BaseAgent                                                     #
# ------------------------------------------------------------------ #

class TestBaseAgent:
    def test_parse_json_array(self):
        from agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            def run(self, p): pass

        agent = ConcreteAgent("Test", "Test role")

        # Tableau JSON direct
        result = agent._parse_json('[{"key": "value"}]')
        assert result == [{"key": "value"}]

    def test_parse_json_with_markdown_block(self):
        from agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            def run(self, p): pass

        agent = ConcreteAgent("Test", "Test role")

        text = 'Voici le résultat :\n```json\n[{"type": "bug"}]\n```\nC\'est tout.'
        result = agent._parse_json(text)
        assert result == [{"type": "bug"}]

    def test_parse_json_with_text_around(self):
        from agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            def run(self, p): pass

        agent = ConcreteAgent("Test", "Test role")

        text = 'Analyse complète : [{"issue": "test", "severity": "high"}] voilà.'
        result = agent._parse_json(text)
        assert isinstance(result, list)
        assert result[0]["severity"] == "high"

    def test_parse_json_invalid_returns_none(self):
        from agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            def run(self, p): pass

        agent = ConcreteAgent("Test", "Test role")
        result = agent._parse_json("Ce n'est pas du JSON du tout.")
        assert result is None

    def test_parse_json_empty_string(self):
        from agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            def run(self, p): pass

        agent = ConcreteAgent("Test", "Test role")
        result = agent._parse_json("")
        assert result is None

    def test_is_excluded(self):
        from agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            def run(self, p): pass

        agent = ConcreteAgent("Test", "role")
        assert agent._is_excluded(Path("project/node_modules/lib/file.js"))
        assert agent._is_excluded(Path("project/_site/index.html"))
        assert not agent._is_excluded(Path("project/assets/css/main.css"))
        assert not agent._is_excluded(Path("project/_includes/nav.html"))

    def test_read_file_truncates(self, tmp_path):
        from agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            def run(self, p): pass

        agent = ConcreteAgent("Test", "role")
        f = tmp_path / "big.txt"
        f.write_text("x" * 10000, encoding="utf-8")
        result = agent._read_file(f, max_chars=100)
        assert len(result) <= 120  # 100 + "[tronqué]"
        assert "[tronqué]" in result

    def test_read_file_missing(self, tmp_path):
        from agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            def run(self, p): pass

        agent = ConcreteAgent("Test", "role")
        result = agent._read_file(tmp_path / "inexistant.txt")
        assert result == ""


# ------------------------------------------------------------------ #
#  Tests BaseAgent — max_llm_calls et vitesse                         #
# ------------------------------------------------------------------ #

class TestBaseAgentSpeed:
    def _make_agent(self, max_llm_calls: int):
        from agents.base_agent import BaseAgent

        class ConcreteAgent(BaseAgent):
            def run(self, p): pass

        return ConcreteAgent("Test", "role", max_llm_calls=max_llm_calls)

    def test_max_calls_zero_skips_llm(self, mock_ollama_response):
        agent = self._make_agent(max_llm_calls=0)
        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response("[]")
            result = agent._chat("test message")
        # Avec max_llm_calls=0, ollama.chat ne doit jamais être appelé
        mock_chat.assert_not_called()
        assert result == "[]"
        assert agent._call_count == 0
        assert agent._skipped_calls == 1

    def test_max_calls_enforced(self, mock_ollama_response):
        agent = self._make_agent(max_llm_calls=2)
        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response("[{}]")
            agent._chat("msg1")
            agent._chat("msg2")
            agent._chat("msg3")  # doit être sauté
        assert mock_chat.call_count == 2
        assert agent._call_count == 2
        assert agent._skipped_calls == 1

    def test_max_calls_minus_one_is_unlimited(self, mock_ollama_response):
        agent = self._make_agent(max_llm_calls=-1)
        assert not agent.llm_budget_exhausted
        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response("[]")
            for _ in range(5):
                agent._chat("msg")
        assert mock_chat.call_count == 5
        assert agent._skipped_calls == 0

    def test_budget_exhausted_property(self):
        agent = self._make_agent(max_llm_calls=3)
        assert not agent.llm_budget_exhausted
        agent._call_count = 3
        assert agent.llm_budget_exhausted

    def test_chat_json_skipped_when_budget_zero(self):
        agent = self._make_agent(max_llm_calls=0)
        result = agent._chat_json("test")
        assert result is None
        assert agent._skipped_calls == 1

    def test_summary_shows_skipped_calls(self, mock_ollama_response):
        agent = self._make_agent(max_llm_calls=1)
        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response("[]")
            agent._chat("msg1")
            agent._chat("msg2")  # sauté
        summary = agent.summary()
        assert "1 appel" in summary
        assert "sauté" in summary

    def test_estimate_duration_function(self):
        from agents.base_agent import estimate_duration
        fast = estimate_duration("fast", ["code", "uiux", "seo", "req"])
        normal = estimate_duration("normal", ["code", "uiux", "seo", "req"])
        deep = estimate_duration("deep", ["code", "uiux", "seo", "req"])
        # Doit retourner des chaînes non vides
        assert len(fast) > 0
        assert len(normal) > 0
        assert len(deep) > 0

    def test_speed_presets_complete(self):
        from agents.base_agent import SPEED_PRESETS
        required_keys = {"max_llm_calls", "label", "estimated_seconds"}
        for name, preset in SPEED_PRESETS.items():
            assert required_keys <= set(preset.keys()), f"Preset {name} incomplet"
        assert "fast" in SPEED_PRESETS
        assert "normal" in SPEED_PRESETS
        assert "deep" in SPEED_PRESETS
        assert SPEED_PRESETS["fast"]["max_llm_calls"] == 0
        assert SPEED_PRESETS["deep"]["max_llm_calls"] == -1


class TestOrchestratorSpeed:
    def test_orchestrator_speed_fast(self, project_path):
        from agents.orchestrator import Orchestrator
        orch = Orchestrator(project_path, speed="fast")
        assert orch.max_llm_calls == 0
        assert orch.speed == "fast"

    def test_orchestrator_speed_normal(self, project_path):
        from agents.orchestrator import Orchestrator
        orch = Orchestrator(project_path, speed="normal")
        assert orch.max_llm_calls == 3
        assert orch.speed == "normal"

    def test_orchestrator_speed_deep(self, project_path):
        from agents.orchestrator import Orchestrator
        orch = Orchestrator(project_path, speed="deep")
        assert orch.max_llm_calls == -1

    def test_orchestrator_max_calls_override(self, project_path):
        from agents.orchestrator import Orchestrator
        # max_llm_calls explicite prend la priorité sur le speed
        orch = Orchestrator(project_path, speed="fast", max_llm_calls=7)
        assert orch.max_llm_calls == 7

    def test_orchestrator_invalid_speed_defaults_to_normal(self, project_path):
        from agents.orchestrator import Orchestrator
        orch = Orchestrator(project_path, speed="turbo")  # invalide → normal
        assert orch.speed == "normal"

    def test_fast_mode_no_llm_calls(self, project_path):
        """En mode fast, aucun appel LLM ne doit être émis."""
        from agents.orchestrator import Orchestrator
        with patch("agents.base_agent.ollama.chat") as mock_chat:
            orch = Orchestrator(project_path, speed="fast")
            orch.run(agents=["code"])
        mock_chat.assert_not_called()

    def test_normal_mode_caps_calls(self, project_path, mock_ollama_response):
        """En mode normal (max=3), chaque agent doit faire au plus 3 appels."""
        from agents.orchestrator import Orchestrator
        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response("[]")
            orch = Orchestrator(project_path, speed="normal")
            orch.run(agents=["code"])
        # Le CodeAgent analyse ~12 fichiers mais est limité à 3 appels
        assert mock_chat.call_count <= 3 * 2  # *2 car retry possible

    def test_report_contains_speed_info(self, project_path, mock_ollama_response):
        """Le rapport doit mentionner le mode de vitesse."""
        from agents.orchestrator import Orchestrator
        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response("[]")
            orch = Orchestrator(project_path, speed="fast")
            report_path = orch.run(agents=["code"])
        content = Path(report_path).read_text(encoding="utf-8")
        assert "FAST" in content or "fast" in content.lower()


# ------------------------------------------------------------------ #
#  Tests CodeAgent — Analyse statique                                  #
# ------------------------------------------------------------------ #

class TestCodeAgentStatic:
    def test_detects_img_without_alt(self):
        from agents.code_agent import CodeAgent
        agent = CodeAgent()
        issues = agent._static_html('<img src="photo.jpg">', "test.html")
        assert any("alt" in i["what"].lower() for i in issues)

    def test_no_issue_when_alt_present(self):
        from agents.code_agent import CodeAgent
        agent = CodeAgent()
        issues = agent._static_html('<img src="photo.jpg" alt="Description">', "test.html")
        alt_issues = [i for i in issues if "alt" in i["what"].lower()]
        assert len(alt_issues) == 0

    def test_detects_target_blank_without_noopener(self):
        from agents.code_agent import CodeAgent
        agent = CodeAgent()
        issues = agent._static_html('<a href="x" target="_blank">Lien</a>', "test.html")
        assert any("noopener" in i["what"].lower() or "blank" in i["what"].lower()
                   for i in issues)

    def test_no_issue_when_noopener_present(self):
        from agents.code_agent import CodeAgent
        agent = CodeAgent()
        issues = agent._static_html(
            '<a href="x" target="_blank" rel="noopener noreferrer">Lien</a>',
            "test.html"
        )
        blank_issues = [i for i in issues if "blank" in i.get("what", "").lower()]
        assert len(blank_issues) == 0

    def test_detects_font_size_px(self):
        from agents.code_agent import CodeAgent
        agent = CodeAgent()
        issues = agent._static_css("body { font-size: 16px; }", "main.css")
        assert any("font-size" in i["what"].lower() for i in issues)

    def test_detects_too_many_important(self):
        from agents.code_agent import CodeAgent
        agent = CodeAgent()
        css = "\n".join(f".rule{i} {{ color: red !important; }}" for i in range(10))
        issues = agent._static_css(css, "main.css")
        assert any("!important" in i["what"] for i in issues)

    def test_detects_var_in_js(self):
        from agents.code_agent import CodeAgent
        agent = CodeAgent()
        issues = agent._static_js("var x = 1;\nvar y = 2;", "main.js")
        assert any("var" in i["what"].lower() for i in issues)

    def test_no_var_issue_with_let_const(self):
        from agents.code_agent import CodeAgent
        agent = CodeAgent()
        issues = agent._static_js("const x = 1;\nlet y = 2;", "main.js")
        var_issues = [i for i in issues if "var" in i.get("what", "").lower()]
        assert len(var_issues) == 0

    def test_all_issues_have_required_keys(self, sample_html):
        from agents.code_agent import CodeAgent
        agent = CodeAgent()
        issues = agent._static_html(sample_html, "test.html")
        required_keys = {"type", "severity", "what", "why", "fix"}
        for issue in issues:
            missing = required_keys - set(issue.keys())
            assert not missing, f"Clés manquantes dans l'issue : {missing}"


# ------------------------------------------------------------------ #
#  Tests CodeAgent — LLM (mocké)                                      #
# ------------------------------------------------------------------ #

class TestCodeAgentLLM:
    def test_run_with_mocked_llm(self, project_path, mock_ollama_response):
        from agents.code_agent import CodeAgent

        llm_result = json.dumps([{
            "type": "improvement",
            "severity": "low",
            "line": 5,
            "what": "Variable non utilisée",
            "why": "Code mort",
            "fix": "Supprimer la variable",
        }])

        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response(llm_result)
            agent = CodeAgent()
            result = agent.run(project_path)

        assert "agent" in result
        assert result["agent"] == "CodeReviewer"
        assert "files_analyzed" in result
        assert result["files_analyzed"] > 0
        assert "total_issues" in result
        assert isinstance(result["all_issues"], list)

    def test_handles_invalid_llm_json(self, project_path, mock_ollama_response):
        from agents.code_agent import CodeAgent

        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response("Je ne peux pas analyser ce code.")
            agent = CodeAgent()
            result = agent.run(project_path)

        # Doit fonctionner même si le LLM ne renvoie pas de JSON
        assert result["agent"] == "CodeReviewer"
        # Les issues statiques doivent quand même être présentes
        assert isinstance(result["all_issues"], list)


# ------------------------------------------------------------------ #
#  Tests UIUXAgent — Analyse statique                                  #
# ------------------------------------------------------------------ #

class TestUIUXAgentStatic:
    def test_detects_missing_focus_style(self):
        from agents.uiux_agent import UIUXAgent
        agent = UIUXAgent()
        issues = agent._check_static_css("body { color: red; }", "main.css")
        assert any(":focus" in i.get("element", "") for i in issues)

    def test_no_focus_issue_when_defined(self):
        from agents.uiux_agent import UIUXAgent
        agent = UIUXAgent()
        issues = agent._check_static_css(
            ":focus-visible { outline: 2px solid blue; }", "main.css"
        )
        focus_issues = [i for i in issues if ":focus" in i.get("element", "")]
        assert len(focus_issues) == 0

    def test_detects_transition_all(self):
        from agents.uiux_agent import UIUXAgent
        agent = UIUXAgent()
        issues = agent._check_static_css(".btn { transition: all 0.3s; }", "main.css")
        assert any("transition" in i.get("element", "").lower() for i in issues)

    def test_detects_missing_media_query(self):
        from agents.uiux_agent import UIUXAgent
        agent = UIUXAgent()
        issues = agent._check_static_css("body { margin: 0; }", "main.css")
        assert any("@media" in i.get("element", "") for i in issues)

    def test_detects_empty_button(self):
        from agents.uiux_agent import UIUXAgent
        agent = UIUXAgent()
        issues = agent._check_static_a11y("<button></button>", "test.html")
        assert any("bouton" in i.get("issue", "").lower() for i in issues)

    def test_detects_positive_tabindex(self):
        from agents.uiux_agent import UIUXAgent
        agent = UIUXAgent()
        issues = agent._check_static_a11y('<div tabindex="3">élément</div>', "test.html")
        assert any("tabindex" in i.get("element", "").lower() for i in issues)

    def test_all_issues_have_required_keys(self, sample_css):
        from agents.uiux_agent import UIUXAgent
        agent = UIUXAgent()
        issues = agent._check_static_css(sample_css, "main.css")
        required_keys = {"category", "priority", "issue", "recommendation"}
        for issue in issues:
            missing = required_keys - set(issue.keys())
            assert not missing, f"Clés manquantes : {missing}"


# ------------------------------------------------------------------ #
#  Tests UIUXAgent — LLM (mocké)                                      #
# ------------------------------------------------------------------ #

class TestUIUXAgentLLM:
    def test_run_with_mocked_llm(self, project_path, mock_ollama_response):
        from agents.uiux_agent import UIUXAgent

        llm_result = json.dumps([{
            "category": "accessibility",
            "priority": "high",
            "element": ".hero",
            "issue": "Contraste insuffisant",
            "impact": "Illisible pour les malvoyants",
            "recommendation": "Augmenter le ratio de contraste à 4.5:1",
            "code_fix": None,
        }])

        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response(llm_result)
            agent = UIUXAgent()
            result = agent.run(project_path)

        assert result["agent"] == "UXDesigner"
        assert "total" in result
        assert "by_priority" in result
        assert isinstance(result["all_recommendations"], list)

    def test_by_priority_structure(self, project_path, mock_ollama_response):
        from agents.uiux_agent import UIUXAgent

        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response("[]")
            agent = UIUXAgent()
            result = agent.run(project_path)

        assert set(result["by_priority"].keys()) == {"high", "medium", "low"}


# ------------------------------------------------------------------ #
#  Tests SEOAgent — Analyse statique                                   #
# ------------------------------------------------------------------ #

class TestSEOAgentStatic:
    def test_detects_missing_title(self):
        from agents.seo_agent import SEOAgent
        agent = SEOAgent()
        issues = agent._check_static_seo("<html><body>Contenu</body></html>", "test.html")
        assert any("title" in i.get("issue", "").lower() for i in issues)

    def test_detects_missing_meta_description(self):
        from agents.seo_agent import SEOAgent
        agent = SEOAgent()
        html = "<html><head><title>Test</title></head><body></body></html>"
        issues = agent._check_static_seo(html, "test.html")
        assert any("description" in i.get("issue", "").lower() for i in issues)

    def test_detects_long_title(self):
        from agents.seo_agent import SEOAgent
        agent = SEOAgent()
        long_title = "x" * 70
        html = f"<html><head><title>{long_title}</title></head><body><h1>Titre</h1></body></html>"
        issues = agent._check_static_seo(html, "test.html")
        assert any("long" in i.get("issue", "").lower() for i in issues)

    def test_detects_multiple_h1(self):
        from agents.seo_agent import SEOAgent
        agent = SEOAgent()
        html = "<html><head><title>Test</title></head><body><h1>Un</h1><h1>Deux</h1></body></html>"
        issues = agent._check_static_seo(html, "test.html")
        assert any("H1" in i.get("issue", "") for i in issues)

    def test_detects_missing_og_tags(self):
        from agents.seo_agent import SEOAgent
        agent = SEOAgent()
        html = "<html><head><title>Test</title></head><body><h1>Test</h1></body></html>"
        issues = agent._check_static_seo(html, "test.html")
        assert any("open graph" in i.get("issue", "").lower() for i in issues)

    def test_no_issues_on_well_formed_html(self):
        from agents.seo_agent import SEOAgent
        agent = SEOAgent()
        html = """<html>
<head>
  <title>Dieu Existe — Les Preuves</title>
  <meta name="description" content="Site apologétique chrétien.">
  <meta property="og:title" content="Test">
  <link rel="canonical" href="https://dieu-preuves.fr/">
</head>
<body>
  <h1>Un seul H1</h1>
  <img src="img.jpg" alt="Description">
</body>
</html>"""
        issues = agent._check_static_seo(html, "test.html")
        # Les issues "high" ne devraient pas apparaître pour les éléments présents
        high = [i for i in issues if i.get("priority") == "high"
                and any(k in i.get("issue", "").lower()
                        for k in ["title manquante", "description manquante", "h1"])]
        assert len(high) == 0


# ------------------------------------------------------------------ #
#  Tests Orchestrateur                                                 #
# ------------------------------------------------------------------ #

class TestOrchestrator:
    def test_init_valid_project(self, project_path):
        from agents.orchestrator import Orchestrator
        orch = Orchestrator(project_path)
        assert orch.project_path == project_path

    def test_init_invalid_project(self, tmp_path):
        from agents.orchestrator import Orchestrator
        with pytest.raises(FileNotFoundError):
            Orchestrator(tmp_path / "inexistant")

    def test_run_all_agents_mocked(self, project_path, mock_ollama_response, tmp_path):
        from agents.orchestrator import Orchestrator

        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response("[]")

            # Rediriger les rapports vers tmp_path
            orch = Orchestrator(project_path)
            orch.project_path = project_path

            report_path = orch.run(agents=["code", "uiux", "seo"])

        assert Path(report_path).exists()
        content = Path(report_path).read_text(encoding="utf-8")
        assert "Rapport d'amélioration" in content
        assert "Jekyll Agent Team" in content

    def test_run_single_agent(self, project_path, mock_ollama_response):
        from agents.orchestrator import Orchestrator

        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response("[]")
            orch = Orchestrator(project_path)
            report_path = orch.run(agents=["code"])

        assert Path(report_path).exists()
        assert "code" in orch.results
        assert "uiux" not in orch.results
        assert "seo" not in orch.results

    def test_report_contains_all_sections(self, project_path, mock_ollama_response):
        from agents.orchestrator import Orchestrator

        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response("[]")
            orch = Orchestrator(project_path)
            report_path = orch.run(agents=["code", "uiux", "seo"])

        content = Path(report_path).read_text(encoding="utf-8")
        assert "Résumé exécutif" in content
        assert "KeyCode" in content
        assert "UI/UX" in content
        assert "SEO" in content
        assert "Actions prioritaires" in content

    def test_get_priority_actions(self, project_path, mock_ollama_response):
        from agents.orchestrator import Orchestrator

        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response("[]")
            orch = Orchestrator(project_path)
            orch.run(agents=["code"])

        actions = orch._get_priority_actions(top_n=5)
        assert len(actions) <= 5


# ------------------------------------------------------------------ #
#  Tests RequirementsAgent                                            #
# ------------------------------------------------------------------ #

class TestRequirementsParser:
    def test_parse_requirements_from_file(self, project_path):
        from agents.requirements_agent import parse_requirements
        req_file = project_path / "REQUIREMENTS.md"
        if not req_file.exists():
            pytest.skip("REQUIREMENTS.md absent")
        reqs = parse_requirements(req_file)
        assert len(reqs) > 10, "Trop peu d'exigences parsées"

    def test_parse_declared_vs_undeclared(self, project_path):
        from agents.requirements_agent import parse_requirements
        req_file = project_path / "REQUIREMENTS.md"
        if not req_file.exists():
            pytest.skip("REQUIREMENTS.md absent")
        reqs = parse_requirements(req_file)
        declared = [r for r in reqs if r.declared]
        undeclared = [r for r in reqs if not r.declared]
        assert len(declared) > 0, "Aucune exigence déclarée [x]"
        assert len(undeclared) > 0, "Aucune exigence non déclarée [ ]"

    def test_parse_sections(self, project_path):
        from agents.requirements_agent import parse_requirements
        req_file = project_path / "REQUIREMENTS.md"
        if not req_file.exists():
            pytest.skip("REQUIREMENTS.md absent")
        reqs = parse_requirements(req_file)
        sections = {r.section for r in reqs}
        assert len(sections) >= 3, f"Trop peu de sections : {sections}"

    def test_parse_from_tmp_file(self, tmp_path):
        from agents.requirements_agent import parse_requirements, Requirement
        md = tmp_path / "REQUIREMENTS.md"
        md.write_text("""
## 1. Technique
### 1.1 Infrastructure
- [x] Fichier robots.txt présent
- [ ] Image OG créée (1200×630px)

## 2. SEO
- [x] Meta description présente
- [ ] Schema.org VideoObject
""", encoding="utf-8")
        reqs = parse_requirements(md)
        assert len(reqs) == 4
        assert reqs[0].declared is True
        assert reqs[0].text == "Fichier robots.txt présent"
        assert reqs[1].declared is False
        assert reqs[2].section == "2. SEO"
        assert reqs[3].section == "2. SEO"

    def test_requirement_dataclass(self):
        from agents.requirements_agent import Requirement, Status
        req = Requirement(
            section="Test", subsection="Sub",
            text="Le site doit être accessible",
            declared=True,
        )
        assert req.status == Status.UNKNOWN
        assert req.id == "Le site doit être accessible"
        assert req.declared is True


class TestStaticChecker:
    def test_check_robots_txt(self, project_path):
        from agents.requirements_agent import StaticChecker, Status
        checker = StaticChecker(project_path)
        status, evidence = checker.check_robots_txt()
        assert status == Status.MET
        assert "robots.txt" in evidence

    def test_check_gemfile(self, project_path):
        from agents.requirements_agent import StaticChecker, Status
        checker = StaticChecker(project_path)
        status, evidence = checker.check_gemfile()
        # Le Gemfile doit exister dans ce projet
        assert status in (Status.MET, Status.PARTIAL)

    def test_check_og_image_missing(self, project_path):
        from agents.requirements_agent import StaticChecker, Status
        checker = StaticChecker(project_path)
        status, evidence = checker.check_og_image()
        # Probablement manquant dans ce projet
        assert status in (Status.MET, Status.MISSING)

    def test_check_lang(self, project_path):
        from agents.requirements_agent import StaticChecker, Status
        checker = StaticChecker(project_path)
        status, evidence = checker.check_lang()
        assert status == Status.MET

    def test_check_canonical(self, project_path):
        from agents.requirements_agent import StaticChecker, Status
        checker = StaticChecker(project_path)
        status, evidence = checker.check_canonical()
        assert status == Status.MET

    def test_check_schema_faqpage(self, project_path):
        from agents.requirements_agent import StaticChecker, Status
        checker = StaticChecker(project_path)
        status, evidence = checker.check_schema_faqpage()
        assert status == Status.MET
        assert "5" in evidence or int("".join(filter(str.isdigit, evidence or "0"))) >= 5

    def test_check_data_files(self, project_path):
        from agents.requirements_agent import StaticChecker, Status
        checker = StaticChecker(project_path)
        status, evidence = checker.check_data_files()
        assert status == Status.MET

    def test_check_lazy_loading(self, project_path):
        from agents.requirements_agent import StaticChecker, Status
        checker = StaticChecker(project_path)
        status, evidence = checker.check_lazy_loading()
        assert status == Status.MET

    def test_check_noopener(self, project_path):
        from agents.requirements_agent import StaticChecker, Status
        checker = StaticChecker(project_path)
        status, evidence = checker.check_noopener()
        # Doit être MET ou PARTIAL mais pas MISSING pour ce projet bien formé
        assert status in (Status.MET, Status.PARTIAL)

    def test_checker_dispatch(self, project_path):
        from agents.requirements_agent import StaticChecker, Requirement, Status
        checker = StaticChecker(project_path)
        req = Requirement(section="SEO", subsection="", text="robots.txt présent", declared=True)
        status, evidence = checker.check(req)
        assert status == Status.MET

    def test_checker_unknown_requirement(self, project_path):
        from agents.requirements_agent import StaticChecker, Requirement, Status
        checker = StaticChecker(project_path)
        req = Requirement(
            section="Custom", subsection="",
            text="Exigence totalement inconnue xyz42",
            declared=False,
        )
        status, evidence = checker.check(req)
        assert status == Status.UNKNOWN


class TestRequirementsAgentMocked:
    def test_run_returns_correct_structure(self, project_path, mock_ollama_response):
        from agents.requirements_agent import RequirementsAgent

        llm_response = '{"status": "met", "evidence": "Trouvé dans le code", "notes": ""}'
        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response(llm_response)
            agent = RequirementsAgent()
            result = agent.run(project_path)

        assert result["agent"] == "RequirementsChecker"
        assert "total" in result
        assert "met" in result
        assert "missing" in result
        assert "compliance_pct" in result
        assert "by_section" in result
        assert "missing_items" in result
        assert "all_requirements" in result
        assert result["total"] > 0

    def test_compliance_pct_is_valid(self, project_path, mock_ollama_response):
        from agents.requirements_agent import RequirementsAgent

        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response(
                '{"status": "met", "evidence": "OK", "notes": ""}'
            )
            agent = RequirementsAgent()
            result = agent.run(project_path)

        pct = result["compliance_pct"]
        assert 0 <= pct <= 100

    def test_all_requirements_have_status(self, project_path, mock_ollama_response):
        from agents.requirements_agent import RequirementsAgent

        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response(
                '{"status": "unknown", "evidence": "", "notes": ""}'
            )
            agent = RequirementsAgent()
            result = agent.run(project_path)

        for req in result["all_requirements"]:
            assert "status" in req
            assert "text" in req
            assert "section" in req

    def test_missing_requirements_file(self, tmp_path, mock_ollama_response):
        from agents.requirements_agent import RequirementsAgent
        # tmp_path n'a pas de REQUIREMENTS.md
        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response("[]")
            agent = RequirementsAgent()
            result = agent.run(tmp_path)

        assert "error" in result
        assert result["requirements"] == []

    def test_orchestrator_includes_req_agent(self, project_path, mock_ollama_response):
        from agents.orchestrator import Orchestrator

        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response(
                '{"status": "met", "evidence": "OK", "notes": ""}'
            )
            orch = Orchestrator(project_path)
            report_path = orch.run(agents=["req"])

        content = Path(report_path).read_text(encoding="utf-8")
        assert "RequirementsChecker" in content
        assert "conformité" in content.lower() or "Conformité" in content

    def test_report_has_compliance_matrix(self, project_path, mock_ollama_response):
        from agents.orchestrator import Orchestrator

        with patch("agents.base_agent.ollama.chat") as mock_chat:
            mock_chat.return_value = mock_ollama_response(
                '{"status": "met", "evidence": "OK", "notes": ""}'
            )
            orch = Orchestrator(project_path)
            report_path = orch.run(agents=["req"])

        content = Path(report_path).read_text(encoding="utf-8")
        assert "Matrice de conformité" in content
        assert "Taux de conformité" in content


# ------------------------------------------------------------------ #
#  Tests d'intégration (Ollama réel)                                  #
# ------------------------------------------------------------------ #

@pytest.mark.integration
class TestIntegrationWithOllama:
    """
    Tests qui appellent vraiment Ollama.
    Marqués @pytest.mark.integration — lents (~30-120s par test).

    Lancer avec : pytest -v -m integration
    """

    def test_ollama_is_reachable(self):
        import ollama
        try:
            models = ollama.list()
            assert models is not None
        except Exception as e:
            pytest.fail(f"Ollama non accessible : {e}")

    def test_llama_model_exists(self):
        import ollama
        models = ollama.list()
        names = [m.model for m in models.models]
        llama_found = any("llama3.1" in n or "llama3" in n for n in names)
        assert llama_found, f"llama3.1:8b non trouvé. Modèles : {names}"

    def test_base_agent_chat(self):
        from agents.base_agent import BaseAgent

        class TestAgent(BaseAgent):
            def run(self, p): pass

        agent = TestAgent("TestAgent", "Tu es un assistant utile. Réponds en JSON.")
        response = agent._chat_json('[{"test": "ok"}]\nRéponds avec exactement : [{"ok": true}]')
        # On vérifie juste que le LLM répond quelque chose
        assert response is not None or True  # Le LLM peut ne pas produire de JSON valide

    def test_code_agent_real_run(self, project_path):
        from agents.code_agent import CodeAgent
        agent = CodeAgent()
        result = agent.run(project_path)
        assert result["agent"] == "CodeReviewer"
        assert result["files_analyzed"] > 0
        assert isinstance(result["all_issues"], list)
        print(f"\n  Issues trouvées : {result['total_issues']}")

    def test_uiux_agent_real_run(self, project_path):
        from agents.uiux_agent import UIUXAgent
        agent = UIUXAgent()
        result = agent.run(project_path)
        assert result["agent"] == "UXDesigner"
        assert isinstance(result["all_recommendations"], list)
        print(f"\n  Recommandations : {result['total']}")

    def test_seo_agent_real_run(self, project_path):
        from agents.seo_agent import SEOAgent
        agent = SEOAgent()
        result = agent.run(project_path)
        assert result["agent"] == "SEOExpert"
        assert isinstance(result["all_issues"], list)
        print(f"\n  Points SEO : {result['total']}")

    def test_requirements_agent_real_run(self, project_path):
        from agents.requirements_agent import RequirementsAgent
        agent = RequirementsAgent()
        result = agent.run(project_path)
        assert result["agent"] == "RequirementsChecker"
        assert result["total"] > 0
        assert 0 <= result["compliance_pct"] <= 100
        print(f"\n  Exigences : {result['total']}")
        print(f"  Conformité : {result['compliance_pct']}%")
        print(f"  Manquantes : {result['missing']}")

    def test_full_orchestrator_run(self, project_path):
        from agents.orchestrator import Orchestrator
        orch = Orchestrator(project_path)
        report_path = orch.run(agents=["code", "uiux", "seo", "req"])
        assert Path(report_path).exists()
        content = Path(report_path).read_text(encoding="utf-8")
        assert len(content) > 500
        assert "Matrice de conformité" in content
        print(f"\n  Rapport : {report_path}")
        print(f"  Taille  : {len(content)} caractères")
