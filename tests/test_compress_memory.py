"""Testes para skill compress-memory.

Garante:
- Blacklist absoluta funciona (CLAUDE.md, MEMORY.md, specs, etc.)
- Detecta spec markers (Given/When/Then, [NEEDS CLARIFICATION], REQ-###)
- Preserva code blocks, URLs, paths, headings, tabelas, frontmatter
- Remove filler PT-BR e EN
- Cria backup .original.md
- Idempotencia (rodar 2x nao comprime mais)
- Dry-run nao escreve
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(os.environ["HARNESS_PLUGIN_ROOT"])
COMPRESS_PATH = ROOT / "skills" / "compress-memory" / "compress.py"


@pytest.fixture(scope="module")
def compress_mod():
    spec = importlib.util.spec_from_file_location("compress_memory", COMPRESS_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["compress_memory"] = mod
    spec.loader.exec_module(mod)
    return mod


def _write(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


class TestBlacklist:
    def test_claude_md_blocked(self, compress_mod, tmp_path):
        p = _write(tmp_path, "CLAUDE.md", "qualquer conteudo")
        with pytest.raises(compress_mod.CompressError, match="blacklist"):
            compress_mod.compress_file(p)

    def test_memory_md_blocked(self, compress_mod, tmp_path):
        p = _write(tmp_path, "MEMORY.md", "- entry")
        with pytest.raises(compress_mod.CompressError, match="blacklist"):
            compress_mod.compress_file(p)

    def test_core_memories_blocked(self, compress_mod, tmp_path):
        p = _write(tmp_path, "core-memories.md", "decisao importante")
        with pytest.raises(compress_mod.CompressError, match="blacklist"):
            compress_mod.compress_file(p)

    def test_readme_blocked(self, compress_mod, tmp_path):
        p = _write(tmp_path, "README.md", "# Projeto")
        with pytest.raises(compress_mod.CompressError, match="blacklist"):
            compress_mod.compress_file(p)

    def test_spec_suffix_blocked(self, compress_mod, tmp_path):
        p = _write(tmp_path, "feature-x-spec.md", "stuff")
        with pytest.raises(compress_mod.CompressError):
            compress_mod.compress_file(p)

    def test_design_suffix_blocked(self, compress_mod, tmp_path):
        p = _write(tmp_path, "feature-x-design.md", "stuff")
        with pytest.raises(compress_mod.CompressError):
            compress_mod.compress_file(p)

    def test_verification_suffix_blocked(self, compress_mod, tmp_path):
        p = _write(tmp_path, "feature-x-verification.md", "stuff")
        with pytest.raises(compress_mod.CompressError):
            compress_mod.compress_file(p)

    def test_claude_variant_blocked(self, compress_mod, tmp_path):
        p = _write(tmp_path, "CLAUDE.original.md", "regras")
        with pytest.raises(compress_mod.CompressError):
            compress_mod.compress_file(p)

    def test_specs_path_blocked(self, compress_mod, tmp_path):
        sub = tmp_path / "docs" / "specs"
        sub.mkdir(parents=True)
        p = sub / "any.md"
        p.write_text("conteudo", encoding="utf-8")
        with pytest.raises(compress_mod.CompressError, match="critico"):
            compress_mod.compress_file(p)

    def test_normal_md_allowed(self, compress_mod, tmp_path):
        p = _write(tmp_path, "recent.md", "basicamente um conteudo simples")
        result = compress_mod.compress_file(p, dry_run=True)
        assert result.compressed_chars < result.original_chars


class TestSpecMarkers:
    def test_given_when_then_blocks(self, compress_mod, tmp_path):
        p = _write(
            tmp_path,
            "fake.md",
            "Some text\nGiven user is logged in\nWhen he clicks\nThen redirect",
        )
        with pytest.raises(compress_mod.CompressError, match="spec"):
            compress_mod.compress_file(p)

    def test_needs_clarification_blocks(self, compress_mod, tmp_path):
        p = _write(tmp_path, "fake.md", "Decision: [NEEDS CLARIFICATION] something")
        with pytest.raises(compress_mod.CompressError, match="spec"):
            compress_mod.compress_file(p)

    def test_req_id_blocks(self, compress_mod, tmp_path):
        p = _write(tmp_path, "fake.md", "Requirement REQ-001 must be enforced")
        with pytest.raises(compress_mod.CompressError, match="spec"):
            compress_mod.compress_file(p)

    def test_ac_id_blocks(self, compress_mod, tmp_path):
        p = _write(tmp_path, "fake.md", "Acceptance AC-042 must pass")
        with pytest.raises(compress_mod.CompressError, match="spec"):
            compress_mod.compress_file(p)


class TestPreservation:
    def test_code_block_preserved(self, compress_mod):
        text = "Texto com basicamente filler\n```python\nbasically = 'string'\n```\n"
        out = compress_mod.compress_text(text)
        assert "basically = 'string'" in out
        assert "basicamente" not in out.split("```")[0]

    def test_inline_code_preserved(self, compress_mod):
        text = "Use `basically` no codigo, mas basicamente nao no texto."
        out = compress_mod.compress_text(text)
        assert "`basically`" in out

    def test_url_preserved(self, compress_mod):
        text = "Veja basicamente https://example.com/path para detalhes."
        out = compress_mod.compress_text(text)
        assert "https://example.com/path" in out

    def test_heading_preserved(self, compress_mod):
        text = "# basicamente Importante\nbasicamente filler.\n"
        out = compress_mod.compress_text(text)
        assert "# basicamente Importante" in out

    def test_table_preserved(self, compress_mod):
        text = "| col1 | col2 |\n| basicamente | really |\n"
        out = compress_mod.compress_text(text)
        assert "| basicamente | really |" in out

    def test_frontmatter_preserved(self, compress_mod):
        text = "---\nname: foo\nbasically: true\n---\nbasicamente conteudo.\n"
        out = compress_mod.compress_text(text)
        assert "basically: true" in out

    def test_path_preserved(self, compress_mod):
        text = "Edite basicamente C:\\Users\\Leo\\file.md hoje."
        out = compress_mod.compress_text(text)
        assert "C:\\Users\\Leo\\file.md" in out

    def test_version_preserved(self, compress_mod):
        text = "Atualize basicamente para v2.3.1 hoje."
        out = compress_mod.compress_text(text)
        assert "v2.3.1" in out

    def test_date_preserved(self, compress_mod):
        text = "Em 2026-04-27 basicamente lancamos."
        out = compress_mod.compress_text(text)
        assert "2026-04-27" in out


class TestFillerRemoval:
    def test_pt_filler_removed(self, compress_mod):
        text = "Eu acho que basicamente isso simplesmente funciona."
        out = compress_mod.compress_text(text)
        assert "basicamente" not in out
        assert "simplesmente" not in out
        assert "eu acho que" not in out.lower()

    def test_en_filler_removed(self, compress_mod):
        text = "I think this basically just works actually."
        out = compress_mod.compress_text(text)
        assert "basically" not in out.lower()
        assert "i think" not in out.lower()
        assert "actually" not in out.lower()

    def test_leading_filler_removed(self, compress_mod):
        text = "Entao, vamos rodar.\nWell, vamos rodar.\n"
        out = compress_mod.compress_text(text)
        assert not out.startswith("Entao,")
        assert "Well, vamos" not in out


class TestIdempotency:
    def test_double_compress_stable(self, compress_mod):
        text = "Eu acho que basicamente isso simplesmente funciona muito bem."
        once = compress_mod.compress_text(text)
        twice = compress_mod.compress_text(once)
        assert once == twice


class TestFileOps:
    def test_backup_created(self, compress_mod, tmp_path):
        p = _write(tmp_path, "recent.md", "basicamente um teste\n")
        result = compress_mod.compress_file(p, backup=True)
        assert result.backup_path is not None
        assert result.backup_path.exists()
        assert "basicamente" in result.backup_path.read_text(encoding="utf-8")

    def test_dry_run_no_write(self, compress_mod, tmp_path):
        original = "basicamente teste\n"
        p = _write(tmp_path, "recent.md", original)
        result = compress_mod.compress_file(p, dry_run=True)
        assert p.read_text(encoding="utf-8") == original
        assert result.backup_path is None

    def test_no_backup_flag(self, compress_mod, tmp_path):
        p = _write(tmp_path, "recent.md", "basicamente teste\n")
        result = compress_mod.compress_file(p, backup=False)
        assert result.backup_path is None
        assert not (tmp_path / "recent.original.md").exists()

    def test_savings_reported(self, compress_mod, tmp_path):
        p = _write(
            tmp_path,
            "recent.md",
            "basicamente eu acho que isso simplesmente funciona realmente bem.\n" * 5,
        )
        result = compress_mod.compress_file(p, dry_run=True)
        assert result.saved_chars > 0
        assert result.saved_pct > 0

    def test_missing_file_raises(self, compress_mod, tmp_path):
        with pytest.raises(compress_mod.CompressError, match="nao existe"):
            compress_mod.compress_file(tmp_path / "missing.md")


class TestCLI:
    def test_cli_dry_run(self, compress_mod, tmp_path, capsys):
        p = _write(tmp_path, "recent.md", "basicamente teste\n")
        rc = compress_mod.main([str(p), "--dry-run"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Saved" in captured.out
        assert p.read_text(encoding="utf-8") == "basicamente teste\n"

    def test_cli_blacklist_returns_2(self, compress_mod, tmp_path, capsys):
        p = _write(tmp_path, "CLAUDE.md", "regras")
        rc = compress_mod.main([str(p)])
        assert rc == 2
        captured = capsys.readouterr()
        assert "REJEITADO" in captured.err
