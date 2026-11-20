"""
Unit tests for Phase 2 C2 (Advanced Search) and D2 (Editable Settings / YAML editor).
"""

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.routes.settings import router as settings_router
from api.routes.vault import router as vault_router
from config import AuroraConfig
from core.indexer import VaultIndexer
from data.models import Note
from utils.yaml_editor import edit_yaml_value


# ─── Helpers ────────────────────────────────────────────────────────────────


def _make_note(
    path: str,
    title: str,
    content: str,
    tags: list[str],
    created: str,
    modified: str,
) -> Note:
    folder = "/".join(path.split("/")[:-1])
    return Note(
        id=path,
        path=path,
        filename=path.split("/")[-1],
        folder=folder,
        title=title,
        content=content,
        clean_content=content,
        tags=tags,
        created_at=datetime.fromisoformat(created),
        modified_at=datetime.fromisoformat(modified),
        word_count=len(content.split()),
    )


def _build_vault_app() -> TestClient:
    notes = {
        "Projects/AI/Habits.md": _make_note(
            "Projects/AI/Habits.md",
            "Habits",
            "# Habits\n\n## Cue Loop\nDopamine spikes on cues.\n\n## Sleep\nRest helps memory.",
            ["neuroscience", "habits"],
            "2026-01-10T09:00:00",
            "2026-05-01T10:00:00",
        ),
        "Projects/Web/React.md": _make_note(
            "Projects/Web/React.md",
            "React Notes",
            "# React Notes\n\nHooks and state management.",
            ["frontend", "react"],
            "2026-02-15T09:00:00",
            "2026-03-20T10:00:00",
        ),
        "Journal/Daily.md": _make_note(
            "Journal/Daily.md",
            "Daily Log",
            "# Daily Log\n\nBuilt a better dopamine habit today.",
            ["habits", "journal"],
            "2026-06-01T09:00:00",
            "2026-06-05T10:00:00",
        ),
    }

    vm = MagicMock()
    vm.notes_cache = notes

    async def fake_search(query: str, limit: int = 10):
        q = query.lower()
        return [
            n
            for n in notes.values()
            if q in n.title.lower() or q in n.clean_content.lower() or any(q in t.lower() for t in n.tags)
        ][:limit]

    vm.search_notes = AsyncMock(side_effect=fake_search)

    indexer = VaultIndexer(vm)
    for p, note in notes.items():
        from core.chunker import chunk_note
        indexer.chunks[p] = chunk_note(note)

    app = FastAPI()
    app.include_router(vault_router, prefix="/api/vault")
    app.state.vault_manager = vm
    app.state.indexer = indexer
    return TestClient(app)


# ─── C2: Advanced Search Tests ──────────────────────────────────────────────


class TestAdvancedSearch:
    def test_search_returns_section_snippets(self):
        client = _build_vault_app()
        r = client.post("/api/vault/search", json={"query": "dopamine", "include_sections": True})
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        habits = next(x for x in body["results"] if x["path"] == "Projects/AI/Habits.md")
        assert len(habits["sections"]) >= 1
        assert "Cue Loop" in habits["sections"][0]["heading"]

    def test_filter_by_nested_folder_and_tag(self):
        client = _build_vault_app()
        r = client.post(
            "/api/vault/search",
            json={"query": "", "folder": "Projects/AI", "tags": ["habits"]},
        )
        assert r.status_code == 200
        paths = [x["path"] for x in r.json()["results"]]
        assert paths == ["Projects/AI/Habits.md"]

    def test_filter_by_parent_folder(self):
        client = _build_vault_app()
        r = client.post("/api/vault/search", json={"query": "", "folder": "Projects"})
        assert r.status_code == 200
        paths = {x["path"] for x in r.json()["results"]}
        assert paths == {"Projects/AI/Habits.md", "Projects/Web/React.md"}

    def test_filter_by_modified_and_created_date_range(self):
        client = _build_vault_app()
        r_mod = client.post(
            "/api/vault/search",
            json={"query": "", "date_from": "2026-04-01", "date_to": "2026-05-31", "date_field": "modified"},
        )
        assert r_mod.status_code == 200
        assert [x["path"] for x in r_mod.json()["results"]] == ["Projects/AI/Habits.md"]

        r_cre = client.post(
            "/api/vault/search",
            json={"query": "", "date_from": "2026-06-01", "date_field": "created"},
        )
        assert r_cre.status_code == 200
        assert [x["path"] for x in r_cre.json()["results"]] == ["Journal/Daily.md"]

    def test_invalid_date_returns_400(self):
        client = _build_vault_app()
        r = client.post("/api/vault/search", json={"query": "", "date_from": "not-a-date"})
        assert r.status_code == 400


# ─── D2: YAML Editor & Editable Settings Tests ──────────────────────────────


SAMPLE_YAML = """\
vault:
  path: "E:\\\\OldVault"
  supported_extensions:
    - ".md"

llm:
  active_provider: "gemini"
  providers:
    openai:
      config:
        api_key: ""
        default_model: "gpt-4o-mini"
    gemini:
      config:
        api_key: "test-key"
        default_model: "gemini-3.6-flash"
    ollama:
      config:
        base_url: "http://localhost:11434"
        default_model: "llama3.1"

privacy:
  enabled: true
  enabled_categories:
    - person_name
    - email
    - phone

skills:
  builtin:
    linker:
      enabled: true
    tag_manager:
      enabled: false
"""


class TestYamlEditor:
    def test_windows_path_escapes_cleanly(self, tmp_path: Path):
        f = tmp_path / "aurora.yaml"
        f.write_text(SAMPLE_YAML, encoding="utf-8")

        ok = edit_yaml_value(str(f), ["vault", "path"], r"E:\Vault\My Notes", backup=False)
        assert ok is True
        parsed = yaml.safe_load(f.read_text(encoding="utf-8"))
        assert parsed["vault"]["path"] == r"E:\Vault\My Notes"

    def test_multiline_list_edit_produces_valid_yaml(self, tmp_path: Path):
        f = tmp_path / "aurora.yaml"
        f.write_text(SAMPLE_YAML, encoding="utf-8")

        ok = edit_yaml_value(str(f), ["privacy", "enabled_categories"], ["email", "api_key"], backup=False)
        assert ok is True
        parsed = yaml.safe_load(f.read_text(encoding="utf-8"))
        assert parsed["privacy"]["enabled_categories"] == ["email", "api_key"]

        # Emptying the list also stays valid YAML
        ok = edit_yaml_value(str(f), ["privacy", "enabled_categories"], [], backup=False)
        assert ok is True
        parsed = yaml.safe_load(f.read_text(encoding="utf-8"))
        assert parsed["privacy"]["enabled_categories"] == []

    def test_nested_key_isolation(self, tmp_path: Path):
        f = tmp_path / "aurora.yaml"
        f.write_text(SAMPLE_YAML, encoding="utf-8")

        ok = edit_yaml_value(str(f), ["llm", "providers", "gemini", "config", "default_model"], "gemini-3.1-flash-lite", backup=False)
        assert ok is True
        parsed = yaml.safe_load(f.read_text(encoding="utf-8"))
        assert parsed["llm"]["providers"]["gemini"]["config"]["default_model"] == "gemini-3.1-flash-lite"
        # OpenAI's default_model was untouched
        assert parsed["llm"]["providers"]["openai"]["config"]["default_model"] == "gpt-4o-mini"


class TestSettingsRoutes:
    def _make_client(self, tmp_path: Path):
        yaml_file = tmp_path / "aurora.yaml"
        yaml_file.write_text(SAMPLE_YAML, encoding="utf-8")
        cfg = AuroraConfig(str(yaml_file))

        registry = MagicMock()
        loaded = {"linker": SimpleNamespace(metadata=SimpleNamespace(id="linker", name="Linker", description="Links"))}
        registry.get_skill = lambda sid: loaded.get(sid)
        registry.get_enabled_skills = lambda: list(loaded.values())
        registry.unregister = lambda sid: loaded.pop(sid, None)

        async def load_and_register(sid, *args):
            loaded[sid] = SimpleNamespace(metadata=SimpleNamespace(id=sid, name=sid, description=""))

        registry.load_and_register = AsyncMock(side_effect=load_and_register)

        llm_client = MagicMock()
        llm_client.switch_provider = MagicMock()

        sanitizer = SimpleNamespace(detector=SimpleNamespace(enabled_categories=["PERSON_NAME", "EMAIL", "PHONE"]))

        app = FastAPI()
        app.include_router(settings_router, prefix="/api/settings")
        app.state.config = cfg
        app.state.skill_registry = registry
        app.state.llm_client = llm_client
        app.state.vault_manager = MagicMock()
        app.state.sanitizer = sanitizer
        return TestClient(app), cfg, llm_client, sanitizer

    def test_put_updates_yaml_reloads_and_hot_swaps(self, tmp_path: Path):
        vault_dir = tmp_path / "new_vault"
        vault_dir.mkdir()
        client, cfg, llm_client, sanitizer = self._make_client(tmp_path)

        res = client.put(
            "/api/settings/",
            json={
                "llm_active_provider": "ollama",
                "llm_model": "llama3.2",
                "privacy_categories": ["email", "api_key"],
                "skills_enabled": {"linker": False, "tag_manager": True},
                "vault_path": str(vault_dir),
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "ok"
        assert body["restart_required"] is True  # vault_path changed
        assert body["settings"]["llm"]["active_provider"] == "ollama"
        assert body["settings"]["llm"]["providers"]["ollama"]["model"] == "llama3.2"
        assert body["settings"]["privacy"]["categories"] == ["email", "api_key"]
        assert body["settings"]["vault"]["path"] == str(vault_dir)
        assert sanitizer.detector.enabled_categories == ["EMAIL", "API_KEY"]
        llm_client.switch_provider.assert_called_once()

        # Subsequent GET reflects the persisted changes immediately
        after = client.get("/api/settings/").json()
        assert after["llm"]["active_provider"] == "ollama"
        assert after["skills"]["loaded"] == ["tag_manager"]

    def test_invalid_vault_dir_reports_error(self, tmp_path: Path):
        client, *_ = self._make_client(tmp_path)
        res = client.put("/api/settings/", json={"vault_path": str(tmp_path / "does_not_exist")})
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "error"
        assert any("does not exist" in e.lower() for e in body["errors"])
