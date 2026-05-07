# Evolving Report — Estado Markoviano

**Última atualização:** 2026-05-06 (Wave 1 + Follow-up 04 + Spec 05 + License Resolution)

## Estado atual

- Pipeline rodou 1 wave com 12 buscas paralelas (3 por track × 4 tracks).
- Coverage estimado em 78%; stop por cobertura suficiente para decisão de roadmap.
- Follow-up `04-deep-read-openface-hubert.md` aprofundou acionáveis #1 (HuBERT/WavLM) e #2 (OpenFace 3.0).
- Coverage pós-04 estimado em ~85% nos itens técnicos focados; demais tracks inalterados.

## Síntese consolidada

- **Insight principal:** os 5 itens de maior ROI cruzam tracks. Migração HuBERT (Track 4) habilita disentanglement de prosódia (Track 1). Adicionar `narrative_structure` (Track 3 gap) também é vetor de diferenciação (Track 2 gap competitor).
- **Risco principal:** ground truth com 7 vídeos é pequeno pra calibrar 14 dims. Antes de mexer em modelos, expandir corpus é prioritário.
- **Decisão default sugerida:** próximas 2 sprints focam em (1) HuBERT/OpenFace 3.0 swap + benchmark, (2) `narrative_structure` dim com Gemini Vision, (3) reproduzir AVI Challenge baseline.

## Refinamentos pós-04

- **#1 HuBERT/WavLM:** modelo padrão recomendado **WavLM-base+**; weighted-sum learnable sobre 12 layers; **NÃO** usar checkpoints ASR-fine-tuned (degradam prosódia). Layers 3-10 cobrem prosódia/voice quality; 10-18 (large) cobrem emoção.
- **#2 OpenFace 3.0:** Py3.12 viável (PyTorch puro, "Python 3.6+" floor); 2 gates antes de migrar — (a) cobertura FACS de AUs vs py-feat, (b) license file para uso comercial. Bridge curto: MediaPipe blendshapes → AUs aproximadas (válido mas NÃO 1:1 com FACS).
- **MediaPipe blendshapes → AUs:** mapping aproximado, "loosely correspond" — não substitui FACS canônico para validação científica.

## Wave 2 — Test comparativo concorrentes (06-*) — 2026-05-06

Evidência pública real (Duarte, G2 críticas, Reddit, support docs) substitui inferência de marketing copy do wave 1. Cobertura média 70%, Yoodli/Poised 85%, Elqo 40%.

### 3 contradições do wave 1
1. **Verble NÃO é debate AI** — é speech-writing service ($9.99 lifetime). Sai da matriz competitiva primária.
2. **Speeko licenciou Roger Love** — 1000+ exercises premium embarcados. "Voice resonance moat" foi parcialmente capturado como content licenciado (não como métrica científica). Implicação: dim "vocal_resonance" Roger Love-style perde força como diferenciador isolado.
3. **Críticas públicas validam tese Oratória Avaliador** — Duarte critica Yoodli pacing average (tu tem janela temporal); Reddit critica Yoodli/Poised feedback genérico (tu tem 24 hooks acionáveis); Duarte aponta ausência de body language em Yoodli (tu tem cross-modal). Moat técnico confirmado por crítico independente.

### Gap competitivo #1 identificado (em produto, não modelo)
**Practice mode multi-persona com memória multi-session (Yoodli Roleplay Memory).** Transforma produto de "boletim post-mortem" em "sparring partner". Maior diferencial Yoodli e onde captura valor B2B (Salesforce/Gong integration). Esforço alto.

### Riscos competitivos novos
- Elqo (PWA, $9.99/mo, 9 dims verbal+visual) — entrante mais agressivo, monitorar trimestralmente.
- Yoodli Admin Analytics + Salesforce — bloqueio B2B sales coaching.
- Speeko + Roger Love trump card pra moat de voz.

## Decisões finais Bruno 2026-05-06

- **#1 WavLM-base+:** APROVADO. Próxima sprint.
- **#2 Bridge MediaPipe blendshapes → AUs:** APROVADO. OpenFace 3.0 fica bloqueado em license CMU. Spec `05-*` é o caminho.
- **#3 discourse_arc + extensão storytelling_analyzer:** APROVADO. **Família = "narrativa"** (slot já reservado pela decisão arquitetural 2026-04-29 técnica/narrativa — não inventar "Substance"). Feature flag `NARRATIVE_FAMILY_ENABLED`. Critério de promoção: Pearson ≥0.6 vs Gui em ≥5/7 vídeos. Família técnica intocada em qualquer cenário; remoção limpa garantida.
- **#4 AVI Challenge 2025 baseline:** APROVADO. Roda em paralelo após #1 e #2 estabilizarem.
- **#5 Presença composta (Patsy 2nd Circle):** REJEITADO. Princípio Bruno: "melhor não medir do que medir errado". 7 vídeos GT + score composto = risco alto de feedback genérico. Movido pra Anti-recomendações em `03-recommendations.md`. Reabrir só com GT ≥25 vídeos + rating qualitativo separado.

## Refinamentos sessão 2026-05-06 (pós-04)

- **License OpenFace 3.0 RESOLVIDA → BLOQUEIO COMERCIAL.** Verificada via `gh api repos/CMU-MultiComp-Lab/OpenFace-3.0/contents/LICENSE`. License é "Academic or Non-Profit Organization Noncommercial Research Use Only" da CMU. Proíbe uso comercial, distribuir, sublicenciar. Termina automaticamente em violação. Pra Oratória Avaliador (produto comercial): inviável sem licenciamento via CMU OTM (semanas, custo variável).
- **Acionável #2 reordenado:** rota default agora é **MediaPipe blendshapes → AUs bridge** (Apache 2.0, comercialmente livre). OpenFace 3.0 vira fallback condicionado a licenciamento.
- **Spec 05 criado:** `05-mediapipe-au-bridge-spec.md` documenta mapping table 22 blendshapes → AUs, cobertura efetiva (10 AUs críticas pra oratória), protocolo de validação contra py-feat (Pearson ≥0.65, F1 ≥0.70, IoU ≥0.55), plano de migração 4 fases (spike 1d → bridge module 2d → validação 1-2d → migração condicional com feature flag).
- **Insight de descoberta de código durante sessão:** projeto JÁ TEM `opening_analyzer.py` (411 LoC, 9 técnicas) e `storytelling_analyzer.py` (743 LoC, 14+ tipos hook + bridge sentence + CTA + chemicals Vinh). Acionável #3 (`narrative_structure`) refinado para evitar duplicação: gap real é **discourse_arc macro** (progressão início→tensão→resolução do discurso completo) + **closure_quality** (callback abertura↔fechamento + tipos de payoff). Possível extensão em vez de dim nova — @pm decide.

## Próximas Markov-decisions (se houver follow-up)

- Wave 2 prioritária se Bruno quer: (a) Roger Love framework formal, (b) AVI Challenge baseline numbers, (c) WavLM-base+ checkpoint PT-BR/multilingual não-ASR-tuned (gap aberto no curiosity_queue).
- Skip wave 2 se decisão é só "começar a executar" — material atual basta.
- Próximo follow-up (`06-*`) potencial: deep-read `discourse_arc` design — rubric formal, baseado em Toastmasters Pathways + TOEFL Topic Development, com método de scoring via LLM e protocolo de validação Gui.
