# Practice Mode — Spec de Implementação Futura

**Status:** Design draft. Não é story aprovada. Aguardando @pm priorizar.
**Origem:** Sessão research 2026-05-06 (`docs/research/2026-05-06-avaliador-oratoria-landscape/`), gap competitivo confirmado vs Yoodli (roleplay) e Poised (real-time).
**Autor:** sessão Claude + Bruno, 2026-05-06.

---

## 1. Por que existe

### Gap competitivo
Yoodli e Poised entregam loop de prática (gravar → feedback → gravar de novo) que Oratória Avaliador não tem. Hoje o produto é **review-only**: vídeo entra, ~30-60s+ de processing pesado, relatório completo sai. Bom pra diagnóstico, ruim pra prática iterativa.

### Restrição arquitetural atual
ml-worker roda 14 analyzers pesados (MediaPipe full holistic, voice analyzer com SSL embeddings, gesture, congruence cross-modal, articulation, storytelling, etc). Latência atual = ordem de minuto. Practice mode requer ordem de segundos.

### O que practice mode NÃO é
- Não é evaluation calibrada. GT ground truth fica protegido. Calibração técnica (gap 18-38pts vs Gui) não é tocada.
- Não é roleplay com IA generativa estilo Yoodli (entrevistador/cliente difícil) — feature separada, requer LLM agent dialógico.
- Não substitui review mode. Coexistem.

---

## 2. 3 níveis possíveis

| Nível | Latência | O que dá pra medir | Custo de implementação | Quando vale |
|---|---|---|---|---|
| **L2: Preview pipeline** | 60-90s pra vídeo de 2min | 6-8 dims subset rápido | ~1 sprint | Sempre — abre practice mode |
| **L1: Quase-tempo-real** | 5-15s em janelas de 10-30s | + smile/gaze/cadência/pausas longas | 2-3 sprints + WebRTC stack | Após L2 estável e com retenção |
| **L0: Real-time streaming** (estilo Poised) | <1s | Filler, pacing, volume, prosody básica | 4-5 sprints + browser-only stack | Só se concorrência forçar |

**Recomendação:** começar em **L2**. Cada nível abre features de produto diferentes; não é necessário escolher um só.

---

## 3. L2 — Preview Pipeline (Sprint 1)

### Conceito
Subset rápido dos analyzers atuais. Loop: usuário grava → preview rápido (~60-90s) → "tente de novo" ou "pedir análise completa" (vira evaluation full).

### Arquitetura

```
┌─────────────┐   POST /practice    ┌────────────────────┐
│   Frontend  │  ────────────────►  │  API gateway       │
│  (gravação) │                     │  pipeline_mode=    │
└─────────────┘                     │   preview          │
                                    └─────────┬──────────┘
                                              │
                                              ▼
                                    ┌────────────────────┐
                                    │  ml-worker         │
                                    │  preview_pipeline()│
                                    │  ─ pacing          │
                                    │  ─ filler_detector │
                                    │  ─ opening_analyzer│
                                    │  ─ smile (subset)  │
                                    │  ─ volume_var      │
                                    │  ─ pauses          │
                                    └─────────┬──────────┘
                                              │
                                              ▼
                                    ┌────────────────────┐
                                    │  practice_sessions │
                                    │  (TTL 7d)          │
                                    └────────────────────┘
```

### Subset de analyzers no preview

Ordem por velocidade × valor pedagógico:

| Analyzer | Latência | Por quê entra |
|---|---|---|
| `pacing` (Sound) | <1s | Derivado de transcript timestamps; sinal forte e instantâneo |
| `filler_detector` | <1s | Regex puro; feedback acionável imediato |
| `opening_analyzer` | <1s | Regex sobre primeiros 20%; já existe (411 LoC) |
| `smile` (subset Look) | ~3-5s | Só blendshape `mouthSmileLeft+Right`, sem brow/blink completo |
| `volume_variability` | ~2s | Feature básica de voice (variância por janela) |
| `pauses` | <1s | Derivado de transcript timestamps |

### O que NÃO entra no preview
- `congruence_analyzer` (cross-modal pesado)
- `gesture_semantic_analyzer` (full holistic)
- `storytelling_analyzer` em modo LLM (regex-only OK; LLM fallback NÃO)
- `articulation_analyzer` completo
- `voice_analyzer` SSL embeddings (HuBERT/WavLM via spec #1)
- `facial_analyzer` AUs completos (FACS via bridge #2)
- `tonality_analyzer`, `variety_analyzer`, `temporal_analyzer`, `posture_analyzer`, `archetype_classifier`, `identity_analyzer`

### Mudanças de código necessárias (pra @dev)

1. **Flag `pipeline_mode`** no orchestrator (`aggregator.py` ou entry-point):
   - `pipeline_mode = "full"` (default) → 14 analyzers (estado atual)
   - `pipeline_mode = "preview"` → 6 analyzers do subset
2. **Subset routing.** Função `run_preview_pipeline(video, transcript)` que ignora analyzers fora do subset.
3. **Schema de dados separado.** Tabela/coleção `practice_sessions`:
   - `id`, `user_id`, `created_at`, `video_path` (ou stream blob), `transcript`, `preview_metrics` (JSON com 6 sub-scores), `ttl` (7d default), `promoted_to_evaluation_id` (nullable).
   - **Não vai pra `evaluations`.** Não conta como ground truth, não exibe na lista de evaluations canônica.
4. **API endpoints:**
   - `POST /practice/sessions` — cria sessão preview, dispara `pipeline_mode=preview`.
   - `GET /practice/sessions/:id` — lê preview metrics.
   - `POST /practice/sessions/:id/promote` — promove pra evaluation (re-roda full pipeline, conecta ao GT mentor).
5. **Frontend:**
   - Nova rota `/practice` com gravação 1-3min.
   - UI mostra 6 dims preview com nomes simplificados ("velocidade", "muletas", "abertura", "expressão", "energia", "pausas").
   - Botão "Tentar de novo" (descarta sessão atual ou guarda em histórico).
   - Botão "Pedir análise completa" → promote → vira evaluation full (review-mode existente).

### UX considerations

- **Onboarding curto.** Primeira tela pede um tema rápido ("fala 60s sobre seu produto") ou template ("pitch 2min").
- **Não exibir scores 0-100 no preview.** Usar bandas qualitativas ("rápido" / "normal" / "devagar"). Score numérico fica em evaluation full — caso contrário usuário compara preview com evaluation e vai ver diferenças (sub-dims diferentes, calibrações diferentes).
- **Streak/histórico.** Mostra evolução das 6 dims preview ao longo das sessões. Já cobre 80% do valor de "currículo" sem currículo formal.
- **Reset semanal.** Practice sessions com TTL 7d. Usuário escolhe "salvar como evaluation" se quer permanência.

### Riscos do L2

| Risco | Mitigação |
|---|---|
| Usuário compara preview metrics com evaluation full e estranha divergência | Bandas qualitativas no preview, não score 0-100; copy explicando "preview rápido vs análise completa" |
| Preview vira fonte de calibração não-intencional | Schema separado `practice_sessions`; mentor Gui só pontua evaluations canônicas |
| Subset de 6 dims é interpretado como "o produto reduziu" | UI nomeia explicitamente "Modo Prática" vs "Análise Completa"; Análise Completa segue 14 dims |
| Latência de 60-90s ainda parece lenta pra "prática" | Loading state engajante (waveform, progress bar com etapas); aceitar que 60-90s é aceitable pro caso de uso |
| Storage cresce rápido (vídeos de prática) | TTL 7d default; comprimir vídeo client-side antes de upload; opção "não salvar vídeo, só métricas" |

### Custo estimado

| Item | Esforço |
|---|---|
| Flag + subset routing no ml-worker | 1-2d |
| Schema `practice_sessions` + endpoints API | 1d |
| Frontend rota `/practice` + gravação + preview UI | 2-3d |
| Histórico/streak básico | 1d |
| QA + UX polish | 1d |
| **Total** | **~1 sprint enxuta** |

---

## 4. L1 — Quase-tempo-real (Sprint 4-5, depois)

### Quando vale evoluir
- L2 estável com retenção comprovada (usuários voltam a praticar).
- Tu tem WebRTC ou stack de streaming.
- Worker leve (não Python pesado — Node ou Rust pra latência).

### O que muda
- Cliente envia chunks de 10-30s em streaming, server processa em janela deslizante.
- Subset ainda menor que L2: pacing + filler + volume + gaze básico.
- Feedback aparece como toast/overlay durante a fala ("acelerou", "muito 'éé'").
- **Cuidado pedagógico:** interrupção durante fala distrai (Patsy Rodenburg "first circle"). Toasts têm que ser sutis e configuráveis (off por default? on com timing?).

### Stack possível
- Cliente: MediaRecorder API + WebSocket.
- Server: Node ou Rust com worker leve (transcribe streaming via Whisper.cpp ou similar; regex pra filler; análise de volume via Web Audio).
- Não chama ml-worker Python pesado nessa rota.

### Custo estimado: 2-3 sprints + decisão de stack.

---

## 5. L0 — Real-time browser-only (estilo Poised, futuro distante)

### Conceito
Tudo client-side. Sem worker.

### Stack
- Web Speech API (transcript)
- Web Audio API (volume/pitch/RMS)
- MediaPipe Web (face landmarks + blendshapes — bate com bridge #2 do roadmap técnico)
- Latência <200ms.

### Trade-off
- Precisão menor (browser models são leves)
- Bom pra "treinador no ouvido", não pra "boletim".

### Custo estimado: 4-5 sprints. Só vale se concorrência forçar (Poised consolidar real-time como expectativa de mercado).

---

## 6. O que NÃO está no escopo deste spec

- **Roleplay com IA generativa** (estilo Yoodli — entrevistador, cliente difícil). Feature separada, requer LLM agent dialógico, deserve seu próprio spec.
- **Currículo estruturado** (estilo Orai — lições/cursos com progressão). Adjacente a practice mode mas é design de conteúdo, não infra.
- **Gamificação completa** (XP, badges, streaks visuais). L2 traz streak básico; gamificação completa é design de produto futura.
- **Mobile app nativo.** Practice mode L2 fica na web por enquanto. Mobile é decisão de plataforma separada.
- **Coaching adaptativo** (sugestão de exercícios baseado em fraquezas detectadas). Vem depois que tu tem dados de practice longitudinais.

---

## 7. Cuidados conceituais

- **Não rebatize practice como evaluation.** GT ground truth fica protegido. Practice é loop de melhoria; evaluation é diagnóstico calibrado.
- **Não use o subset L2 pra gerar feedback de evaluation.** Sub-dims diferentes, GT diferente, calibrações diferentes.
- **Não prometa "real-time" no L2.** Linguagem de produto = "feedback rápido" ou "preview". Real-time é L1/L0 e merece nome diferente.
- **Yoodli roleplay ≠ practice mode comum.** Roleplay precisa de LLM agent dialógico — outro spec.

---

## 8. Métrica de sucesso (pra validar antes de evoluir L2 → L1)

Após 1 mês de L2 em produção, validar:

| Métrica | Threshold pra justificar L1 |
|---|---|
| % usuários que rodam practice ≥3 vezes na semana | ≥40% |
| % sessões practice promovidas a evaluation | ≥15% |
| Tempo médio entre 1ª e 5ª session de practice | ≤14 dias |
| Net Promoter Score do feature practice | ≥40 |

Se métricas baixas, **não evoluir pra L1** — pode ser que o problema seja UX, conteúdo, ou que practice mode não é o gap percebido pelo usuário (talvez seja roleplay ou currículo).

---

## 9. Próximos passos

Para implementar:
- **@pm** — priorizar story `practice-mode-l2` no backlog. Criar epic se vai vir junto com features adjacentes (streak, coaching plan longitudinal).
- **@dev** — Sprint 1 conforme custos da seção 3.
- **@ux-design-expert (Uma)** — desenhar fluxo de gravação, copy de "preview vs análise completa", banding qualitativo das 6 dims preview.

Para refinar este spec antes de virar story:
- Decidir se preview salva o vídeo ou só métricas (impacto storage).
- Decidir se práticas com tema livre ou guiadas por templates ("pitch 2min", "abertura impactante").
- Decidir se streak é por dia, por semana, ou por contagem absoluta de sessões.

---

**Referências:**
- Pasta de research: `docs/research/2026-05-06-avaliador-oratoria-landscape/`
- Concorrentes referência: Yoodli (roleplay), Poised (real-time), Orai (currículo)
- Memória relevante: `feedback_no_measurement_over_bad_measurement.md` (banding qualitativo no preview alinha com este princípio — não exibir scores que podem confundir)
