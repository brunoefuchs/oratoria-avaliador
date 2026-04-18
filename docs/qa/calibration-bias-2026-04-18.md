# Calibration Bias Report — 2026-04-18

**Context:** Diagnóstico Vinh pós primeiro coaching real em dados de prod (eval `8534ca9e-6c0a-47e9-9457-d0f30971c528`, score 50/100).

User perguntou: *"agora estamos avaliando mais certo? Pra se for ruim pegarmos, mas se for bom também reconhecermos?"*

**TL;DR:** App está **80% calibrado**. Os 20% restantes são enviesados pra **pegar ruim** mais que **celebrar bom**.

---

## ✅ Onde o app acerta (95% confiança)

### Punições justas (métricas objetivas quantitativas)

| Sinal | Dado | Veredito |
|---|---|---|
| Monotonia 75% tempo | cv_volume 0.0099 (ideal 0.03–0.25) | ✅ Ruim real |
| Fillers 6.7/min | 6 muletas em 54s | ✅ Ruim real (meta <3/min) |
| Smile 6.7% | MediaPipe detection 100% frames | ✅ Ruim real |
| Lock-in arquetípico | 100% Amigo em 5 janelas | ✅ Ruim real |

### Celebrações justas

| Sinal | Dado | Veredito |
|---|---|---|
| Alcance vocal | 21.6 semitons | ✅ Raro (>10 bom, >20 excepcional) |
| Gesto zona ideal | 91.4% | ✅ Faixa correta |
| Postura aberta | 100% frames | ✅ Medido objetivamente |
| 0 hesitações reais | "éé"/"humm" = 0 | ✅ Fluência confirmada |

---

## ⚠️ 4 Bias detectados — ainda injustamente punitivos

### Bias 1: Voice 55 — excelência mascarada pela média

**Problema:** Sub-score `Tom: 100` (alcance 21.6 semitons) é diluído no score geral 55.

Sub-scores atuais da Voz:
```
Tom: 100              ← EXCEPCIONAL
Velocidade: 65
Pausa: 42
Palavras/minuto: 50
Volume: 20            ← puxa média pra baixo
Média geral: 55       ← parece mediano
```

**Impacto:** User vê "Voz 55" e pensa "voz mediana". Na realidade, tem piano completo (Tom=100) + um vício de volume (Volume=20).

**Fix proposto:** Card da Voz destacar sub-score máximo em bold (ex: *"Tom 100 — alcance vocal excepcional"*) ANTES do score geral.

### Bias 2: Eye contact 95% não explicado como excesso

**Problema:** Banda Vinh ideal = 70–90%. User em 95.4% = **acima** (olhar fixo intimida). App baixou sub-score de 100 pra 71 mas **não explicou por quê**.

**Impacto:** User lê "Contato Visual 71" e pensa *"preciso olhar mais"*. **Contrário real:** olhar menos fixo, distribuir mais.

**Fix proposto:** Quando `eye_contact_pct > 90`, feedback deve dizer explicitamente *"olhar fixo demais — 95%, ideal 70–90, distribua mais pra evitar intimidação"*.

### Bias 3: Tonality=0 com ML dizendo "hap"

**Problema:** Canais contraditórios sem resolução:
- Heurística (jitter/shimmer): "tenso"
- Wav2Vec2 ML: "hap" dominante (0.468), valence 0.52

Score final = **0**. Heurística venceu ML em silêncio.

**Impacto:** Vídeo explicativo de internet não é emocionalmente "tenso" — é só voz um pouco apertada, estilístico/natural. Score 0 = punição injusta.

**Fix proposto:** Quando ML e heurística divergem, usar ML como tie-breaker (ML é mais robusto). OU reportar ambos separados (sem combinar num só score).

### Bias 4: Storytelling score=3 (regex rígida demais)

**Problema:** Regex procura frase canônica `"a razão de eu estar te contando é..."`. Vídeo explicativo tem estrutura didática válida (pergunta retórica → pensamento audience → revelação), mas não usa template formal Vinh.

**Impacto:** Regex confunde *"sem narrativa"* com *"narrativa não-canônica"*. Score 3 pune estrutura didática legítima.

**Fix proposto:** Threshold mais honesto:
- Score baixo + disclaimer *"estrutura didática detectada, mas sem Bridge formal"*
- OU categoria "analytical/instructional" distinta da Bridge narrativa

---

## ⚠️ 2 Bias de inflação (celebra demais)

### Bias 5: Postura 66 com vídeo curto (54s)

Alinhamento 90 + Aberto 100 + Ombros 99% mas Dinamismo=30 (parado).

Em vídeo de 54s, "parado" é normal. Em palco real de 20min, seria monotonia postural crítica. **Amostra curta esconde falta de variedade temporal.**

**Fix proposto:** Ajustar scoring de postura baseado em `duration_seconds`. Vídeos <2min: não penalizar dinamismo baixo.

### Bias 6: Gesto 85 idem

Em 54s você mantém 1 padrão gestual = zona ideal. Em palco longo, mesma coisa = repetitivo.

**Fix proposto:** Mesma lógica do Bias 5 — penalizar falta de variedade gestual só em vídeos >2min.

---

## Próximo marco — Gui Reginatto (ground truth ancora)

Gui Reginatto vai gravar vídeo **intencionalmente para ter nota alta** (mentor experiente, conhece framework Vinh). Esse é nosso **calibration anchor**:

### Hipóteses a validar com vídeo Gui

| Hipótese | Expectativa |
|---|---|
| H1: App reconhece excelência comunicativa real | Score ≥ 75/100 |
| H2: Variety > 50 (Gui cycla archetypes) | CV volume/pitch/velocidade altos |
| H3: Fillers < 3/min | Conte de muletas baixo |
| H4: Smile > 20% (Gui usa rosto) | Facial > 60 |
| H5: Archetypes > 60 (Gui cycla, não lock-in) | Diversidade + trocas/min > 0 |
| H6: Pausas retóricas > 3 | pyannote detecta >1.2s pauses |

### Falhas esperadas (calibration debt)

Mesmo com vídeo "perfeito":
- Voice score pode vir 70-80 se Volume sub-score puxar (**Bias 1 ainda ativo**)
- Storytelling pode pontuar baixo se Gui usar narrativa não-canônica (**Bias 4**)
- Tonality pode ser penalizada se Gui usar variação vocal intencional (heurística confunde com "tenso") (**Bias 3**)

### O que fazer com os resultados

Se Gui tirar >75 = app calibrado **o suficiente** pra identificar excelência. Os 4 bias viram follow-ups não-bloqueantes.

Se Gui tirar <65 = app tem **viés sistêmico contra boa comunicação**. Fix dos 4 bias vira prioridade P0 antes de qualquer usuário real.

---

## Recomendação de ação

1. **Usuário roda vídeo Gui agora** (não precisa fix prévio dos 4 bias)
2. **Resultado serve como teste de calibração**
3. **Ajustar escopo de fix** baseado em onde Gui perde pontos injustamente
4. **Story 9.7 (calibração pesos contextuais)** passa a incluir esses 4 bias no escopo — em vez de só pesos, também detalhes de sub-scoring e feedback

---

## Princípio Vinh — a justiça da avaliação

> *"If it distracts from the message, it's a problem. If it doesn't, leave it alone."*

App hoje pega distraction bem. Mas **às vezes marca como distraction coisa que não é** (ex: olhar 95% é excesso mas não é explicado, alcance raro é diluído).

**Calibração perfeita = punir o ruim com precisão E celebrar o bom com a mesma precisão.** Ground truth Gui vai nos dizer se estamos lá.
