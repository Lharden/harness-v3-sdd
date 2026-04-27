#!/usr/bin/env python3
"""compress-memory — Compressao segura de arquivos de memoria.

Inspirado no caveman-compress (https://github.com/JuliusBrussee/caveman),
adaptado com blacklist critica para nunca tocar em specs, CLAUDE.md,
MEMORY.md, core-memories.md, ou qualquer arquivo do plugin system.

Uso:
    python compress.py <arquivo>
    python compress.py <arquivo> --dry-run
    python compress.py <arquivo> --no-backup
    python compress.py <arquivo> --stats
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

BLACKLIST_NAMES = frozenset({
    "CLAUDE.md",
    "MEMORY.md",
    "core-memories.md",
    "README.md",
    "plugin.json",
    "settings.json",
})

BLACKLIST_PATH_PARTS = (
    "/docs/specs/",
    "\\docs\\specs\\",
    "/.claude-plugin/",
    "\\.claude-plugin\\",
)

SPEC_MARKERS = (
    "[NEEDS CLARIFICATION]",
    "Given/When/Then",
    re.compile(r"^\s*Given\s+", re.MULTILINE),
    re.compile(r"\bREQ-\d{3}\b"),
    re.compile(r"\bAC-\d{3}\b"),
)

FILLER_PT = [
    r"\bbasicamente\b",
    r"\bsimplesmente\b",
    r"\bna verdade\b",
    r"\bde fato\b",
    r"\brealmente\b",
    r"\btalvez\b",
    r"\beu acho que\b",
    r"\beu acredito que\b",
    r"\bacho que\b",
    r"\bme parece que\b",
    r"\bpor favor\b",
    r"\bse voc[eê] puder\b",
    r"\bse n[aã]o for inc[oô]modo\b",
]

FILLER_EN = [
    r"\bbasically\b",
    r"\bsimply\b",
    r"\bactually\b",
    r"\breally\b",
    r"\bperhaps\b",
    r"\bkind of\b",
    r"\bsort of\b",
    r"\bI think\b",
    r"\bI believe\b",
    r"\bit might\b",
    r"\bcould potentially\b",
    r"\bit seems(?: that)?\b",
    r"\bplease\b",
    r"\bif you don'?t mind\b",
    r"\bwould you mind\b",
]

LEADING_FILLER = re.compile(
    r"^(?:Ent[aã]o|Bom|Bem|Agora|Olha|So|Well|Now|Look),\s+",
    re.IGNORECASE,
)

PRESERVE_LINE_PATTERNS = (
    re.compile(r"^\s*#"),                          # headings
    re.compile(r"^\s*[-*+]\s+\["),                 # task lists
    re.compile(r"^\s*\|"),                         # tables
    re.compile(r"^\s*```"),                        # fences
    re.compile(r"^\s*\$\s"),                       # shell prompts
    re.compile(r"^---\s*$"),                       # frontmatter
    re.compile(r"^\s*<[^>]+>"),                    # HTML/XML tags
)

INLINE_PRESERVE = re.compile(
    r"(`[^`\n]*`|"                                 # inline code
    r"https?://\S+|"                               # URLs
    r"[A-Za-z]:[\\/][\w\\/.\-]+|"                  # Windows abs paths
    r"(?:^|\s)[\w\-./]+/[\w\-./]+|"                # unix-ish paths
    r"\bv?\d+\.\d+(?:\.\d+)?\b|"                   # versions
    r"\b\d{4}-\d{2}-\d{2}\b|"                      # dates
    r"--?[A-Za-z][\w\-]*)"                         # CLI flags
)


@dataclass
class CompressResult:
    input_path: Path
    backup_path: Path | None
    original_chars: int
    compressed_chars: int
    original_lines: int
    compressed_lines: int

    @property
    def saved_chars(self) -> int:
        return self.original_chars - self.compressed_chars

    @property
    def saved_pct(self) -> float:
        if self.original_chars == 0:
            return 0.0
        return 100.0 * self.saved_chars / self.original_chars


class CompressError(Exception):
    """Raised when compression must be refused."""


def is_blacklisted(path: Path) -> tuple[bool, str]:
    name = path.name
    if name in BLACKLIST_NAMES:
        return True, f"nome em blacklist absoluta: {name}"
    posix = path.as_posix()
    raw = str(path)
    for marker in BLACKLIST_PATH_PARTS:
        if marker in posix or marker in raw:
            return True, f"path contem marker critico: {marker}"
    if name.startswith("CLAUDE") and name.endswith(".md"):
        return True, f"variante de CLAUDE.md: {name}"
    if name.endswith("-spec.md") or name.endswith("-spec-light.md"):
        return True, "spec formal nao deve ser comprimida"
    if name.endswith("-design.md") or name.endswith("-verification.md"):
        return True, "design/verification doc nao deve ser comprimido"
    return False, ""


def has_spec_markers(text: str) -> tuple[bool, str]:
    for marker in SPEC_MARKERS:
        if isinstance(marker, str):
            if marker in text:
                return True, f"contem marker: {marker!r}"
        else:
            if marker.search(text):
                return True, f"contem padrao: {marker.pattern}"
    return False, ""


def _mask_inline(line: str) -> tuple[str, list[str]]:
    masks: list[str] = []

    def _replace(match: re.Match[str]) -> str:
        masks.append(match.group(0))
        return f"\x00{len(masks) - 1}\x00"

    masked = INLINE_PRESERVE.sub(_replace, line)
    return masked, masks


def _unmask_inline(line: str, masks: list[str]) -> str:
    def _restore(match: re.Match[str]) -> str:
        idx = int(match.group(1))
        return masks[idx]

    return re.sub(r"\x00(\d+)\x00", _restore, line)


def _compress_line(line: str) -> str:
    if not line.strip():
        return line
    for pattern in PRESERVE_LINE_PATTERNS:
        if pattern.search(line):
            return line

    masked, masks = _mask_inline(line)

    for pat in FILLER_PT + FILLER_EN:
        masked = re.sub(pat, "", masked, flags=re.IGNORECASE)

    masked = LEADING_FILLER.sub("", masked)
    masked = re.sub(r"[ \t]{2,}", " ", masked)
    masked = re.sub(r"\s+([.,;:!?])", r"\1", masked)
    masked = re.sub(r"^\s+", "", masked) if masked != line else masked

    return _unmask_inline(masked, masks)


def compress_text(text: str) -> str:
    in_fence = False
    in_frontmatter = False
    frontmatter_done = False
    out_lines: list[str] = []
    lines = text.splitlines(keepends=False)
    for idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()
        if stripped == "---":
            if idx == 0 and not frontmatter_done:
                in_frontmatter = True
                out_lines.append(raw_line)
                continue
            if in_frontmatter:
                in_frontmatter = False
                frontmatter_done = True
                out_lines.append(raw_line)
                continue
        if in_frontmatter:
            out_lines.append(raw_line)
            continue
        if stripped.startswith("```"):
            in_fence = not in_fence
            out_lines.append(raw_line)
            continue
        if in_fence:
            out_lines.append(raw_line)
            continue
        out_lines.append(_compress_line(raw_line))
    if text.endswith("\n"):
        return "\n".join(out_lines) + "\n"
    return "\n".join(out_lines)


def compress_file(
    path: Path,
    *,
    dry_run: bool = False,
    backup: bool = True,
) -> CompressResult:
    if not path.exists():
        raise CompressError(f"arquivo nao existe: {path}")
    if not path.is_file():
        raise CompressError(f"nao e arquivo: {path}")
    blocked, reason = is_blacklisted(path)
    if blocked:
        raise CompressError(f"REJEITADO: {path.name} - {reason}")

    original = path.read_text(encoding="utf-8")
    spec_hit, spec_reason = has_spec_markers(original)
    if spec_hit:
        raise CompressError(
            f"REJEITADO: {path.name} parece ser spec/AC formal "
            f"({spec_reason}). Use --force-spec se tem certeza (nao implementado por seguranca)."
        )

    compressed = compress_text(original)

    backup_path: Path | None = None
    if not dry_run:
        if backup:
            backup_path = path.with_suffix(".original" + path.suffix)
            backup_path.write_text(original, encoding="utf-8")
        path.write_text(compressed, encoding="utf-8")

    return CompressResult(
        input_path=path,
        backup_path=backup_path,
        original_chars=len(original),
        compressed_chars=len(compressed),
        original_lines=original.count("\n") + (0 if original.endswith("\n") else 1),
        compressed_lines=compressed.count("\n") + (0 if compressed.endswith("\n") else 1),
    )


def _print_result(result: CompressResult, dry_run: bool) -> None:
    prefix = "[compress-memory:dry-run]" if dry_run else "[compress-memory]"
    print(
        f"{prefix} Input: {result.input_path.name} "
        f"({result.original_lines} lines, {result.original_chars} chars)"
    )
    if result.backup_path:
        print(f"{prefix} Backup: {result.backup_path.name}")
    print(
        f"{prefix} Output: {result.input_path.name} "
        f"({result.compressed_lines} lines, {result.compressed_chars} chars)"
    )
    print(
        f"{prefix} Saved: {result.saved_pct:.1f}% "
        f"({result.saved_chars} chars removed)"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="compress-memory",
        description="Comprime arquivos de memoria secundarios com seguranca.",
    )
    parser.add_argument("path", help="Arquivo a comprimir")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview: nao escreve nada",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Nao cria .original.md (NAO recomendado)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="So imprime estatisticas (equivalente a --dry-run)",
    )
    args = parser.parse_args(argv)

    dry_run = args.dry_run or args.stats
    try:
        result = compress_file(
            Path(args.path),
            dry_run=dry_run,
            backup=not args.no_backup,
        )
    except CompressError as exc:
        print(f"[compress-memory:ERROR] {exc}", file=sys.stderr)
        return 2

    _print_result(result, dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
