# Headless Constraints & Guardrails

A execução de modelos LLM em workflows massivos (headless pipelines) através da `runner-lib` requer estrita conformidade para evitar falhas silenciosas, perdas financeiras (OOM tokens) e loops infinitos.

## As 10 Regras do Headless Pipeline 

Baseado nas 212 regras extraídas (`.claude/rules/headless-pipeline.md`), todo runner é obrigado a seguir os seguintes princípios ao criar o LLM command (encapsulados por padrão no módulo `runtime.sh`):

1. **Auto-Deny Absoluto:** Qualquer tool action não aprovisionada por whitelist sofrerá auto-deny em background (ausência de console pseudo-tty interativo).
2. **Safety Bypass Limits:** As flags `--dangerously-skip-permissions` não contornam escrita em diretórios restritos (ex: `.git`, configurações de shield).
3. **Agent Type Bound Tooling:** Agentes criados assincronamente possuem hard limits e chaves limitadas.
4. **AllowedTools Mandatório:** É obrigatório mapear expressamente as tools usando `--allowedTools` para previnir surpresas do Claude Code CLI.
5. **Output Cap Truncation (50K Chars):** Outputs excedendo 50.000 caracteres serão severamente truncados na memória do buffer, o que destrói JSONs de resposta.
6. **Denial Tracker Panic:** Acúmulo de $\geq$ 3 denials desativam o LLM localmente, escalonando para graceful fallback.
7. **Compound Bash Block:** LLM bash commands com mais de 50 pipes/statements compostos darão panic pre-execution.
8. **JSON Metadata Garbaging:** O stdout via headless pipeline costuma jogar metadados (`type: result, subtype: max_turns`) sujando o buffer alvo.
9. **Read-Before-Write (BR-PROMPT-006):** LLMs sofrem severos impedimentos se tentarem submeter file modifications em arquivos que nunca deram `.Read()`.
10. **Session Amnesia:** Aprovações de um step/phase jamais sangram para o próximo phase. Contextos autoritativos devem ser reinjetados do zero.

---

## Model Capability Matrix (Empirical Data)

As performances a seguir refletem as estatísticas acumuladas dos scripts `books.sh`, `copy.sh` e `decoder.sh`:

| Model | Token Capacity | Native Output Extraction | Context Integrity | Routing Ideal | Cost Rate |
|---|---|---|---|---|---|
| **Gemini 3.1 Pro (Preview)** | Extrema (2M tokens) | JSON Isolado Perfeito | Zero Esquecimento em Prior Contexts | Refactoring Base, Modeling complexo de grandes repos. | Alto |
| **Claude 3.7 Sonnet** | Equilibrado (200K) | Markdown bem estruturado | Ocasionalmente omite premissas longas | Execução Headless Ágil, Extração e Regex | Moderado |
| **Claude 3.5 Haiku** | Baixa a Moderada | Propenso a verbosidade (tag suja) | Perde prior context $>$ 15K bytes facilmente | Roteamento Semântico e Filtros Binários Rápido | Baixo / Veloz |

---

## Anti-Patterns Listados

### 1. Invasão de E9 Gate
Alguns runners tentaram submeter todo o context state e history logs complexos usando `jq` direto pro prompt da próxima phase, extrapolando o byte limit de 3KB permitido para injeção. O *novo* `headless-guard.sh` intercepta e trunca via `truncate_prior_context()` mitigando o E9 Gate crash.

### 2. A Ilusão do Fallback Cascade
Achar que falhar na extração de JSON gerará novas tentativas sozinhas (Cascade). Runners que não usam `run_llm_prompt` tentavam engatilhar retry loop manuais com `while`, resultando em rate limits na API BDT.

### 3. Jq Parsing com LLM Lixo
LLM Outputs que começam conversacionalmente ("Aqui está seu JSON solicitado: ...") seguido por markdown block explodem os parsers nativos de bash (`jq`). Invoque **`filter_llm_output()`** extrair com segurança via AWK.
