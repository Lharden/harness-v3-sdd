"""Testes para hook context7-trigger.

Garante:
- Detecta libs/frameworks conhecidos (true positive)
- Ignora prompts genericos (true negative)
- Skip se prompt ja menciona context7
- JSON malformado retorna sem crash
- Verb-only path (perguntas tipo "como configurar X")
- Mensagem tem formato esperado
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(os.environ["HARNESS_PLUGIN_ROOT"])
HOOK_PATH = ROOT / "hooks" / "context7-trigger.py"


@pytest.fixture(scope="module")
def hook_mod():
    spec = importlib.util.spec_from_file_location("context7_trigger", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["context7_trigger"] = mod
    spec.loader.exec_module(mod)
    return mod


class TestDetect:
    def test_detects_react(self, hook_mod):
        assert "react" in hook_mod.detect("como usar react com hooks")

    def test_detects_fastapi(self, hook_mod):
        assert "fastapi" in hook_mod.detect("instalar fastapi com pydantic")

    def test_detects_multiple(self, hook_mod):
        hits = hook_mod.detect("nextjs com prisma e postgres")
        assert "nextjs" in hits
        assert "prisma" in hits
        assert "postgres" in hits

    def test_ignores_generic(self, hook_mod):
        assert hook_mod.detect("refatora essa funcao em main.py") == []

    def test_ignores_short(self, hook_mod):
        assert hook_mod.detect("oi") == []

    def test_skip_if_context7_mentioned(self, hook_mod):
        assert hook_mod.detect("ja usei context7 para react") == []

    def test_skip_if_resolve_library_id(self, hook_mod):
        assert hook_mod.detect("rodar resolve-library-id pra prisma") == []

    def test_verb_only_fallback(self, hook_mod):
        hits = hook_mod.detect("qual a api correta pra essa lib obscura")
        assert hits == ["__verb_only__"]

    def test_verb_only_setup(self, hook_mod):
        hits = hook_mod.detect("getting started instructions please")
        assert hits == ["__verb_only__"]

    def test_case_insensitive(self, hook_mod):
        assert "react" in hook_mod.detect("REACT hooks")

    def test_anthropic_sdk_detected(self, hook_mod):
        assert "anthropic sdk" in hook_mod.detect("integrar anthropic sdk no app")

    def test_aws_lambda_detected(self, hook_mod):
        assert "aws lambda" in hook_mod.detect("deploy aws lambda hoje")


class TestBuildMessage:
    def test_libs_message_format(self, hook_mod):
        msg = hook_mod.build_message(["react", "next.js"])
        assert "[context7-hint]" in msg
        assert "react" in msg
        assert "OBRIGATORIO" in msg
        assert "resolve-library-id" in msg
        assert "query-docs" in msg

    def test_verb_only_message(self, hook_mod):
        msg = hook_mod.build_message(["__verb_only__"])
        assert "[context7-hint]" in msg
        assert "docs/setup/versao" in msg or "considere" in msg.lower()

    def test_message_truncates_at_5(self, hook_mod):
        many = ["react", "vue", "angular", "svelte", "nextjs", "remix", "astro"]
        msg = hook_mod.build_message(many)
        assert msg.count(",") <= 4 or "remix" not in msg


def _run_hook_with_stdin(hook_mod, payload: dict, monkeypatch, capsys) -> tuple[int, str]:
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    rc = hook_mod.main()
    captured = capsys.readouterr()
    return rc, captured.out


class TestMainEntry:
    def test_libs_emits_json(self, hook_mod, monkeypatch, capsys):
        rc, out = _run_hook_with_stdin(
            hook_mod,
            {"prompt": "como configurar fastapi com pydantic"},
            monkeypatch,
            capsys,
        )
        assert rc == 0
        parsed = json.loads(out)
        assert parsed["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
        assert "context7-hint" in parsed["hookSpecificOutput"]["additionalContext"]
        assert "fastapi" in parsed["hookSpecificOutput"]["additionalContext"]

    def test_generic_emits_nothing(self, hook_mod, monkeypatch, capsys):
        rc, out = _run_hook_with_stdin(
            hook_mod,
            {"prompt": "refatora essa funcao em main.py"},
            monkeypatch,
            capsys,
        )
        assert rc == 0
        assert out == ""

    def test_empty_prompt(self, hook_mod, monkeypatch, capsys):
        rc, out = _run_hook_with_stdin(
            hook_mod,
            {"prompt": ""},
            monkeypatch,
            capsys,
        )
        assert rc == 0
        assert out == ""

    def test_missing_prompt_field(self, hook_mod, monkeypatch, capsys):
        rc, out = _run_hook_with_stdin(
            hook_mod,
            {"otherField": "value"},
            monkeypatch,
            capsys,
        )
        assert rc == 0
        assert out == ""

    def test_malformed_json_no_crash(self, hook_mod, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("not-json{{"))
        rc = hook_mod.main()
        assert rc == 0

    def test_skip_when_already_using_context7(self, hook_mod, monkeypatch, capsys):
        rc, out = _run_hook_with_stdin(
            hook_mod,
            {"prompt": "rode resolve-library-id pra prisma"},
            monkeypatch,
            capsys,
        )
        assert rc == 0
        assert out == ""
