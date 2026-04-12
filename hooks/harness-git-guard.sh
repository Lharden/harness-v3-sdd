#!/usr/bin/env bash
# harness-git-guard.sh — PreToolUse:Bash hook
# Protects against destructive git operations.
# Reads JSON from stdin (field: tool_input.command)
# Exit 2 = BLOCK, Exit 0 = PASS (with optional warning)

set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" 2>/dev/null || echo "")

# If no command extracted, pass through
if [[ -z "$COMMAND" ]]; then
  exit 0
fi

# --- HARD BLOCK (exit 2) ---

# git push --force / --force-with-lease
if echo "$COMMAND" | grep -qE 'git\s+push\s+.*--force'; then
  echo '{"decision":"block","reason":"BLOCKED: git push --force e uma operacao destrutiva. Use git push sem --force."}' >&2
  exit 2
fi

# git reset --hard
if echo "$COMMAND" | grep -qE 'git\s+reset\s+.*--hard'; then
  echo '{"decision":"block","reason":"BLOCKED: git reset --hard descarta alteracoes irrecuperavelmente. Use git stash ou git reset --soft."}' >&2
  exit 2
fi

# git clean -f / -fd
if echo "$COMMAND" | grep -qE 'git\s+clean\s+.*-[a-zA-Z]*f'; then
  echo '{"decision":"block","reason":"BLOCKED: git clean -f remove arquivos nao-rastreados permanentemente."}' >&2
  exit 2
fi

# git branch -D (uppercase D only)
if echo "$COMMAND" | grep -qE 'git\s+branch\s+.*-[a-zA-Z]*D'; then
  echo '{"decision":"block","reason":"BLOCKED: git branch -D forca exclusao de branch sem verificar merge. Use git branch -d."}' >&2
  exit 2
fi

# git checkout .
if echo "$COMMAND" | grep -qE 'git\s+checkout\s+\.\s*$'; then
  echo '{"decision":"block","reason":"BLOCKED: git checkout . descarta todas as alteracoes locais nao commitadas."}' >&2
  exit 2
fi

# git restore .
if echo "$COMMAND" | grep -qE 'git\s+restore\s+\.\s*$'; then
  echo '{"decision":"block","reason":"BLOCKED: git restore . descarta todas as alteracoes locais nao commitadas."}' >&2
  exit 2
fi

# --- WARNING (exit 0, print message) ---

# git push (without --force, already filtered above)
if echo "$COMMAND" | grep -qE 'git\s+push(\s|$)'; then
  echo "## Harness Warning: git push detectado. Confirme com o usuario antes de prosseguir."
  exit 0
fi

# --- PASS ---
exit 0
