# Recomendações Priorizadas

**Aviso:** Sem código de produção. Decisões de implementação ficam com @pm/@dev.

## Top 4 Acionáveis (ordem de ROI estimado)

> Originalmente 5 itens. Item #5 (presença Patsy 2nd Circle) rejeitado em 2026-05-06 por princípio "não medir > medir errado". Movido pra Anti-recomendações.

### 1. [TÉCNICO — ALTA] Migrar wav2vec2 → HuBERT/WavLM
- **Por quê:** wav2vec2 saiu do HF (memória); HuBERT/WavLM são drop-in com API compatível e equivalente ou superior em paralinguística.
- **Esforço:** baixo (1-2 dias).
- **Risco:** baixo — pode rodar A/B contra ground truth Gui pra validar antes de switch.
- **Bônus:** extrair de **camadas iniciais** (4-6) pra prosódia, não só última.

### 2. [TÉCNICO — ALTA] Bridge MediaPipe blendshapes → AUs (substitui py-feat)
- **Por quê:** py-feat 0.6.2 bloqueia Py3.12 e é lento. **OpenFace 3.0 está bloqueado comercialmente** (CMU "Academic or Non-Profit Noncommercial Research Use Only" — verificado 2026-05-06 via gh api). Rota viável: MediaPipe FaceLandmarker já no stack (Apache 2.0) expõe 52 blendshapes ARKit-style mapeáveis pra ~22 AUs FACS aproximadas.
- **Cobertura efetiva:** 10 AUs críticas pra oratória (AU1, AU2, AU4, AU5, AU6, AU7, AU9, AU12, AU15, AU45) ficam cobertas. Caveat científico: blendshapes "loosely correspond" a FACS canônicos, não 1:1.
- **Esforço:** 4-5 dias até promoção (Fase 0 spike 1d + bridge module 2d + validação contra py-feat 1-2d).
- **Risco:** falha em critérios de aceite (Pearson ≥0.65, F1 ≥0.70, IoU ≥0.55 nas 10 AUs críticas) → fica em modo hybrid (bridge para AUs aprovadas, py-feat para o resto). Não é catástrofe.
- **Spec completo:** `05-mediapipe-au-bridge-spec.md` (mapping table, protocolo de validação, plano de migração 4 fases).
- **Bypass disponível:** Fase 0 sozinha (1 dia, só liga `output_face_blendshapes=True` no FaceLandmarker existente) já desbloqueia Py3.12 informacionalmente — tu fica sabendo se rota é viável antes de comprometer.

**Alternativa OpenFace 3.0 via licenciamento comercial:** contatar CMU Center for Technology Transfer / OTM. Tempo: semanas. Custo variável. Só vale se bridge MediaPipe falhar nos critérios e os 22 AUs do OpenFace 3.0 ficarem indispensáveis.

### 3. [PRODUTO — ALTA] Adicionar dim `discourse_arc` na família "narrativa"
- **Refinamento pós-auditoria de código:** projeto já tem `opening_analyzer.py` (9 técnicas de hook calibradas) e `storytelling_analyzer.py` (14+ tipos de hook + bridge sentence + CTA + chemicals Vinh). Hook e fechamento já cobertos. **Gap real é o arco macro do discurso completo** — progressão início → tensão → resolução. Nenhum analyzer mede isso hoje.
- **Família:** "narrativa" — slot já reservado arquiteturalmente pela decisão 2026-04-29 (separar overall em `family_score_técnica` calibrada + `family_score_narrativa` próxima fase). `discourse_arc` é a primeira dim a povoar essa família. NÃO inventar família "Substance".
- **Por quê:** gap claro vs Toastmasters Pathways "Content/Organization" e TOEFL "Topic Development". Concorrentes (Yoodli, Poised, Orai) não cobrem arco narrativo — diferenciação.
- **Como:** scoring via Gemini Vision sobre transcript completo (rubric explícita citando Toastmasters/TOEFL/Dicks/Hall — não inventa). Output estruturado JSON: discourse_type (lista|argumentação|narrativa|explicativo) + score 0-100 + label categórico do arco + justificativa citando trecho. Determinismo: temperature=0, seed fixo, prompt versionado.
- **Estender `storytelling_analyzer`** (não dim nova) com callback abertura↔fechamento + tipos de payoff (insight, imagem, CTA, lição). Reusa infra existente.
- **Feature flag:** `NARRATIVE_FAMILY_ENABLED` (padrão Epic 9). Envolve a dim E a exibição da family no report.
- **Critério de promoção:** Pearson ≥0.6 vs Gui em ≥5/7 vídeos (mesmo bar Epic 9). Se falhar → flag fica `false`, dim some, family "narrativa" volta a "próxima fase".
- **Garantia de remoção limpa:** família técnica intocada em qualquer cenário (rodando bem, ruim, ou removida). Overall score só vira `weighted_avg(técnica, narrativa)` após promoção; antes disso é só `family_técnica` puro.
- **Validar:** com Gui em vídeos GUI ITAJAI/PRIME (mentor padrão) antes de generalizar pros outros 5.

### 4. [CALIBRAÇÃO — ALTA] Reproduzir AVI Challenge 2025 baseline
- **Por quê:** dá número absoluto pra ancorar gap 18-38pts vs Gui. Hoje é só relativo. Saber se gap é grande "no absoluto" muda priorização.
- **Esforço:** médio-alto (semana). Vale o investimento — produz métrica defensável pra investidores e mentores.

### 5. ~~Refinar dim "presença" via Patsy 2nd Circle~~ — **REJEITADO 2026-05-06**

**Decisão Bruno:** não medir. Movido pra Anti-recomendações abaixo.

**Razão:** princípio de produto "melhor não medir do que medir errado". Score composto de 3 sinais (gaze_var × tonal_var × pause_responsiveness) com 7 vídeos de ground truth tem alto risco de virar feedback genérico — pior que ausência de feedback em produto de oratória. Reabrir só com (a) corpus GT ≥25 vídeos, (b) rating qualitativo separado de "presença sentida", (c) plano de degradação (não exibir se confiança baixa).

---

## Recomendações Secundárias

### Tecnologia (pode esperar)

- **L2CS-Net como fallback gaze** — só se MediaPipe Iris mostrar falhas concretas em pose extrema nos 7 vídeos de teste.
- **emotion2vec+ pra voice_analyzer** — incremental; vale só após HuBERT estabilizado.
- **MMPose substituindo MediaPipe Holistic** — não justifica troca a menos que gesture analysis fique no top-3 de gaps.
- **Praat/parselmouth (jitter, shimmer, F0)** — features clássicas como sanity check independente; baixo custo, valor de auditoria.

### Produto

- **Roger Love voice ressonância (chest/mask/head)** — gap claro mas operacionalização é incerta. Esperar literatura mais sólida ou tratar via Gemini Vision com prompt dirigido.
- **Fundir `articulation` + `pacing` em `delivery_quality`?** — investigar antes de mexer; a separação pode ser pedagogicamente valiosa mesmo se redundante estatisticamente. Validar com mentor.
- **Storytelling layer** — separado de `narrative_structure`: detectar uso de specifics, dialogue, sensory details (Matthew Dicks, Kindra Hall). Roadmap longo.

### Calibração

- **Cross-validar contra TOEFL SpeechRater output** — se possível obter scores SpeechRater nos vídeos de teste, ancora qualidade ASR/prosódia em padrão da indústria.
- **Aumentar ground truth pra >7 vídeos** — 7 é frágil pra calibração de 14 dims; mirar 25-30 vídeos antes do próximo sprint major.

---

## Anti-recomendações (não fazer)

- ❌ **Migrar pra arquitetura cross-attention transformer multimodal** — salto grande de complexidade; 14 analyzers independentes (late fusion) ainda têm runway antes de virar gargalo.
- ❌ **Adicionar dim "perceived confidence" estilo Yoodli** — é proxy ruim, vira feedback genérico. Manter foco em dims diagnósticas (que sugerem ação) em vez de descritivas.
- ❌ **Dim composta de "presença" (Patsy 2nd Circle)** — score composto de gaze_var × tonal_var × pause_responsiveness. Decidido 2026-05-06 (Bruno): risco de feedback genérico > valor de cobrir o conceito. Princípio: "melhor não medir do que medir errado". Reabrir só com corpus GT ≥25 vídeos + rating qualitativo "presença sentida" + plano de degradação. Mantém o conceito Patsy como guia de design, não como dim mensurada.
- ❌ **Trocar MediaPipe Holistic por SAM-Pose** — overkill; MediaPipe é bom suficiente até prova em contrário.
- ❌ **Investir em VR (estilo Virtual Orator)** — é praticar, não avaliar. Fora do core.

---

## Escopo NÃO coberto / Próximos research

- Datasets novos pós-Jan 2026 (pode haver lançamentos relevantes não capturados).
- Roger Love framework formal — requer leitura direta de "Set Your Voice Free" (livro).
- Comparação custo cloud/inference por dim (Gemini Vision $ vs HuBERT self-hosted) — análise operacional separada.
- Análise de Elqo (concorrente direto Yoodli novo) — fonte mencionou mas não detalhou.
- Latência ponta-a-ponta dos concorrentes (Yoodli/Poised real-time) — não foi pesquisado.

Para implementar qualquer item: **acionar @pm pra priorização de stories, depois @dev pra execução**. Esta pesquisa é para informar, não para executar.
