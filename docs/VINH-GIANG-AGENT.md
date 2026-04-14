# Agente Vinh Giang — Documentacao para oratoria-avaliador

## O que e

Um **agente de coaching de comunicacao** baseado no clone mental do Vinh Giang — comunicador, ex-magico profissional, criador do Stage Academy. O agente foi extraido de 138 transcricoes de video (122K palavras) atraves de pipelines automatizados de ETL e Clone-Mind, com fidelidade estimada de 92-95%.

### Relacao com o oratoria-avaliador

O oratoria-avaliador avalia oratoria e comunicacao. O agente Vinh Giang complementa o sistema fornecendo:

- **Coaching personalizado** — Diagnostico e plano de melhoria baseado nos 12 frameworks originais do Vinh
- **Avaliacao com criterios reais** — Usa as mesmas 5 fundacoes vocais, 4 arquetipos e body language system que o Vinh ensina
- **Storytelling aplicado** — Workshop de storytelling com 4 "quimicos" (Dopamine, Oxytocin, Endorphins, Cortisol)
- **Referencia pedagogica** — 96 pares Q&A organizados por nivel Bloom e categoria Socratica

O agente pode ser usado como **modulo de coaching** dentro do fluxo de avaliacao de oratoria: apos o sistema avaliar uma apresentacao, o agente Vinh Giang pode fornecer coaching detalhado sobre como melhorar.

---

## O que esta instalado e onde

### Agente (skill global)

```
~/.claude/skills/vinh-giang.md          ← 1,478 linhas, ativacao automatica
```

### Knowledge Base (global)

```
~/.claude/knowledge/vinh-giang/         ← 1.3 MB
├── mind/                               ← Voice DNA + Thinking DNA + Smoke Tests
├── etl/                                ← 7 artefatos ETL + clone-ready package
└── transcricoes/                       ← 138 transcricoes originais (.txt)
```

O agente esta instalado **globalmente** — disponivel em qualquer projeto com Claude Code, incluindo este.

---

## Como Ativar

```
/vinh-giang
```

O agente carrega a persona completa do Vinh Giang e aguarda comando.

---

## Comandos Disponiveis

### `*coach` — Sessao de Coaching Completa

Sessao 1-on-1 usando o pipeline de coaching do Vinh (9 passos). Analisa uma apresentacao ou descricao do problema e entrega:

- Pontos fortes identificados (sempre primeiro)
- Os 20% de melhorias que geram 80% de impacto (80/20 Lens)
- Plano de 12 semanas (1 skill por semana)

**Exemplo:**
```
/vinh-giang
*coach
"Gravei uma apresentacao de 15 minutos para investidores. Senti que perdi a
atencao deles quando mostrei os numeros. Minha voz fica sempre igual."
```

### `*assess-communication` — Diagnostico Completo

Avaliacao detalhada de comunicacao com scores em:

- 5 Fundacoes Vocais (Rate, Volume, Pitch, Tonality, Pause)
- 4 Arquetipos Vocais (Educator, Coach, Motivator, Friend)
- Body Language (gestos, contato visual, postura)
- Variety score geral

**Exemplo:**
```
/vinh-giang
*assess-communication
[colar transcricao de uma apresentacao ou descrever o contexto]
```

### `*storytelling-workshop` — Workshop de Storytelling

Workshop interativo para construir historias com impacto. O agente ajuda a:

- Escolher o "quimico" certo (Dopamine, Oxytocin, Endorphins)
- Construir o Story Bridge ("The reason I'm telling you this is because...")
- Estruturar a narrativa (hook → build-up → bridge → insight)

**Exemplo:**
```
/vinh-giang
*storytelling-workshop
"Preciso contar a historia da fundacao da empresa para novos funcionarios.
Quero que eles sintam orgulho de trabalhar aqui."
```

### `*archetype-check` — Verificar Archetype

Identifica qual dos 4 arquetipos vocais e o seu default e mapeia quais voce acessa facilmente e quais estao ausentes.

**Exemplo:**
```
/vinh-giang
*archetype-check
"Sou advogada, falo em tribunais e reunioes com clientes."
```

### `*help` — Lista de Comandos

Mostra todos os comandos disponiveis com descricao.

---

## Frameworks Principais do Agente

| Framework | Uso no Coaching |
|-----------|-----------------|
| **Variety Principle** | Diagnostico central: qualquer default e um problema |
| **5 Vocal Foundations** | Avaliar Rate, Volume, Pitch, Tonality, Pause |
| **4 Vocal Archetypes** | Mapear Educator, Coach, Motivator, Friend |
| **4 Storytelling Chemicals** | Selecionar tipo de historia por objetivo |
| **Story Bridge** | Conectar historia ao ponto de aprendizado |
| **80/20 Coaching Lens** | Priorizar melhorias de maior impacto |
| **12-Week Process** | Estruturar plano de desenvolvimento |
| **Look-Feel-Sound** | Integrar body language, emocao e voz |

---

## Documentacao Completa

Para documentacao tecnica completa do pipeline (ETL, Clone-Mind, quality gates, inventario de artefatos), consulte:

```
/mnt/c/Users/bruno/code/transcricao-dqfb/docs/VINH-GIANG-PIPELINE.md
```

Para documentacao da knowledge base global (file tree, exemplos, Q&A pairs):

```
~/.claude/knowledge/vinh-giang/README.md
```

---

## Metadados

| Campo | Valor |
|-------|-------|
| Especialista | Vinh Giang |
| Fonte | Stage Academy (138 videos, 122K palavras) |
| Fidelidade | 92-95% |
| Agente | 1,478 linhas |
| Ativacao | `/vinh-giang` |
| Data de extracao | 2026-03-31 |
