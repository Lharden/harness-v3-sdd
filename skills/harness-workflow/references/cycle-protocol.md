# Ciclo de Execucao — Protocolo Detalhado

## L1: INIT → EXECUTE → VERIFY-LIGHT → DONE

### INIT
- Append ao trace:
  ## [INIT] {HH:MM:SS} | L1
  - Tarefa: {descricao concisa}
  - Criterio: {definicao de pronto}

### EXECUTE
- Trabalhar normalmente
- Append ao trace no inicio e fim:
  ## [EXECUTE] {HH:MM:SS}
  - Arquivos: {modificados}
  - Resultado: {sucesso|parcial|bloqueio}

### VERIFY-LIGHT
- Confirmar:
  - ruff ok (ja executou via hook PostToolUse)
  - pyright ok (ja executou via hook PostToolUse)
  - Mudanca atende o pedido
  - Hookify warnings registrados
- Append ao trace:
  ## [VERIFY-LIGHT] {HH:MM:SS}
  - ruff: pass
  - pyright: pass
  - funcional: sim

### DONE
- Append ao trace:
  ## [DONE] {HH:MM:SS}
  - Resultado: {concluido|parcial|abandonado}
  - Arquivos modificados: {lista final}
- Atualizar signals.json (detectar sinais)
- Atualizar counters.l1_tasks_completed

---

## L2: INIT → PLAN → EXECUTE → VERIFY → REVIEW(opcional) → DONE

### INIT
- Append ao trace:
  ## [INIT] {HH:MM:SS} | L2
  - Tarefa: {descricao}
  - Criterio: {definicao de pronto}
  - Verify condicional: {quais gates se aplicam}
  - Arquivos provaveis: {lista estimada}
- Criar Tasks via TaskCreate

### PLAN
- Decompor em fases com criterios
- Pode usar skill writing-plans ou inline
- Append ao trace:
  ## [PLAN] {HH:MM:SS}
  - Fase 1: {descricao} → criterio: {como saber que terminou}
  - Fase 2: ...

### EXECUTE
- Registrar por fase:
  ## [EXECUTE:FASE-N] {HH:MM:SS}
  - Arquivos: {lista}
  - Resultado: {sucesso|parcial|bloqueio}
- Registrar transicoes:
  ## [EXECUTE:FASE-N→FASE-M] {HH:MM:SS}
  - Criterio atendido: {evidencia}

### VERIFY
- Executar nucleo obrigatorio + condicionais definidos no INIT
- Ver references/verify-gates.md para detalhes
- Se FALHA: volta para EXECUTE
  ## [VERIFY:FALHA] {HH:MM:SS}
  - Falha: {motivo com evidencia}
  - Acao: retornando para EXECUTE
- Circuit breaker: max 3 ciclos. No 3o:
  ## [VERIFY:CIRCUIT-BREAKER] {HH:MM:SS}
  - Falha 1: {motivo}
  - Falha 2: {motivo}
  - Falha 3: {motivo}
  - Acao: reportando ao usuario
  → Registrar sinal loop_detectado

### REVIEW (condicional)
- Ativar se: seguranca/auth, 4+ arquivos, ou usuario pediu
- Invocar feature-dev:code-reviewer ou pedir review do usuario

### DONE
- Append ao trace:
  ## [DONE] {HH:MM:SS}
  - Resultado: {concluido|parcial|bloqueado|abandonado}
  - Arquivos modificados: {lista final}
  - Fases completadas: {N/M}
  - Verificacao: {pass|fail} ({Na tentativa})
  - Retrabalho: {N ciclos VERIFY→EXECUTE}
  - Resumo: {2-3 linhas}
- Gerar resumo consolidado em summaries/
- Atualizar signals.json
- Atualizar counters.l2_tasks_completed

---

## Caso Debug

INIT (classifica como debug) → systematic-debugging assume → VERIFY → DONE

O Harness registra trace e sinais, mas delega logica de execucao para a skill de debug.

---

## Skills Ativadas por Fase

| Fase | L1 | L2 |
|---|---|---|
| INIT | Harness classifica | Harness classifica |
| PLAN | — | writing-plans ou inline |
| EXECUTE | Skills de dominio | Skills de dominio + code-architect |
| VERIFY | Hooks existentes + checklist | Nucleo + condicional |
| DONE | Trace basico | Resumo + code-simplifier |

brainstorming PRECEDE o Harness. systematic-debugging SUBSTITUI o ciclo.
