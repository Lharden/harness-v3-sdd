---
name: harness-workflow
description: "Orquestrador de pipeline v2. Lê classificação do hook (L0/L1/L2), roteia para pipeline correto (brainstorming, write-a-prd, grill-me, prd-to-plan, tdd, etc.), mantém state.json, registra métricas. Usar quando <harness-classification> aparece com L1+ no contexto."
category: workflow
risk: low
source: custom
date_added: "2026-03-24"
metadata:
  version: 2
  triggers: harness-classification, L1, L2, pipeline, feature, bug, refactor, architecture
---

# Harness Workflow v2 — Roteador de Pipeline

> **Precedência:** CLAUDE.md SEMPRE tem prioridade sobre esta skill.

## Quando ativar

Ative quando o contexto contiver `<harness-classification>` com `level: L1` ou `level: L2`.
Para L0, NÃO ative — execute direto sem pipeline.

## Protocolo

1. **Ler classificação** — extraia level, type, pipeline do bloco injetado pelo hook
2. **Anunciar** — exiba ao usuário: "Harness v2: {level}-{type} → {pipeline}"
3. **Atualizar state.json** — marcar `current_step` conforme progride no pipeline
4. **Invocar skills** — na sequência do pipeline, usando Skill tool
5. **Flexibilidade** — pular etapas se justificar (ex: PRD já existe, bug óbvio)
6. **DONE** — marcar `status: done` no state.json, registrar em signals.json

## Pipelines

### L1-feature (v3 — SDD)
`write-spec-light` → `tdd` → `autoresearch:ship` → [verify-against-spec]

### L1-bug
`autoresearch:debug` (Iterations: 10) → `triage-issue` → `autoresearch:fix` (Iterations: 20, Guard: pytest) → [verify]

### L1-refactor
`request-refactor-plan` → execução → `autoresearch:ship` → [verify]

### L2-feature (v3 — SDD)
`discuss` → `brainstorming` → `write-spec` → `grill-me` (sem limite) → `design-doc` → `validate-plan` → `tdd` → `autoresearch:security` (Iterations: 15, condicional: auth/dados/API) → `autoresearch:ship` → [verify-against-spec]

### L2-bug
`autoresearch:debug` (Iterations: 15) → `triage-issue` → `grill-me` → `autoresearch:fix` (Iterations: 30, Guard: pytest, --from-debug) → [verify]

### L2-refactor (v3 — SDD)
`discuss` → `request-refactor-plan` → `grill-me` → `write-spec` → `design-doc` → `validate-plan` → `tdd` → `autoresearch:ship` → [verify-against-spec]

### L2-architecture (v3 — SDD)
`discuss` → `autoresearch:predict` (--depth standard) → `brainstorming` → `write-spec` → `grill-me` → `improve-codebase-architecture` → `design-doc` → `validate-plan` → `tdd` → `autoresearch:security` (Iterations: 15) → `autoresearch:ship` → [verify-against-spec]

## Steps novos (v2.1)

### discuss
Alinhamento upstream com usuario. Gera `docs/CONTEXT.md` com decisoes Locked/Deferred/Discretion. Todas as etapas downstream DEVEM ler e respeitar CONTEXT.md. Invocar via `Skill(skill="discuss")`.

### validate-plan
Verificacao pre-execucao. Verifica se plano cobre todos requisitos do CONTEXT.md/PRD. Detecta gaps, auto-revisa ate 2x. Invocar via `Skill(skill="validate-plan")`.

## Steps novos (v3.0 — SDD)

### write-spec
Gera spec formal completa com user stories priorizadas (P1/P2/P3), acceptance criteria Given/When/Then, boundaries ALWAYS/NEVER/ASK, e `[NEEDS CLARIFICATION]` para ambiguidades. Substitui `write-a-prd` em L2. Invocar via `Skill(skill="write-spec")`.

Artefato: `docs/specs/{feature-slug}-spec.md`

### write-spec-light
Versão enxuta para L1 (~50 linhas: objetivo, REQs, ACs Given/When/Then, boundaries mínimas). Invocar via `Skill(skill="write-spec-light")`.

Artefato: `docs/specs/{feature-slug}-spec-light.md`

### design-doc
Gera design técnico separado (arquitetura, data model, API contracts, test strategy, risks) a partir de spec aprovada. Usado em L2 entre `grill-me` e `validate-plan`. Invocar via `Skill(skill="design-doc")`.

Artefato: `docs/specs/{feature-slug}-design.md`

### verify-against-spec
Estende `verify` com verificação item-por-item da spec: cada REQ, AC, US, boundary e success criterion é checado com evidência concreta. Gera report de cobertura e lista de gaps. Invocar via `Skill(skill="verify-against-spec")`.

Artefato: `docs/specs/{feature-slug}-verification.md`

### Backward compatibility v3
- `write-a-prd` ainda funciona (legacy). Novos pipelines L1/L2 usam `write-spec`/`write-spec-light`.
- `verify` tradicional ainda funciona. Novos pipelines usam `verify-against-spec`.
- Pipelines L1/L2-bug e L1-refactor mantêm fluxo antigo (bug/refactor não precisa de spec formal).

## Related patterns — Advisor Strategy (Anthropic 2026-04-09)

A Anthropic lançou a **Advisor Strategy** um dia antes do Harness v3 ser implementado. É uma **primitiva da Claude Platform API** (`advisor_20260301` tool type) que permite Sonnet/Haiku consultar Opus mid-generation dentro de uma única request `/v1/messages`. Opera em camada diferente do Harness v3.

### Distinção clara
| Camada | Tecnologia | Granularidade |
|--------|-----------|---------------|
| **Advisor Strategy** | API Messages, intra-turn | Modelo executor consulta Opus via tool call, mid-generation |
| **Harness v3** | Claude Code CLI, inter-turn | Pipeline de skills sequenciais com humano no loop |
| **Multi-model review (v3 verify)** | Subagents paralelos | Codex+Gemini revisam pós-execução |

### Por que são complementares, não concorrentes
- Advisor Strategy é **pre-decisão mid-generation** (Opus opina ANTES do executor gerar resposta)
- Multi-model review v3 é **pós-decisão** (revisa diff depois do Claude escrever)
- `grill-me` é **humano-no-loop adversarial** (questiona para humano decidir)
- Advisor Strategy é **modelo-no-loop colaborativo** (consulta outro modelo automaticamente)

### O que o Harness v3 já cobre do espírito advisor (sem o nome):
1. `grill-me` — adversarial pré-execução (humano decide)
2. Multi-model review — Codex+Gemini como advisors pós-execução
3. `validate-plan` — gate antes de tdd
4. `autoresearch:predict` — multi-persona pré-análise

### Quando considerar incorporar Advisor Strategy
**NÃO** refatorar pipelines atuais para incluir advisor step. **NÃO** criar skill `advisor` (confunde orchestration vs API primitive).

**SIM** quando/se o Harness v3 migrar etapas para execução não-interativa via Agent SDK (scope futuro F6 do plano harness-v3-sdd). Nesse caso, habilitar `advisor_20260301` na chamada API faz sentido para que o executor Sonnet possa escalonar para Opus dentro da etapa sem round-trips extras. Benchmarks: Sonnet +2.7pp SWE-bench com -11.9% custo.

**Referência completa:** `~/.claude/projects/C--Windows-System32/memory/reference_advisor_strategy.md`

### verify (com gap-closure + multi-model)
O step `[verify]` no final de cada pipeline agora funciona como loop com review multi-modelo:

1. Rodar `verification-before-completion` (testes, lint, type check)
2. **Lançar review multi-modelo** (conforme Multi-Model Protocol acima):
   - Em L1: Claude (foreground) + Codex review (background) + Gemini review (background)
   - Em L2: triple-model review (Claude + Codex + Gemini)
   - Apresentar tabela consolidada de findings
3. Se PASS (testes + review sem findings críticos) → pipeline completo, ir para DONE
5. Se FAIL → analisar o que faltou:
   a. Listar gaps especificos (teste falhando, requisito nao implementado, finding critico do review multi-modelo)
   b. Gerar `docs/closure-plan.md` com APENAS as delta-tasks necessarias
   c. Executar as delta-tasks
   d. Re-verificar (volta ao passo 1)
6. Max 2 iteracoes de gap-closure. Se apos 2 ainda falhar → escalar ao usuario

**closure-plan.md** deve conter:
```markdown
# Closure Plan — [task_id]
## Gaps encontrados
- [gap 1]: [descricao + evidencia]
## Delta tasks
- [ ] [task especifica para fechar gap 1]
## Origem
- Verificacao que falhou: [qual teste/check]
- Iteracao: 1 de 2
```

## Multi-Model Protocol v2.2

> **Dependência:** plugin `multi-model` em `~/.claude/plugins/local/multi-model/`

### Princípio

Claude é sempre o primário. Codex e Gemini são secundários invocados em background quando agregam valor. Com assinaturas ilimitadas (Max + Plus + Pro), usar secundários agressivamente.

### Quando invocar modelos secundários

Ler `~/.claude/plugins/local/multi-model/config/routing.json` para decidir. Regra: se o stage atual tem `secondary` no routing.json, invocar.

**Tabela rápida (não precisa ler routing.json para estes):**

| Stage | Secundários | Timing | Quando |
|-------|-------------|--------|--------|
| `verify` | Codex + Gemini review | parallel | **SEMPRE** em L1 e L2 |
| `autoresearch:security` | Codex adversarial | parallel | **SEMPRE** em L2 |
| `write-a-prd` | Gemini context-scan | pre-stage | L2 com escopo grande |
| `validate-plan` | Gemini cross-reference | parallel | **SEMPRE** em L2 |
| `autoresearch:predict` | Gemini full codebase | parallel | **SEMPRE** em L2-architecture |

### Como invocar

**Ao entrar em um stage com secondary models:**

1. Checar saúde dos modelos — rodar:
   ```bash
   cd ~/.claude/plugins/local/multi-model && python -c "
   import sys; sys.path.insert(0, 'scripts')
   from lib.health_check import compute_health, format_system_message
   from pathlib import Path; pr=Path('.')
   h=compute_health(pr/'telemetry', pr/'config'/'thresholds.json')
   for m in h: print(f'{m.model}: {m.status}')
   "
   ```
2. Pular modelos com status "red"
3. **Timing "parallel":** Lançar secundários via Agent tool em background ENQUANTO Claude faz o stage em foreground
   - Gemini: lançar agent `gemini-worker` com o contexto do stage
   - Codex: lançar agent `codex-rescue` pedindo review do diff
4. **Timing "pre":** Esperar resultado do secundário ANTES de Claude iniciar o stage
5. Quando backgrounds retornarem → Quality Gate:
   - Parsear outputs contra schema unificado
   - Deduplicar findings (mesmo arquivo + linha = merge, listar fontes)
   - Filtrar confidence < 0.5
   - Apresentar tabela consolidada com coluna "Source"
6. Logar telemetria de cada chamada

### Degradação graciosa

- Modelo indisponível → pular, continuar com os demais
- Ambos indisponíveis → pipeline continua só com Claude (como antes)
- Timeout → marcar "skipped" na telemetria, seguir
- **O pipeline NUNCA trava por causa de modelo secundário**

## Configurações padrão do autoresearch por etapa

| Etapa | Iterations | Guard | Flags | Quando ajustar |
|---|---|---|---|---|
| `autoresearch:debug` L1 | 10 | — | `--scope <arquivos afetados>` | Aumentar se bug complexo |
| `autoresearch:debug` L2 | 15 | — | `--scope <módulo>` | Aumentar se multi-módulo |
| `autoresearch:fix` L1 | 20 | `pytest` | `--from-debug` se veio de debug | Aumentar se muitos findings |
| `autoresearch:fix` L2 | 30 | `pytest` | `--from-debug` | Aumentar se regressões |
| `autoresearch:security` | 15 | `pytest` | `--fail-on high` | `--fix` para auto-corrigir |
| `autoresearch:predict` | — | — | `--depth standard`, `--chain` se encadear | `--depth deep` para decisões críticas |
| `autoresearch:ship` | — | — | `--dry-run` primeiro | `--auto` se CI/CD confiável |

**Princípio:** Iterations são defaults — o agente ou o usuário podem ajustar conforme a complexidade real da tarefa. Guard é sempre `pytest` para projetos Python (detectado automaticamente).

## State management

A cada transição de etapa, atualizar `~/.claude/harness/state.json`:

```json
{
  "task_id": "t-YYYYMMDD-HHMMSS",
  "classification": "L2-feature",
  "status": "active",
  "pipeline": ["brainstorming", "write-a-prd", "grill-me", "prd-to-plan", "tdd"],
  "current_step": "grill-me",
  "artifacts_so_far": ["docs/prd/feature-name.md"],
  "started_at": "ISO timestamp"
}
```

Use o Edit tool para atualizar state.json. Custo: ~20 tokens por transição.

## DONE — registrar métricas

Ao completar o pipeline:
1. Marcar `status: "done"` no state.json
2. Ler `files_modified` do counter file (`~/.claude/harness/.session-files-count`)
3. Calcular `actual_level` baseado em files (0-1=L0, 2-3=L1, 4+=L2)
4. Append entrada em `~/.claude/harness/signals.json` → array `tasks`
5. Atualizar `aggregates`

### Template concreto para signals.json

Ler signals.json, adicionar ao array `tasks`, e recalcular `aggregates`:

```json
{
  "task_id": "<copiar de state.json>",
  "classification": "<copiar de state.json>",
  "actual_level": "L0|L1|L2 (baseado em files: 0-1=L0, 2-3=L1, 4+=L2)",
  "pipeline_completed": true,
  "steps_executed": ["brainstorming", "write-a-prd", "..."],
  "files_modified": 5,
  "completed_at": "2026-04-03T12:00:00Z"
}
```

Aggregates: incrementar `total_tasks` e o contador do level correspondente (`l0_count`, `l1_count`, `l2_count`). Recalcular `pipeline_completion_rate` = tasks com `pipeline_completed: true` / total.

## Artefatos

- **Artefatos de projeto** → `./docs/` (PRDs, planos, issues)
- **Estado operacional** → `~/.claude/harness/` (state.json, signals.json)

## Princípios

- **CLAUDE.md é rei** — usuário pode override qualquer pipeline
- **Degradação graceful** — se uma skill não existe, pula e continua
- **Grill-me sem limite** — convergência natural, não contagem
- **Artefatos são o trace** — PRDs e planos gerados são evidência natural do trabalho
