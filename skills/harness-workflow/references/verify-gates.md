# Gates de Verificacao — Referencia

## L1: VERIFY-LIGHT

Checklist mental (sem tool calls extras alem do trace):
- [ ] ruff ok (ja executou via hook PostToolUse)
- [ ] pyright ok (ja executou via hook PostToolUse)
- [ ] Mudanca atende o pedido
- [ ] Hookify warnings registrados no trace

Registrar no trace mesmo se tudo passou.

## L2: VERIFY — Nucleo Obrigatorio + Condicional

### Nucleo Obrigatorio (toda tarefa L2)

- [ ] ruff: pass
- [ ] pyright: pass (0 errors)
- [ ] Evidencia positiva exigida (nao ausencia de erro)

**Regra:** Ausencia de output NAO conta como sucesso. Se nao tem output de ruff/pyright, registrar como `inconclusive`.

### Camada Condicional (definida no INIT)

O agente decide no INIT quais se aplicam e registra:

| Gate condicional | Quando ativar |
|---|---|
| pytest executado + pass | Tarefa envolve logica testavel |
| Sem regressao em testes existentes | Modifica codigo com testes pre-existentes |
| code-reviewer (feature-dev) | 4+ arquivos ou seguranca envolvida |
| Validacao funcional | UI/UX ou integracao externa |

### Formato no INIT

## [INIT] HH:MM:SS | L2
- Verify condicional: pytest, regressao, code-reviewer

### Formato no VERIFY

## [VERIFY] HH:MM:SS
- ruff: pass
- pyright: pass (0 errors)
- pytest: pass (12 passed, 0 failed)     ← condicional ativado
- regressao: nenhuma detectada            ← condicional ativado
- review: code-reviewer, 0 criticos      ← condicional ativado
- hookify: 1 warning (warn-todo-fixme)

### Se VERIFY falha

1. Registrar [VERIFY:FALHA] com motivo e evidencia
2. Voltar para EXECUTE
3. Max 3 ciclos (circuit breaker)
4. No 3o: [VERIFY:CIRCUIT-BREAKER], reportar ao usuario, sinal loop_detectado
