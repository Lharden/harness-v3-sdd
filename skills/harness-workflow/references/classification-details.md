# Classificacao de Complexidade — Detalhes

## Heuristica Completa

### L0 — Trivial (Harness nao intervem)

TODOS devem ser verdadeiros:
- Usuario pede informacao, explicacao ou opiniao
- OU edit em 1 arquivo com escopo evidente
- Sem necessidade de planejamento
- Sem risco de regressao

Exemplos: "o que faz essa funcao?", "adiciona type hint nesse parametro", "explica esse erro"

### L1 — Moderado (ciclo leve)

Tudo que nao e L0 nem L2. Inclui explicitamente:
- Tarefas de 2-3 arquivos
- Refatoracoes localizadas
- Bugfixes com escopo definido
- Adicao de funcao/metodo simples com teste

Exemplos: "adiciona endpoint GET /users com teste", "refatora essa classe em dois modulos"

### L2 — Complexo (ciclo completo)

QUALQUER verdadeiro:
- Envolve 4+ arquivos
- Requer planejamento/decomposicao
- Envolve testes + codigo + config simultaneamente
- Usuario ativou skill de planejamento (writing-plans, brainstorming)
- Tarefa tem dependencias entre passos
- Risco de regressao em codigo existente

Exemplos: "implementa autenticacao OAuth2", "migra de SQLite para PostgreSQL"

## Regra Hard-Coded de Seguranca

Se durante execucao de QUALQUER tarefa (mesmo L0) o agente modifica 3+ arquivos:
→ Promover automaticamente para L1 minimo
→ Registrar reclassificacao no trace

## Reclassificacao

- Permitida apenas para CIMA: L0→L1, L1→L2
- NUNCA para baixo durante execucao
- Registrar no trace com formato:

## [RECLASSIFICACAO] L1 → L2
- Motivo: {motivo concreto}
- Acao: ativando ciclo completo

## Custo

- L0: zero tokens extras
- L1: ~3 tool calls (~250 tokens)
- L2: ~9 tool calls (~800 tokens, 0.4% de 200k)
