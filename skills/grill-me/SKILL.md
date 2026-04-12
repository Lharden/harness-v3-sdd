---
name: grill-me
description: "Desafia a spec/plano com perguntas adversariais para encontrar gaps, ambiguidades e suposições erradas antes da execução. Roda sem limite de iterações até o usuário estar satisfeito. Use em pipelines L2 do Harness v3 após write-spec e antes de design-doc."
category: workflow
risk: low
source: custom
date_added: "2026-04-12"
metadata:
  version: 1
  triggers: grill-me, grill, challenge, questionar, desafiar, adversarial review
---

# Grill Me — Adversarial Review da Spec

> Parte do **Harness v3 SDD**. Desafia spec para encontrar gaps antes de implementar.

## Quando ativar

Ative quando:
- Pipeline L2 está na etapa `grill-me` (após `write-spec`, antes de `design-doc`)
- Usuário pede explicitamente para desafiar/questionar um plano ou spec
- Existe uma spec em `docs/specs/` que ainda não foi desafiada

**NÃO ative** em L0 ou L1 — para L1, a spec-light é suficiente sem adversarial review.

## Objetivo

Atuar como **adversário construtivo** que questiona:
1. Suposições implícitas na spec que podem estar erradas
2. Edge cases não cobertos pelos acceptance criteria
3. Requisitos não-funcionais ausentes (performance, segurança, escalabilidade)
4. Conflitos entre user stories ou entre requisitos
5. Viabilidade técnica de decisões implícitas
6. Ambiguidades que deveriam ser `[NEEDS CLARIFICATION]` mas não foram marcadas

## Workflow

### Passo 1: Ler spec atual

Ler `docs/specs/{feature-slug}-spec.md` e `docs/CONTEXT.md` (se existir).

### Passo 2: Formular 5-10 perguntas adversariais

Cada pergunta deve ser:
- **Específica** (não "e se der erro?" — sim "o que acontece se o webhook timeout em 30s com payload de 10MB?")
- **Acionável** (a resposta deve mudar algo na spec ou confirmar uma decisão)
- **Priorizada** (começar pelas que têm maior impacto se a suposição estiver errada)

Exemplos de boas perguntas:
- "O AC-2 assume conexão estável — o que acontece se o request falha no meio do processamento?"
- "REQ-NF1 diz 'resposta em <200ms' mas não menciona carga concorrente. Qual é o target de requests/segundo?"
- "US-2 depende de US-1 estar completa? Se sim, isso não está documentado."

Exemplos de perguntas RUINS (evitar):
- "E os edge cases?" (vago demais)
- "E se der erro?" (genérico demais)
- "Tem certeza disso?" (não acionável)

### Passo 3: Apresentar ao usuário

Listar as perguntas numeradas com contexto:
```
Analisei a spec e encontrei 7 pontos que precisam de atenção:

1. [SUPOSIÇÃO] AC-2 assume payload sempre < 1MB...
2. [GAP] Nenhum AC cobre o cenário de timeout...
3. [CONFLITO] REQ-F3 contradiz a boundary NEVER...
...

Responda cada uma para eu atualizar a spec.
```

### Passo 4: Atualizar spec com respostas

Para cada resposta:
- Se revelou gap → adicionar REQ ou AC na spec
- Se confirmou decisão → anotar como "validated by grill-me"
- Se gerou nova ambiguidade → adicionar `[NEEDS CLARIFICATION]`

### Passo 5: Iterar até satisfação

Perguntar: "Mais alguma preocupação? Continuo desafiando?"
- Se sim → voltar ao Passo 2 com novas perguntas baseadas nas respostas
- Se não → marcar spec como "grilled" e seguir para design-doc

**Sem limite de iterações.** Convergência natural pelo humano.

## Princípios

1. **Adversário construtivo, não destrutivo** — objetivo é melhorar a spec, não demoli-la
2. **Específico sobre genérico** — "e os edge cases?" é inútil; "o que acontece com input de 0 bytes?" é útil
3. **Priorizado por impacto** — questionar primeiro o que quebraria mais se estiver errado
4. **Iterar até satisfação** — humano decide quando parar, não o agente
5. **Resultados voltam para a spec** — cada resposta vira REQ, AC ou clarification resolvida
6. **Não inventar problemas** — se a spec está bem em algum aspecto, dizer isso explicitamente

## Saída

- Spec atualizada com novos REQs/ACs/clarifications
- Anotação no spec metadata: `"grilled": true, "grill_rounds": N`
- Retorno ao harness-workflow para continuar pipeline

## Integração com pipeline

```
discuss → brainstorming → write-spec → grill-me → design-doc → validate-plan → tdd → verify-against-spec
                                        ^^^^^^^^^
                                        Esta skill
```

- Upstream: `write-spec` gera a spec
- Downstream: `design-doc` consome a spec grilhada
- Loop possível: se grill-me revelar gaps fundamentais, pode voltar para `write-spec`
