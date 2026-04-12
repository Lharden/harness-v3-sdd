# Sinais — Protocolo de Deteccao e Atualizacao

## Quando Detectar

Na fase DONE de toda tarefa L1+. NAO detectar em L0.
L1 detecta apenas: verification_skipped, trace_gap, verification_clean_streak, trace_consistent_streak.
L2 detecta todos os 10 sinais.

## Sinais de Falha

| Sinal | Condicao de deteccao | Acao no signals.json |
|---|---|---|
| verification_skipped | DONE sem bloco [VERIFY] no trace | count++, add session ID |
| trace_gap | Sessao L1+ concluida sem trace-current.md atualizado | count++, add session ID |
| loop_detectado | Circuit breaker ativado (3 ciclos VERIFY→EXECUTE) | count++, add session ID + details |
| classificacao_errada_subiu | Reclassificacao L0→L1 ou L1→L2 durante execucao | count++, add session ID |
| retomada_falhou | Usuario re-explicou contexto apos compact/restart | count++, add session ID |

## Sinais de Sucesso

| Sinal | Condicao de deteccao | Acao no signals.json |
|---|---|---|
| verification_clean_streak | VERIFY pass na 1a tentativa | count++, update streak_start se count==1 |
| trace_consistent_streak | Trace completo nesta sessao | count++, update streak_start se count==1 |
| execution_efficient | L2 concluida sem ciclo VERIFY→EXECUTE | count++, update streak_start se count==1 |
| classificacao_errada_desceu | L2 concluida que era L1 na pratica (<4 arquivos, sem fases) | count++, add session ID |
| retomada_limpa | Retomada pos-compact sem intervencao do usuario | count++, update streak_start se count==1 |

## Reset de Streaks

Sinais de sucesso (streaks) resetam count para 0 e streak_start para null quando o sinal de falha correspondente ocorre:
- verification_clean_streak reseta se verification_skipped ocorre
- trace_consistent_streak reseta se trace_gap ocorre
- execution_efficient reseta se loop_detectado ocorre
- retomada_limpa reseta se retomada_falhou ocorre

**Nota:** `classificacao_errada_subiu` e `classificacao_errada_desceu` usam `sessions[]` (contagem de eventos), nao `streak_start` (contagem consecutiva). Nao ha reset entre eles — sao contadores independentes.

## Atualizacao de signals.json

Na fase DONE, ler signals.json, atualizar campos relevantes, escrever de volta.
Usar Read + Write (nao Edit, pois e JSON completo).

## Thresholds e Recomendacoes

### Recomendacao de ADICIONAR controle
Quando um sinal de falha atinge count >= 3:
→ Na proxima INIT de tarefa L1+, surfacear:

"Padrao '{tipo}' detectado {count} vezes.
Sugestao: {acao especifica}.
Adicionar? (s/n)"

### Recomendacao de RELAXAR controle
Quando um sinal de sucesso atinge count >= 10 consecutivos:
→ Na proxima INIT de tarefa L1+, surfacear:

"Padrao '{tipo}' atingiu {count} sessoes consecutivas.
O hook/controle correspondente pode ser desnecessario.
Sugestao: {acao especifica}.
Remover? (s/n)"

### Acoes por sinal de falha

| Sinal | Recomendacao ao atingir threshold |
|---|---|
| verification_skipped | Adicionar hookify rule no evento stop para enforcement |
| trace_gap | Adicionar hook SessionStart para lembrete de Harness |
| loop_detectado | Revisar heuristica de classificacao (tarefas subestimadas?) |
| classificacao_errada_subiu | Ajustar criterios L0/L1 (threshold muito permissivo?) |
| retomada_falhou | Adicionar hook SessionStart para injecao de estado Harness |

## Health Report

Gerado quando counters.l2_tasks_completed - counters.last_health_report_at_l2 >= 20
E SOMENTE se ha algo acionavel (sinais acima de 50% do threshold OU recomendacoes pendentes).

Formato salvo em summaries/health-report-YYYY-MM-DD.md:

# Harness Health — apos {N} tarefas L2

## Sinais de falha
- {tipo}: {count}x {(abaixo|ACIMA) do threshold}

## Sinais de sucesso
- {tipo}: {count} consecutivas

## Hooks ativos (Fase 2)
- {lista ou "Nenhum"}

## Versoes do ecossistema
- claude_code: {version}
- context_mode: {version}
- superpowers: {version}
- Mudancas desde ultimo check: {lista ou "Nenhuma"}

## Recomendacao
- {acao ou "Sistema saudavel. Nenhuma acao necessaria."}

Atualizar counters.last_health_report_at_l2 apos gerar.
