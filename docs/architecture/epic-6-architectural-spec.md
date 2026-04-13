# Epic 6 — Especificacao Arquitetural para @sm e @po

**Autor:** @architect (Aria)
**Data:** 2026-04-13
**Status:** SPEC COMPLETA — pronto para @sm criar stories e @po validar
**Contexto:** Decisoes tomadas em reuniao com mentor em 2026-04-10. Foco em "melhor espinha dorsal possivel" para o APP antes de evoluir outros pontos.

---

## Resumo das Decisoes do Mentor

### IMPLEMENTAR AGORA (5 features)

| ID | Feature | Tipo |
|----|---------|------|
| **6.Q** | Questionario novo (6 perguntas reescritas pelo mentor) | Schema + Frontend + Prompt |
| **6.1** | Insights Cruzados no prompt do LLM | Prompt Engineering |
| **6.2** | Hierarquia de Problemas (ranking por impacto) | Prompt Engineering |
| **6.8** | Score de Identidade (identity_analyzer.py) | Novo Worker |
| **6.10** | Analise de Abertura — Tecnica de Conexao | Novo Worker |

### DEFERIR (proximo ciclo)
6.3, 6.4, 6.5, 6.6, 6.7, 6.9, 6.11, 6.12, 6.13

---

## FEATURE 6.Q — Questionario Reescrito pelo Mentor (6 perguntas)

### O que e
Substituir as 5 perguntas atuais do questionario pre-avaliacao por 6 perguntas novas definidas pelo mentor. As opcoes mudam, a estrutura muda, e 2 perguntas sao completamente novas.

### O que existe hoje

**Tabela `evaluation_context`:**
```sql
CREATE TABLE evaluation_context (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evaluation_id UUID NOT NULL REFERENCES evaluations(id) ON DELETE CASCADE,
    sentimento INTEGER CHECK (sentimento BETWEEN 1 AND 5),
    maior_medo TEXT[],
    contexto TEXT CHECK (contexto IN ('vendas', 'palco', 'aula', 'rede_social', 'reuniao', 'podcast', 'outro')),
    avaliado_antes BOOLEAN DEFAULT false,
    objetivo TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(evaluation_id)
);
```

**Frontend:** `apps/web/src/app/evaluate/[id]/context/page.tsx` — wizard de 5 steps

### O que precisa mudar

#### Schema — Colunas a REMOVER ou RENOMEAR

| Coluna atual | Acao | Nova coluna |
|--------------|------|-------------|
| `sentimento` (1-5) | **MANTER** (mesma pergunta) | — |
| `maior_medo` (text[]) | **ATUALIZAR opcoes** (de 5 para 7) | — |
| `contexto` (text check) | **SUBSTITUIR** por nova pergunta | `motivacao` (text[]) |
| `avaliado_antes` (boolean) | **MANTER** | — |
| `objetivo` (text livre) | **SUBSTITUIR** por 2 novas perguntas | `desejo_transmitir` (text[]) + `desejo_melhorar` (text[]) |

#### Migration necessaria

```sql
-- Migration 008: Atualizar questionario conforme mentor
-- 1. Remover constraint do campo contexto (agora e motivacao)
ALTER TABLE evaluation_context DROP CONSTRAINT IF EXISTS evaluation_context_contexto_check;
ALTER TABLE evaluation_context RENAME COLUMN contexto TO motivacao;

-- 2. Adicionar novas colunas
ALTER TABLE evaluation_context ADD COLUMN IF NOT EXISTS desejo_transmitir TEXT[];
ALTER TABLE evaluation_context ADD COLUMN IF NOT EXISTS desejo_melhorar TEXT[];

-- 3. Remover coluna objetivo (substituida por desejo_transmitir + desejo_melhorar)
ALTER TABLE evaluation_context DROP COLUMN IF EXISTS objetivo;
```

#### As 6 perguntas (EXATAMENTE como o mentor definiu)

**Pergunta 1 — Sentimento ao gravar** (MANTIDA, mesma de antes)
- Tipo: Escala 1-5 (clique unico)
- "Como voce se sentiu gravando esse video?"
- Opcoes: 1=Muito nervoso, 2=Nervoso, 3=Neutro, 4=Confiante, 5=Muito confiante
- Campo DB: `sentimento` (INTEGER, ja existe)

**Pergunta 2 — Maior medo** (ATUALIZADA — opcoes mudaram)
- Tipo: Selecao multipla (checkboxes)
- "Qual seu maior medo ao se comunicar?"
- Opcoes:
  1. `dar_branco` — "Esquecer o que ia falar (dar branco)"
  2. `julgamento` — "Do que os outros vao dizer (julgamento)"
  3. `monotono` — "Parecer monotono ou entediante"
  4. `nao_convencer` — "Nao conseguir convencer"
  5. `errar` — "De errar"
  6. `parecer_diferente` — "Parecer diferente de quem eu sou"
  7. `outro` — "Outro"
- Campo DB: `maior_medo` (TEXT[], ja existe — valores mudam)
- **IMPORTANTE:** opcoes antigas (`esquecer`, `julgamento`, `monotono`, `nao_convencer`, `outro`) sao substituidas. Valores antigos no banco nao quebram (sao apenas strings).

**Pergunta 3 — Motivacao** (NOVA — substitui "contexto da apresentacao")
- Tipo: Selecao multipla (checkboxes)
- "Por que voce quer melhorar a comunicacao?"
- Opcoes:
  1. `redes_sociais` — "Me posicionar nas redes sociais"
  2. `vender_mais` — "Vender mais"
  3. `carreira` — "Crescer na profissao/carreira"
  4. `palestrar` — "Palestrar"
  5. `satisfacao_pessoal` — "Satisfacao pessoal"
  6. `outro` — "Outro"
- Campo DB: `motivacao` (TEXT[], era `contexto` TEXT — renomeado e tipo muda)
- **IMPACTO CRITICO:** O aggregator.py usa `contexto` para selecionar pesos contextuais (PESOS_POR_CONTEXTO). Com essa mudanca, o campo `contexto` nao existe mais. **O aggregator precisa de adaptacao** para inferir pesos a partir da `motivacao` ou usar PESOS_DEFAULT sempre.

**Pergunta 4 — Avaliado antes** (MANTIDA)
- Tipo: Sim/Nao (botoes)
- "Voce ja se avaliou antes?"
- Campo DB: `avaliado_antes` (BOOLEAN, ja existe)

**Pergunta 5 — Desejo transmitir** (NOVA)
- Tipo: Selecao multipla (checkboxes)
- "O que voce deseja transmitir atraves da sua comunicacao?"
- Opcoes:
  1. `confianca` — "Confianca"
  2. `autoridade` — "Autoridade"
  3. `credibilidade` — "Credibilidade"
  4. `naturalidade` — "Naturalidade"
  5. `seguranca` — "Seguranca"
  6. `outro` — "Outro"
- Campo DB: `desejo_transmitir` (TEXT[], NOVO)
- **USO NO LLM:** O relatorio avalia se a FALA do orador realmente transmite o que ele DESEJA transmitir. Ex: orador quer transmitir "autoridade" mas usa linguagem de vitima → gap detectado.

**Pergunta 6 — Desejo melhorar** (NOVA — substitui "O que voce espera melhorar?" texto livre)
- Tipo: Selecao multipla (checkboxes)
- "O que voce espera melhorar?"
- Opcoes:
  1. `diccao` — "Diccao"
  2. `postura` — "Postura"
  3. `gestual` — "Gestual"
  4. `tom_de_voz` — "Tom de voz"
  5. `clareza_fala` — "Clareza na fala (ritmo, pausas, velocidade)"
  6. `outro` — "Outro"
- Campo DB: `desejo_melhorar` (TEXT[], NOVO)
- **USO NO LLM:** O relatorio prioriza feedback nas dimensoes que o orador PEDIU para melhorar. Se ele quer melhorar "postura" e tirou 77, o LLM explica que postura esta boa mas mostra detalhes. Se quer melhorar "tom de voz" e tirou 51, o LLM aprofunda aqui.

### Arquivos a modificar

| Arquivo | O que muda |
|---------|-----------|
| `supabase/migrations/008_questionnaire_v2.sql` | **NOVO** — migration acima |
| `apps/web/src/app/evaluate/[id]/context/page.tsx` | **REESCREVER** — wizard de 6 steps com novas opcoes |
| `apps/api/app/routes/evaluations.py` | **ATUALIZAR** endpoint POST/GET context com novos campos |
| `ml-worker/workers/aggregator.py` | **ADAPTAR** — `contexto` nao existe mais, ajustar `_get_pesos()` para mapear `motivacao` para pesos OU usar default |
| `ml-worker/workers/report_generator.py` | **ATUALIZAR** secao de contexto do prompt com os 6 campos novos |
| `ml-worker/app.py` | **ATUALIZAR** Step 9 — buscar novos campos para passar ao aggregator e report_generator |

### Mapeamento motivacao → pesos (proposta)

Como `contexto` (palco/vendas/podcast...) virou `motivacao` (redes sociais/vender mais/carreira...), os pesos contextuais precisam ser remapeados:

| Motivacao | Peso sugerido | Racional |
|-----------|--------------|----------|
| `redes_sociais` | PESOS_POR_CONTEXTO["rede_social"] | Mesma coisa |
| `vender_mais` | PESOS_POR_CONTEXTO["vendas"] | Vendas diretas |
| `carreira` | PESOS_POR_CONTEXTO["reuniao"] | Comunicacao corporativa |
| `palestrar` | PESOS_POR_CONTEXTO["palco"] | Palco |
| `satisfacao_pessoal` | PESOS_DEFAULT | Generico |
| `outro` | PESOS_DEFAULT | Generico |

**Se multiplas motivacoes selecionadas:** usar a PRIMEIRA motivacao como peso principal (ou media ponderada — decisao do @dev).

### Integracao com o prompt do LLM

Novo bloco no prompt:

```
## CONTEXTO DO ORADOR (questionario pre-avaliacao)
- Sentimento ao gravar: {sentimento_label} ({sentimento}/5)
- Maiores medos: {', '.join(maior_medo)}
- Motivacao para melhorar: {', '.join(motivacao)}
- Ja se avaliou antes: {'sim' if avaliado_antes else 'nao, primeira vez'}
- Deseja transmitir: {', '.join(desejo_transmitir)}
- Quer melhorar: {', '.join(desejo_melhorar)}

INSTRUCOES DE ADAPTACAO:
1. SENTIMENTO: Se nervoso (1-2), tom EXTRA encorajador. Se confiante (4-5), mais direto/desafiador.
2. MEDOS: Enderece pelo menos 1 medo mencionado no feedback — mostre que a avaliacao ajuda a superar esse medo especifico.
3. MOTIVACAO: Conecte o feedback ao MOTIVO do orador. Se quer "vender mais", linke a melhoria a resultado de vendas.
4. PRIMEIRA VEZ: Se nao se avaliou antes, explique brevemente o que cada metrica significa.
5. DESEJO_TRANSMITIR: Avalie se a comunicacao REALMENTE transmite o que o orador quer. Se ele quer "autoridade" mas usa linguagem de vitima, aponte esse gap. Se ja transmite, celebre.
6. DESEJO_MELHORAR: Priorize feedback nas dimensoes que o orador PEDIU. Comece por elas.
```

### Retrocompatibilidade

- Registros antigos no banco terao `motivacao = NULL`, `desejo_transmitir = NULL`, `desejo_melhorar = NULL`. O LLM deve tratar campos nulos silenciosamente (nao mencionar o que nao existe).
- Registros antigos com `objetivo` (texto livre) serao perdidos apos DROP COLUMN. **Se quiser preservar:** fazer migration que copia `objetivo` para `desejo_melhorar = ARRAY[objetivo]` antes de dropar.

### Criterios de Aceite sugeridos

1. Questionario funcional com 6 perguntas (todas de selecao/escala, nenhuma texto livre)
2. Opcao "Pular" mantida
3. Dados salvos corretamente no Supabase
4. LLM recebe os 6 campos e adapta tom conforme instrucoes
5. Registros antigos nao quebram
6. Aggregator funciona com ou sem `motivacao` (fallback para PESOS_DEFAULT)

---

## FEATURE 6.1 — Insights Cruzados no Prompt do LLM

### O que e
Funcao **deterministica Python** (NAO LLM) que combina 2+ metricas em um unico diagnostico acionavel pre-calculado. O output vai direto para o prompt do LLM como secao estruturada. Isso resolve o problema dos mentores: "as metricas sao apresentadas isoladas, o LLM nao cruza sozinho."

### Estado atual do codigo

O `report_generator.py` monta o prompt assim:
```python
prompt = REPORT_PROMPT.format(
    overall_score=...,
    variety_score=..., variety_metrics=...,
    voice_score=..., voice_metrics=...,
    gesture_score=..., gesture_metrics=...,
    posture_score=..., posture_metrics=...,
    fillers_score=..., fillers_metrics=...,
    archetype_score=..., archetype_metrics=...,
)
```

**Cada dimensao e formatada separadamente.** O LLM nao recebe instrucao para CRUZAR pitch range com CV pitch, ou gesticulation com zona ideal.

### O que precisa ser feito

**Novo helper `_build_cross_insights(aggregated)` no `report_generator.py`** que retorna uma lista de strings com diagnosticos compostos.

### Regras de cruzamento (lista completa para o @dev implementar)

| ID | Condicao 1 | Condicao 2 | Diagnostico |
|----|-----------|-----------|-------------|
| X01 | `pitch_range_semitones >= 15` | `cv_pitch < 0.08` | "Instrumento vocal rico ({range} semitons) mas sub-utilizado (CV {cv}). Metafora: Ferrari na segunda marcha." |
| X02 | `wpm > 170` | `cv_velocidade < 0.10` | "Fala rapida ({wpm} WPM) E sem variacao (CV {cv}). Dois problemas que se amplificam — rapidez sem respiro." |
| X03 | `gesticulation_pct >= 90` | `zona_ideal_pct < 30` | "Gesticula {gest}% do tempo mas apenas {zona}% na zona ideal (peito-cintura). O gesto e ruido visual, nao enfase." |
| X04 | `arquetipo_dominante == 'amigo'` | `volume_base_1_10 > 8` | "Lock-in no arquetipo Amigo (casual) mas com volume {vol}/10. Amigo deveria ser caloroso e calmo — nao gritando." |
| X05 | `eye_contact_pct >= 95` | `distribuicao_olhar < 0.3` | "Contato visual excelente ({eye}%) mas olhar fixo em um ponto. Falta distribuir para toda a audiencia." |
| X06 | `posture.alignment_score >= 80` | `posture.grounding_score < 50` | "Postura alinhada ({align}) mas instavel ({ground}). O corpo esta certo mas os pes nao estao firmes." |
| X07 | `variety.pct_tempo_monotono > 70` | `voice.pitch_range_semitones >= 12` | "Monotono em {mono}% do tempo APESAR de ter range vocal de {range} semitons. O instrumento esta ali — voce escolheu nao usar." |
| X08 | `fillers_per_minute > 5` | `pausas.qtd_estrategicas < 2` | "Muitos vicios ({fpm}/min) e quase zero pausas estrategicas ({pausas}). Os vicios SUBSTITUEM as pausas — quando deveria ter silencio, voce preenche com 'ne', 'tipo', 'ai'." |
| X09 | `voice.score >= 60` | `variety.score < 30` | "Voz tecnicamente razoavel ({voice}) mas variedade muito baixa ({var}). Voce tem a tecnica mas a usa de forma monotona — como um musico que sabe tocar mas repete a mesma musica." |
| X10 | `temporal.abertura.score < 50` | `temporal.meio.score >= 70` | "Abriu fraco ({ab}) mas pegou forca no meio ({meio}). Voce demora pra esquentar — vamos trabalhar a abertura." |

### Onde inserir no prompt

Apos as metricas por dimensao, antes das instrucoes criticas:

```
## INSIGHTS PRE-CALCULADOS (cruzamento de metricas — USE como base)
{insights_text}

INSTRUCAO: use esses insights como BASE do seu feedback. NAO copie literal — 
reescreva no seu tom de coach. Esses cruzamentos sao a PRIORIDADE do feedback.
```

### Arquivos a modificar

| Arquivo | O que muda |
|---------|-----------|
| `ml-worker/workers/report_generator.py` | Adicionar funcao `_build_cross_insights(aggregated)` + inserir output no prompt |

Nenhum outro arquivo muda. Nenhuma migration. Nenhum frontend.

### Criterios de Aceite sugeridos

1. Pelo menos 10 regras de cruzamento implementadas (tabela acima)
2. Funcao retorna lista de strings com diagnosticos
3. Diagnosticos injetados no prompt do LLM como secao estruturada
4. Relatorio gerado usa pelo menos 1 insight cruzado no texto
5. Funcao retorna lista vazia se nenhuma regra e acionada (graceful)
6. Teste: reprocessar video de referencia (e4359918) e comparar antes/depois

---

## FEATURE 6.2 — Hierarquia de Problemas (Ranking por Impacto)

### O que e
Funcao **deterministica Python** que rankeia os problemas detectados do orador por **impacto real** (nao por score absoluto). O output vai para o prompt do LLM como lista numerada "#1 CRITICO, #2 ALTO, #3 MEDIO..." com instrucao de concentrar 80% do feedback nos problemas #1 e #2.

### Estado atual

O LLM recebe metricas isoladas e decide sozinho o que priorizar. Resultado: lista plana de 5 melhorias com peso aparentemente igual. O orador nao sabe por onde comecar.

### O que precisa ser feito

**Novo helper `_rank_problems(aggregated)` no `report_generator.py`.**

### Tabela de pesos para ranking

| Metrica | Threshold de problema | Peso | Label |
|---------|----------------------|------|-------|
| `voice.cv_volume` | < 0.05 | 10 | "Volume uniforme (sem peaks and troughs)" |
| `variety.pct_tempo_monotono` | > 50% | 10 | "Fala previsivel/monotona" |
| `voice.cv_pitch` | < 0.08 | 9 | "Tom de voz sem variacao" |
| `archetypes.lock_in` | == True | 8 | "Lock-in em 1 arquetipo vocal" |
| `voice.wpm` | > 170 ou < 110 | 7 | "Velocidade de fala fora do ideal" |
| `gesture.zona_ideal_pct` | < 30% | 6 | "Gestos fora da zona de poder" |
| `gesture.gesto_repetitivo` | == True | 5 | "Gesto repetitivo (default gestual)" |
| `fillers.fillers_per_minute` | > 4 | 5 | "Vicios de linguagem frequentes" |
| `posture.grounding_score` | < 50 | 4 | "Instabilidade corporal" |
| `voice.pausas.ratio_estrategicas` | < 0.2 | 6 | "Poucas pausas estrategicas" |
| `temporal.abertura.score` | < 50 | 7 | "Abertura fraca (primeiros segundos)" |

**Calculo:**
```python
severity = abs(value - threshold) / max(abs(threshold), 1)  # quao longe do ideal
priority = weight * severity
```

**Output para o prompt:**
```
## HIERARQUIA DE PROBLEMAS (rankeados por impacto — 80/20)
#1 CRITICO — Volume uniforme (CV 0.003, ideal > 0.05). Causa raiz da monotonia.
#2 CRITICO — 83.6% do tempo monotono (ideal < 30%).
#3 ALTO — Lock-in no arquetipo Amigo (100%). Sem variacao de persona.
#4 MEDIO — WPM 187 (ideal 130-170). Fala rapida sem pausas.
#5 BAIXO — 5.6 vicios de linguagem/min (ideal < 3).

INSTRUCAO: concentre 80% do feedback nos problemas #1 e #2. 
Menciona #3 brevemente. #4 e #5 como observacao final.
O orador SAI com 1 unica prioridade: o problema #1.
```

### Arquivos a modificar

| Arquivo | O que muda |
|---------|-----------|
| `ml-worker/workers/report_generator.py` | Adicionar funcao `_rank_problems(aggregated)` + inserir output no prompt |

### Criterios de Aceite sugeridos

1. Funcao retorna lista de problemas ordenada por priority (weight × severity)
2. Cada problema tem: ranking, severidade (CRITICO/ALTO/MEDIO/BAIXO), label, valor atual, threshold ideal
3. Max 5-7 problemas retornados (nao listar tudo)
4. Injetado no prompt ANTES dos insights cruzados
5. LLM respeita hierarquia (80% do texto sobre #1 e #2)
6. Se nenhum problema detectado (score >= 70 em tudo), retorna lista vazia com mensagem: "Sem problemas criticos detectados"
7. Teste: reprocessar video de referencia — relatorio deve ter prioridade clara

---

## FEATURE 6.8 — Score de Identidade (identity_analyzer.py)

### O que e
**Novo worker** que analisa o transcript do Whisper buscando **marcadores linguisticos** dos 5 vicios emocionais do Gui Reginatto (Vitimizacao, Comparacao, Rejeicao, Culpa, Injustica) e a ratio de linguagem de Autoridade vs linguagem de Vitima. Produz um "Score de Identidade Comunicativa" de 0-100.

### Por que e importante
O mentor definiu: identidade precede tecnica. Se o orador fala com linguagem de vitima ("eu acho", "talvez", "nao sei se posso"), nenhuma melhoria tecnica resolve. Esse analyzer detecta isso automaticamente a partir do texto que o orador JA disse.

### Dados disponivel para usar (JA EXISTE no pipeline)

O Whisper produz:
- `full_text` — transcricao completa em texto
- `words` — lista de palavras com timestamps `[{word, start, end}, ...]`
- `language` — idioma detectado

### Arquitetura do worker

**Novo arquivo:** `ml-worker/workers/identity_analyzer.py`

**Input:** `transcription: dict` (mesmo input que o filler_detector recebe)

**Output:**
```python
{
    "score": int,  # 0-100 (100 = identidade firme, autoridade alta)
    "vicios_emocionais": {
        "vitimizacao": int,  # contagem
        "comparacao": int,
        "rejeicao": int,
        "culpa": int,
        "injustica": int,
    },
    "vicio_dominante": str | None,
    "total_vicios": int,
    "autoridade_count": int,
    "vitima_count": int,
    "autoridade_ratio": float,  # 0.0 a 1.0 (1.0 = 100% linguagem de autoridade)
    "exemplos": [  # top 5 ocorrencias para citar no relatorio
        {"texto": str, "categoria": str, "timestamp": float}
    ],
    "diagnostico": str,  # "identidade_firme" | "identidade_media" | "identidade_fragil" | "identidade_bloqueada"
}
```

### Marcadores linguisticos (lista completa para implementacao)

**VICIOS EMOCIONAIS (Gui Reginatto — 5 vicios)**

```python
VICIOS_EMOCIONAIS = {
    "vitimizacao": [
        r"\bnao consigo\b",
        r"\bnão consigo\b",
        r"\be muito dificil\b",
        r"\bé muito difícil\b",
        r"\bninguem me ajuda\b",
        r"\bninguém me ajuda\b",
        r"\bsempre me acontece\b",
        r"\bnao tem jeito\b",
        r"\bnão tem jeito\b",
        r"\bnao da pra\b",
        r"\bnão dá pra\b",
        r"\bnao da certo\b",
        r"\bimpossivel\b",
        r"\bimpossível\b",
    ],
    "comparacao": [
        r"\bdiferente d[eo]\b",
        r"\btodo mundo tem\b",
        r"\bmenos que os outros\b",
        r"\beu nao sou como\b",
        r"\bo fulano consegue\b",
        r"\beles conseguem\b",
        r"\bpra eles e facil\b",
        r"\bpra eles é fácil\b",
    ],
    "rejeicao": [
        r"\bvao me julgar\b",
        r"\bvão me julgar\b",
        r"\bnao vou conseguir\b",
        r"\bnão vou conseguir\b",
        r"\bninguem vai acreditar\b",
        r"\bninguém vai acreditar\b",
        r"\bvao rir de mim\b",
        r"\bvão rir de mim\b",
        r"\bque vergonha\b",
        r"\bnao sou bom\b",
        r"\bnão sou bom\b",
        r"\bnao sou capaz\b",
    ],
    "culpa": [
        r"\bdesculpa\b",
        r"\bnao sei se posso\b",
        r"\bnão sei se posso\b",
        r"\bespero nao estar atrapalhando\b",
        r"\bperdao\b",
        r"\bperdão\b",
        r"\bme desculpe\b",
        r"\bsinto muito\b",
        r"\bfoi mal\b",
    ],
    "injustica": [
        r"\bdeveria ser diferente\b",
        r"\bnao e justo\b",
        r"\bnão é justo\b",
        r"\berrado isso\b",
        r"\bnao e certo\b",
        r"\bnão é certo\b",
        r"\binjusto\b",
    ],
}
```

**LINGUAGEM DE AUTORIDADE vs VITIMA**

```python
LINGUAGEM_AUTORIDADE = [
    r"\beu vou\b",
    r"\ba melhor forma e\b",
    r"\ba melhor forma é\b",
    r"\bfaca isso\b",
    r"\bfaça isso\b",
    r"\beu sei\b",
    r"\beu sei que\b",
    r"\bfunciona assim\b",
    r"\beu decidi\b",
    r"\be assim\b",
    r"\bé assim\b",
    r"\btenho certeza\b",
    r"\bcom certeza\b",
    r"\beu garanto\b",
    r"\bvamos la\b",
    r"\bvamos lá\b",
    r"\bprecisamos\b",
    r"\bdevemos\b",
]

LINGUAGEM_VITIMA = [
    r"\beu tento\b",
    r"\btalvez\b",
    r"\bquem sabe\b",
    r"\beu acho\b",
    r"\bpode ser que\b",
    r"\beu espero\b",
    r"\bse der\b",
    r"\bnao sei se\b",
    r"\bnão sei se\b",
    r"\bseila\b",
    r"\bsei la\b",
    r"\bsei lá\b",
    r"\bde repente\b",
    r"\bse possivel\b",
    r"\bse possível\b",
]
```

### Formula de Score

```
Base: 60
Penalidade vicios: -5 por ocorrencia (max -40)
Bonus autoridade: (autoridade_ratio - 0.5) × 80  (range: -40 a +40)
Score final: max(0, min(100, base - penalidade + bonus))
```

**Diagnostico:**
- score >= 80: `identidade_firme`
- score >= 60: `identidade_media`
- score >= 40: `identidade_fragil`
- score < 40: `identidade_bloqueada`

### Integracao no pipeline

**No `app.py` — Novo Step 5.5 (apos filler_detector, antes de variety_analyzer):**

```python
# Step 5.5: Analise de identidade linguistica
await _notify_status(req.callback_url, req.evaluation_id, "analyzing_identity")
try:
    from workers.identity_analyzer import analyze_identity
    identity_result = analyze_identity(transcription)
except Exception as e:
    logger.error("identity_analysis_failed", error=str(e))
    identity_result = {"score": 0, "diagnostico": "failed"}

_save_analysis(supabase, req.evaluation_id, "identity", identity_result)
```

**No `aggregator.py`:**
- Receber `identity_result` como parametro
- NAO incluir no overall_score (dimensao informativa, assim como archetypes)
- Salvar em `detailed_metrics["identity"]`

**No `report_generator.py`:**
```
## IDENTIDADE COMUNICATIVA DO ORADOR
Score de identidade: {score}/100 ({diagnostico})
Linguagem de autoridade: {autoridade_count} marcadores ({autoridade_ratio:.0%})
Linguagem de vitima: {vitima_count} marcadores
Vicios emocionais detectados: {total_vicios} (dominante: {vicio_dominante})

{exemplos formatados}

INSTRUCAO: 
- Se identidade_bloqueada ou identidade_fragil: aborde PRIMEIRO. 
  "Antes de falar de tecnica, preciso falar sobre como voce se POSICIONA na fala."
- Se identidade_firme: celebre e use como base do coaching.
- Cruze com desejo_transmitir do questionario: o orador quer transmitir {desejo} 
  mas sua linguagem indica {diagnostico}? Aponte o gap.
```

### No frontend (report dashboard)

Adicionar card informativo (NAO afeta overall score):
- "Identidade Comunicativa: {score}/100"
- Sub-label: {diagnostico humanizado}
- Clicavel para detalhe: mostra exemplos de frases detectadas

### Criterios de Aceite sugeridos

1. Worker funcional que processa transcript e retorna score + vicios + autoridade ratio
2. Pelo menos 14 patterns de vicios emocionais e 17+15 patterns de autoridade/vitima
3. Score calculado corretamente (formula acima)
4. Salvo no banco como dimension "identity" na tabela analysis_results
5. Injetado no prompt do LLM
6. Exibido no dashboard como card informativo (sem afetar overall score)
7. Teste: reprocessar video de referencia (e4359918)
8. Retrocompatibilidade: avaliacoes antigas sem identity_result nao quebram

---

## FEATURE 6.10 — Analise de Abertura (Tecnica de Conexao)

### O que e
**Novo worker** que analisa os primeiros 15-20% do transcript para detectar se o orador usou alguma **tecnica de abertura profissional** que gera conexao, curiosidade ou impacto. Conforme o mentor definiu:

> *"Objetivo: fazer com que todas as pessoas que estao diante de voce parem o que estao fazendo e olhem para voce."*

### Tecnicas de abertura a detectar

| # | Tecnica | Descricao | Pattern de deteccao |
|---|---------|-----------|---------------------|
| 1 | **Frase de impacto** | Afirmacao forte e memoravel que abre a fala | Frases curtas (<10 palavras) no inicio com volume acima da media |
| 2 | **Pergunta reflexiva** | Pergunta que forca o ouvinte a pensar | Deteccao de `?` nos primeiros 20% do transcript |
| 3 | **Dado chocante** | Numero ou estatistica que surpreende | Deteccao de numeros/porcentagens nos primeiros 20% |
| 4 | **Piada / humor** | Leveza proposital para conectar | Difícil de detectar automaticamente — verificar se o transcript tem palavras de humor + volume/ritmo de humor (riso do falante, quebra de ritmo) |
| 5 | **Quebra-gelo** | Interacao direta com audiencia ("Quem aqui ja...?") | Pattern "quem aqui", "levantem a mao", "voces ja", "quantos de voces" |
| 6 | **Gancho com historia** | Comeca com narrativa pessoal/alheia | Pattern "quando eu", "ha X anos", "um dia", "lembro quando", "imagine", "era uma vez" |
| 7 | **Conexao com audiencia** | Fala diretamente PARA a audiencia | Pattern "voce que esta", "voces que", "pra voce que" |
| 8 | **Dado chocante** | Estatistica ou numero impactante | Numeros + palavras como "porcento", "%", "bilhoes", "milhoes" nos primeiros 20% |
| 9 | **Citacao de autoridade** | Abre com citacao de alguem famoso/respeitado | Pattern "como disse", "segundo", "nas palavras de" |

### Arquitetura do worker

**Novo arquivo:** `ml-worker/workers/opening_analyzer.py`

**Input:**
```python
def analyze_opening(
    transcription: dict,      # transcript do Whisper (full_text + words)
    voice_metrics: dict,      # metricas do voice_analyzer (volume, pausas)
    duration_seconds: float,  # duracao total do audio
) -> dict:
```

**Logica principal:**

```python
def analyze_opening(transcription, voice_metrics, duration_seconds):
    words = transcription.get("words", [])
    full_text = transcription.get("full_text", "")

    if not words or duration_seconds < 10:
        return {"disponivel": False, "motivo": "Video muito curto"}

    # Pegar os primeiros 20% do transcript
    total_words = len(words)
    opening_word_count = max(5, int(total_words * 0.20))
    opening_words = words[:opening_word_count]
    opening_text = " ".join(w["word"] for w in opening_words).lower()
    opening_end_time = opening_words[-1].get("end", 0) if opening_words else 0

    tecnicas_detectadas = []

    # 1. Pergunta reflexiva
    if "?" in opening_text:
        perguntas = [s.strip() for s in opening_text.split("?") if s.strip()]
        if perguntas:
            tecnicas_detectadas.append({
                "tecnica": "pergunta_reflexiva",
                "label": "Pergunta Reflexiva",
                "descricao": "Voce abriu com uma pergunta — isso ativa a curiosidade do ouvinte",
                "exemplo": perguntas[0][:100] + "?",
                "qualidade": "boa" if len(perguntas[0].split()) >= 5 else "fraca",
            })

    # 2. Dado chocante (numeros, estatisticas)
    import re
    numeros = re.findall(r'\b\d+[%]?\b|\b\d+[\.,]\d+\b', opening_text)
    palavras_impacto = re.findall(r'por ?cento|porcento|bilh[oõ]|milh[oõ]|mil\b|metade|dobro|triplo', opening_text)
    if numeros or palavras_impacto:
        tecnicas_detectadas.append({
            "tecnica": "dado_chocante",
            "label": "Dado / Estatistica",
            "descricao": "Voce usou dados numericos para gerar impacto na abertura",
            "exemplo": f"Numeros usados: {', '.join(numeros[:3])}",
            "qualidade": "boa",
        })

    # 3. Quebra-gelo (interacao com audiencia)
    patterns_quebra = [r"quem aqui", r"levant[ae]m?\s+a\s+m[aã]o", r"voc[eê]s j[aá]", r"quantos de voc[eê]s"]
    for p in patterns_quebra:
        if re.search(p, opening_text):
            tecnicas_detectadas.append({
                "tecnica": "quebra_gelo",
                "label": "Quebra-Gelo",
                "descricao": "Voce interagiu diretamente com a audiencia — isso gera conexao imediata",
                "qualidade": "boa",
            })
            break

    # 4. Gancho com historia
    patterns_historia = [r"quando eu", r"h[aá] \d+ anos", r"um dia", r"lembro quando", r"imagine", r"era uma vez"]
    for p in patterns_historia:
        if re.search(p, opening_text):
            tecnicas_detectadas.append({
                "tecnica": "gancho_historia",
                "label": "Gancho com Historia",
                "descricao": "Voce abriu com uma narrativa — historias ativam oxitocina (confianca)",
                "qualidade": "boa",
            })
            break

    # 5. Conexao direta com audiencia
    patterns_conexao = [r"voc[eê] que est[aá]", r"voc[eê]s que", r"pra voc[eê] que", r"voce que ta"]
    for p in patterns_conexao:
        if re.search(p, opening_text):
            tecnicas_detectadas.append({
                "tecnica": "conexao_audiencia",
                "label": "Conexao Direta",
                "descricao": "Voce falou diretamente PARA a audiencia — cria sensacao de conversa pessoal",
                "qualidade": "boa",
            })
            break

    # 6. Citacao de autoridade
    patterns_citacao = [r"como disse", r"segundo\s+\w+", r"nas palavras de"]
    for p in patterns_citacao:
        if re.search(p, opening_text):
            tecnicas_detectadas.append({
                "tecnica": "citacao_autoridade",
                "label": "Citacao de Autoridade",
                "descricao": "Voce referenciou uma autoridade — transfere credibilidade",
                "qualidade": "boa",
            })
            break

    # 7. Frase de impacto (frase curta + volume acima da media no inicio)
    primeira_frase = full_text.split(".")[0].strip() if "." in full_text else ""
    if primeira_frase and len(primeira_frase.split()) <= 10:
        volume_windows = voice_metrics.get("volume_por_janela", [])
        if volume_windows and len(volume_windows) > 1:
            media_vol = sum(volume_windows) / len(volume_windows)
            if volume_windows[0] >= media_vol:
                tecnicas_detectadas.append({
                    "tecnica": "frase_impacto",
                    "label": "Frase de Impacto",
                    "descricao": "Voce abriu com uma frase curta e forte — captura atencao imediata",
                    "exemplo": primeira_frase[:100],
                    "qualidade": "boa",
                })

    # Score de abertura
    if len(tecnicas_detectadas) == 0:
        score = 20  # Nao usou nenhuma tecnica
        diagnostico = "abertura_fraca"
        feedback = "Voce comecou falando sem usar nenhuma tecnica de conexao. O objetivo dos primeiros segundos e: fazer TODOS pararem o que estao fazendo e olharem pra voce."
    elif len(tecnicas_detectadas) == 1:
        score = 60
        diagnostico = "abertura_razoavel"
        feedback = f"Voce usou 1 tecnica ({tecnicas_detectadas[0]['label']}). Bom, mas ha espaco pra mais impacto."
    else:
        score = 85
        diagnostico = "abertura_forte"
        feedback = f"Voce usou {len(tecnicas_detectadas)} tecnicas de abertura. Abertura profissional."

    # Bonus: se tem pergunta E historia = combinacao poderosa
    tecnica_ids = {t["tecnica"] for t in tecnicas_detectadas}
    if "pergunta_reflexiva" in tecnica_ids and "gancho_historia" in tecnica_ids:
        score = min(100, score + 10)

    return {
        "disponivel": True,
        "score": score,
        "diagnostico": diagnostico,
        "feedback": feedback,
        "tecnicas_detectadas": tecnicas_detectadas,
        "tecnicas_ausentes": _get_sugestoes_ausentes(tecnica_ids),
        "opening_text": opening_text[:300],
        "opening_duration_seconds": round(opening_end_time, 1),
    }


def _get_sugestoes_ausentes(tecnicas_usadas: set) -> list:
    """Sugere tecnicas que o orador NAO usou."""
    todas = {
        "pergunta_reflexiva": "Pergunte algo que faca a audiencia PENSAR: 'Voce ja parou pra pensar...?'",
        "dado_chocante": "Abra com um numero que surpreenda: '93% das pessoas tem medo de falar em publico.'",
        "quebra_gelo": "Interaja direto: 'Quem aqui ja passou por isso? Levanta a mao.'",
        "gancho_historia": "Comece com uma historia: 'Quando eu tinha 23 anos, larguei tudo...'",
        "conexao_audiencia": "Fale diretamente PARA alguem: 'Voce que ta assistindo isso agora...'",
        "frase_impacto": "Abra com uma frase curta e forte: 'Poucas coisas custam tanto quanto o silencio.'",
        "citacao_autoridade": "Cite alguem respeitado: 'Como disse Warren Buffett...'",
    }
    ausentes = []
    for tecnica, sugestao in todas.items():
        if tecnica not in tecnicas_usadas:
            ausentes.append({"tecnica": tecnica, "sugestao": sugestao})
    return ausentes[:3]  # Top 3 sugestoes
```

### Integracao no pipeline

**No `app.py` — Novo Step 5.6 (apos identity_analyzer):**

```python
# Step 5.6: Analise de abertura (tecnica de conexao)
try:
    from workers.opening_analyzer import analyze_opening
    opening_result = analyze_opening(
        transcription, voice_result.get("metrics", voice_result), 
        video_metadata.get("duration_seconds", 0)
    )
except Exception as e:
    logger.error("opening_analysis_failed", error=str(e))
    opening_result = {"disponivel": False, "motivo": str(e)}

# Nao salvar como dimension separada — fica em aggregated_metrics
aggregated["opening"] = opening_result
```

### No prompt do LLM

```
## ANALISE DE ABERTURA
Score de abertura: {score}/100 ({diagnostico})
Tecnicas detectadas: {lista de tecnicas com descricao}
Feedback: {feedback}

Sugestoes de tecnicas nao usadas:
{lista de sugestoes}

INSTRUCAO: Se abertura_fraca, comece o feedback por isso. A abertura e o 
momento mais critico — o objetivo e fazer TODOS pararem e olharem pra voce. 
Se abertura_forte, celebre e sugira refinamento.
```

### No frontend (report dashboard)

Nova secao "Sua Abertura" ANTES das dimensoes, com:
- Score visual (como os outros cards)
- Lista de tecnicas detectadas (icone verde)
- Lista de tecnicas sugeridas (icone cinza)
- Texto do opening (primeiros 20% do transcript)

### Criterios de Aceite sugeridos

1. Detecta pelo menos 7 tipos de tecnica de abertura
2. Score de 0-100 baseado na quantidade e qualidade das tecnicas
3. Sugere ate 3 tecnicas que o orador NAO usou, com exemplo concreto
4. Texto dos primeiros 20% do transcript extraido e exibido
5. Se video < 10s, retorna `disponivel: False`
6. Injetado no prompt do LLM
7. Exibido no dashboard como secao propria
8. Teste: reprocessar video de referencia

---

## Sequencia de Implementacao Recomendada

```
Sprint 1 (2-3 dias):
  → Story 6.Q: Questionario novo (6 perguntas)
  → Story 6.1: Insights cruzados (prompt)
  → Story 6.2: Hierarquia de problemas (prompt)

Sprint 2 (3-4 dias):
  → Story 6.8: Identity Analyzer (novo worker)
  → Story 6.10: Opening Analyzer (novo worker)
```

### Dependencias entre stories

```
6.Q (questionario) ──→ 6.1 (insights cruzados usam motivacao)
                   ──→ 6.2 (hierarquia pode incluir abertura)
                   ──→ 6.8 (identity cruza com desejo_transmitir)

6.8 (identity) ────→ 6.10 (opening pode cruzar com identity score)
```

**A story 6.Q deve ser implementada PRIMEIRO** porque todas as outras dependem dos novos campos do questionario (motivacao, desejo_transmitir, desejo_melhorar).

---

## Checklist Final para @sm

Para cada story que voce criar, garanta que tem:

- [ ] Titulo claro e objetivo
- [ ] User story (As a / I want / So that)
- [ ] Acceptance Criteria testaveis (use essa spec como base)
- [ ] IN/OUT scope explicito
- [ ] Arquivos a modificar (listados acima por feature)
- [ ] Dependencias (sequencia acima)
- [ ] Complexidade estimada
- [ ] Riscos documentados
- [ ] Criteria of Done

**Use os EXEMPLOS CONCRETOS desta spec** nos acceptance criteria — eles sao testáveis.

**Use os SNIPPETS DE CODIGO** desta spec como referencia — o @dev pode usar como base.

**Use as TABELAS DE PATTERNS** (vicios emocionais, linguagem autoridade/vitima, tecnicas de abertura) como parte do escopo — nao invente, use exatamente o que esta aqui.

---

**Status:** SPEC COMPLETA. Pronto para @sm criar stories e @po validar.

— Aria, arquitetando o futuro 🏗️
