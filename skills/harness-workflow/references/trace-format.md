# Trace Format — Referencia

## Localizacao

- Sessao atual: `~/.claude/harness/trace-current.md`
- Historico: `~/.claude/harness/traces/YYYY-MM-DD-HHmm.md`
- Resumos L2: `~/.claude/harness/summaries/YYYY-MM-DD-HHmm-summary.md`

## Mecanismo de Escrita

Usar tool `Edit` (append ao final do arquivo) para cada transicao de fase.
Cada entrada custa 1 tool call. Custo aceitavel para auditabilidade.

## Rotacao

Na fase INIT de tarefa L1+, verificar data do header de trace-current.md:
- Se data diferente de hoje: rotacionar
  1. mv trace-current.md → traces/YYYY-MM-DD-HHmm.md (via Bash)
  2. Criar novo trace-current.md com header atualizado
  3. Remover traces/ com >30 dias

## Retomada pos-compact

Ler ultimas 20 linhas de trace-current.md (Read com offset) para identificar fase atual.
O diretorio harness/ NAO e indexado por context-mode — usar Read direto.

## Exemplo Completo (L2)

# Harness Trace — 2026-03-20 14:30

## [INIT] 14:30:12 | L2
- Tarefa: Implementar endpoint de autenticacao OAuth2
- Criterio: testes passam, endpoint responde 200 com token valido
- Verify condicional: pytest + regressao + code-reviewer
- Arquivos provaveis: auth.py, routes.py, test_auth.py

## [PLAN] 14:31:05
- Fase 1: criar modelo de token → criterio: migracao ok
- Fase 2: implementar endpoint → criterio: rota responde
- Fase 3: testes → criterio: pytest pass

## [EXECUTE:FASE-1] 14:32:00
- Arquivos: models/token.py (criado), alembic/versions/003.py (criado)
- Resultado: sucesso

## [EXECUTE:FASE-1→FASE-2] 14:35:00
- Criterio atendido: migracao executada sem erro

## [EXECUTE:FASE-2] 14:35:30
- Arquivos: routes/auth.py (mod), config.py (mod)
- Resultado: sucesso

## [VERIFY] 14:40:00
- ruff: pass
- pyright: pass (0 errors)
- pytest: FAIL (1 failed: test_token_expiry)
- Acao: retornando para EXECUTE

## [EXECUTE:FASE-2] 14:42:00
- Correcao: token expiry calculado errado
- Arquivos: routes/auth.py (mod)

## [VERIFY] 14:44:00
- ruff: pass
- pyright: pass
- pytest: pass (8 passed, 0 failed)
- review: code-reviewer — 0 criticos

## [DONE] 14:45:00
- Resultado: concluido
- Arquivos: models/token.py, routes/auth.py, config.py, test_auth.py, alembic/003.py
- Fases: 3/3
- Verificacao: pass (2a tentativa)
- Retrabalho: 1 ciclo VERIFY→EXECUTE
- Resumo: Endpoint OAuth2 implementado com modelo de token, rota POST /auth/token, e 8 testes.

## Formato do Resumo Consolidado (summaries/)

# Resumo: {titulo}
- Data: YYYY-MM-DD
- Nivel: L2
- Duracao: ~{N}min
- Arquivos: {N} ({M} criados, {K} modificados)
- Verificacao: {pass|fail} ({Na tentativa})
- Retrabalho: {N ciclos}
- Sinais detectados: {lista ou "nenhum"}
