---
name: validate-plan
description: "Validacao pre-execucao de plano. Verifica se o plano cobre todos os requisitos do CONTEXT.md e PRD antes de executar. Detecta gaps, dependencias quebradas e scope drift. Auto-revisa ate 2x. Usar em pipelines L2 entre prd-to-plan e tdd."
category: workflow
risk: low
source: custom
date_added: "2026-04-03"
metadata:
  version: 1
  triggers: validate-plan, validar plano, verificar plano, plan-checker, pre-execucao
---

# Validate Plan — Verificacao Pre-Execucao

> Verifica se o plano VAI atingir o objetivo ANTES de gastar contexto executando.

## Quando usar

- Automaticamente em pipelines L2 (entre `prd-to-plan` e `tdd`)
- Manualmente antes de executar qualquer plano complexo

## Protocolo

### 1. Coletar artefatos

Leia os arquivos gerados pelas etapas anteriores:
- `docs/CONTEXT.md` (se existir — decisoes locked)
- O PRD ou spec mais recente em `docs/`
- O plano gerado por `prd-to-plan` (arquivo de plano ativo)

### 2. Checklist de validacao

Para cada item, marcar PASS ou FAIL:

#### Cobertura de requisitos
- [ ] Cada requisito do PRD/spec tem pelo menos 1 task no plano que o implementa
- [ ] Cada decisao Locked do CONTEXT.md tem task(s) correspondente(s)
- [ ] Nenhum item Deferred aparece no plano (scope leak)

#### Integridade de dependencias
- [ ] Tasks com dependencias listam as dependencias corretas
- [ ] Nao ha dependencias circulares
- [ ] Ordem de execucao respeita dependencias

#### Completude tecnica
- [ ] Mudancas de schema/modelo tem migration correspondente
- [ ] Novos endpoints tem testes correspondentes
- [ ] Mudancas em API publica tem atualizacao de docs/tipos

#### Viabilidade
- [ ] Nenhuma task assume biblioteca/ferramenta nao disponivel no projeto
- [ ] Estimativa de complexidade e razoavel (nenhuma task e "faça tudo")

### 3. Resultado

Se todos PASS:
- Anunciar: "Plano validado. Prosseguindo para execucao."
- Continuar pipeline normalmente

Se algum FAIL:
- Listar os gaps encontrados com detalhes
- Propor correcoes especificas ao plano
- Aplicar correcoes automaticamente (max 2 iteracoes)
- Re-validar apos cada correcao
- Se apos 2 iteracoes ainda houver FAIL: perguntar ao usuario

### 4. Registro

Adicionar ao final do arquivo de plano:

```markdown
## Validation Report
- Status: PASS | PASS (after revision N)
- Gaps found: [lista ou "none"]
- Revisions applied: [lista ou "none"]
- Validated at: [timestamp]
```

## Regras

- Nao executar nenhum codigo — esta fase e somente analise
- Nao reescrever o plano inteiro — apenas corrigir gaps especificos
- Se o plano parece fundamentalmente errado, escalar ao usuario em vez de tentar consertar
- Manter a validacao rapida — nao gastar mais contexto que a propria execucao gastaria
