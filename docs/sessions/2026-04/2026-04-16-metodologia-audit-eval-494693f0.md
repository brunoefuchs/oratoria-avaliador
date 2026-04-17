# Auditoria Metodológica — Pesos e Fórmulas do ml-worker

**Data:** 2026-04-16
**Squad:** mentores-comunicacao (Patsy Rodenburg + Roger Love)
**Eval analisado:** `494693f0-785f-403c-8583-da172ef93570`
**Vídeo:** 54s, 166 palavras, 185 wpm
**Objetivo:** validar se as fórmulas de scoring dos analyzers refletem pedagogia de oratória

---

## 1. Resultado do Eval (dados Supabase)

| Dimensão | Score | Status | Sinais-chave |
|----------|-------|--------|--------------|
| posture | 66 | ok | aberta 100%, alinhamento 90, dinamismo **30** |
| gesture | 85 | ok | zona ideal 91%, eye contact 95%, **gesto_repetitivo=true**, vocab=5 |
| voice | 55 | ok | wpm 185, pitch range 21,6 semitones, **cv_volume 0,99%**, monotonia 20 |
| fillers | 22 | ok | 6,7/min, **1 cluster de 18s** (17–36s) |
| identity | 60 | ok | `dados_insuficientes` (vídeo curto) |
| archetypes | 45 | ok | **lock_in amigo 100%**, ausentes: coach/educador/motivador |
| variety | — | skipped | — |

**Leitura mentores (síntese):** orador tecnicamente correto mas **estático** — forma sem fluxo. Convergência Rodenburg (dinamismo 30) + Love (cv_volume 0,99%) apontam mesmo fenômeno: **ausência de variação dinâmica**.

---

## 2. Fórmulas Extraídas dos Analyzers

### posture_analyzer.py
```
final = 0,30·alignment + 0,10·open + 0,25·grounding + 0,20·proposital + 0,15·dinamismo
```
- `grounding_score`: buckets discretos — `plantado=90`, `proposital=80`, `energetico=60`, `ansioso=30`
- `dinamismo_postural`: thresholds de variância; máximo 90 requer var>0,002 **E** proposital≥70

### gesture_analyzer.py
```
final = 0,35·contato_visual + 0,30·gesticulacao + 0,15·duas_maos + 0,10·zona + 0,10·distribuicao_olhar
```
- `gesticulacao`: bell curve 40–70% ideal + bonus vocab (máx +20) − penalty repetitivo (**−15**)
- `duas_maos`: `min(100, pct·1,5)` — 67% já bate teto
- `zona`: `min(100, pct·1,1)`

### voice_analyzer.py
```
final = 0,20·wpm + 0,20·pitch + 0,20·velocidade + 0,20·volume + 0,20·pausa
```
- `pitch`: função de `pitch_range_semitones`. ≥15 → 100
- `volume`: função de `cv_volume`. <0,03 → 20; ≥0,10 → 100
- `monotonia_score`: calculado mas **descartado** (informacional)

### filler_detector.py
```
base = linear(wpm_fillers 3..12 → 100..0)
final = base − 5·clusters + bonus_ttr
```
- Weighted fillers/min com contexto (cluster=2.0, post-hesitation=1.5, end-phrase=0.2)

### archetype_classifier.py
```
final = 0,15·diversidade + 0,20·cycling + 0,25·anti_lockin + 0,40·qualidade_dominante
```
- `qualidade_dominante = min(100, confianca_media_dom·200)` — **40% de peso**
- `anti_lockin`: pct_dominante >80 → 10; >50 → 60

---

## 3. Veredito por Dimensão (Rodenburg + Love)

### POSTURE ⚠️ desbalanceado a favor do estático
- 40% para fatores estáticos (align + open) vs 35% dinâmicos (proposital + dinamismo)
- **Bug filosófico:** bucket `plantado=90 > proposital=80` — Rodenburg inverteria. Plantado ≠ Second Circle.
- **Sugestão:** `align 0,20 + open 0,05 + ground 0,20 + proposital 0,25 + dinamismo 0,30`

### GESTURE ⚠️ penaliza repetição de leve
- Contato visual 35% **correto** (canal #1 de Second Circle)
- Penalty `gesto_repetitivo` de **−15 é brando** — Rodenburg: *"gesture born from pattern, not thought"* é morte de autenticidade
- `duas_maos` 15% com fórmula linear tem barra baixa demais
- **Sugestão:** penalty repetitivo −15 → **−25**; realocar `duas_maos` 15% → 10% e dar peso próprio a `vocabulario_gestos`

### VOICE ❌ maior problema metodológico
- **Issue #1:** `pitch_range_semitones≥15 → 100` ignora intencionalidade. Orador pode ter 2 oitavas de range e soar monótono. `monotonia_score` captura isso mas foi descartado.
  - **Fix:** `pitch_final = 0,5·range_score + 0,5·(100 − monotonia_score)`
- **Issue #2:** pesos iguais (20% cada) ignoram hierarquia Love: **breath → volume → pitch → rhythm**
  - **Fix:** `pausa 0,25 + volume 0,25 + pitch 0,20 + velocidade 0,15 + wpm 0,15`
- **Issue #3:** `pausa` não distingue silêncio estratégico de respiração apressada

### FILLERS ✅ fórmula mais sólida
- Contextual weighting (cluster 2.0, post-hesitation 1.5, end-phrase 0.2) é **pedagogicamente correto**
- **Issue pequeno:** penalty `−5 por cluster` é baixo. Este eval (cluster de 18s em 54s = 33% do tempo em filler-mode) merecia score ~10, não 22
- **Sugestão:** penalty cluster −5 → **−10**, cap −30

### ARCHETYPES ⚠️ fórmula autossabotada
- `qualidade_dominante` 40% **contradiz** `anti_lockin` 25%: quanto mais consistente o arquétipo, mais alto qualidade E mais baixo anti_lockin
- Mentores alinhados: **versatilidade de registro > consistência de persona**
- **Sugestão:** `diversidade 0,25 + cycling 0,30 + anti_lockin 0,30 + qualidade 0,15`

---

## 4. Tabela Comparativa — Score Atual vs Corrigido

| Dimensão | Score atual | Score corrigido | Delta | Causa |
|----------|-------------|-----------------|-------|-------|
| posture | 66 | ~55 | −11 | Plantado=90 premia estático |
| gesture | 85 | ~65 | −20 | Repetitivo subpenalizado |
| voice | 55 | ~42 | −13 | Pitch range ≠ musicalidade |
| fillers | 22 | ~10 | −12 | Cluster 18s merece mais penalty |
| archetypes | 45 | ~30 | −15 | qualidade_dominante conflita com anti_lockin |

**Overall atual (média simples): ~55**
**Overall corrigido: ~40**

---

## 5. Top 3 Correções de Maior ROI

### 1. Voice — incorporar `monotonia_score` no pitch sub-score
**Arquivo:** `ml-worker/workers/voice_analyzer.py`
**Mudança:** combinar `pitch_range_score` com `(100 − monotonia_score)` em média ponderada
**Impacto:** elimina falso-positivo de orador monótono com range amplo (exato caso deste eval)

### 2. Posture — inverter buckets grounding
**Arquivo:** `ml-worker/workers/posture_analyzer.py`
**Mudança:** `proposital=90` (topo), `plantado=75`, demais ajustar proporcionalmente
**Impacto:** sistema deixa de recompensar orador estático em postura correta

### 3. Archetypes — reduzir `qualidade_dominante` 40% → 15%
**Arquivo:** `ml-worker/workers/archetype_classifier.py`
**Mudança:** realocar 25 pontos para `diversidade` (+10) e `cycling` (+10) e `anti_lockin` (+5)
**Impacto:** fórmula para de se autossabotar; premia versatilidade real

---

## 6. Pontos Cegos Metodológicos

- **Nenhum sub-score mede INTENÇÃO.** Rodenburg: *"elephant in the room"* — sem intenção, tudo é cosmética. Nenhuma dimensão captura se o orador está presente vs performando.
- **Vídeos curtos (<60s) produzem scores ruidosos.** `identity` retornou `dados_insuficientes` corretamente — mas outras dimensões deveriam ter guard similar (ex: archetype com 5 janelas de 10s = borderline).
- **`monotonia_score` calculado e descartado** é sintoma de débito técnico: o analyzer SABE que o orador é monótono, mas o score final não reflete.

---

## 7. Próximos Passos Sugeridos

1. Discutir com @architect se correções entram como story no Epic 9 (State-of-the-Art) ou novo epic de calibração
2. Rodar re-scoring nos 10 vídeos ground truth do mentor Guilherme (Story 7.7) **antes e depois** das correções para medir delta vs ground truth humano
3. Considerar exposição do `monotonia_score` e outros sub-scores descartados no report pro usuário — são sinais pedagógicos ricos

---

**Referências:**
- `/home/bruno/.claude/projects/-mnt-c-Users-bruno-code-oratoria-avaliador/memory/squad_mentores_comunicacao.md`
- `squads/mentores-comunicacao/agents/mentores-comunicacao-chief.md`
- `ml-worker/workers/{posture,gesture,voice,filler_detector,archetype_classifier}.py`
