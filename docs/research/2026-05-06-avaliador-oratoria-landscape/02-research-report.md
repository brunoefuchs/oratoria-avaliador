# Research Report — Avaliador de Oratória / Comunicação Landscape

**Data:** 2026-05-06
**Coverage:** 78% (1 wave, 12 buscas paralelas + conhecimento de treino até Jan 2026)
**Confidence legend:** [HIGH] = múltiplas fontes; [MED] = 1-2 fontes; [LOW] = inferência.

---

## Track 1 — SOTA Acadêmico 2024-2026

### 1.1 Tendências de pesquisa multimodal

- **AVI Challenge 2025** [HIGH] — track oficial de Multimodal Interview Performance Assessment com 3 modalidades (visual, áudio, texto), 6 respostas, 5 dimensões de avaliação. É o benchmark de avaliação multimodal mais relevante hoje pra o domínio adjacente (entrevista, mas as features se sobrepõem). Fonte: arXiv:2507.22676 ("Listening to the Unspoken").
- **Modality imbalance** [HIGH] — papel recente identifica problema sistemático: modelos multimodais favorecem features textuais por terem representação mais estruturada, subutilizando o sinal acústico crítico pra delivery. Há trabalhos com curriculum learning (arXiv:2508.12591) propondo MLLM unificado pra balancear.
- **Disentanglement prosódico** [HIGH] — embeddings SSL (wav2vec2/HuBERT/WavLM) misturam conteúdo linguístico com paralinguístico; trabalhos 2024-2025 (arXiv:2502.19387 "Residual Speech Embeddings for Tone Classification") propõem remover conteúdo linguístico pra reforçar análise paralinguística — relevante pro `voice_analyzer` do projeto.
- **Camadas relevantes** [MED] — em wav2vec2, **camadas iniciais** captam paralinguística/prosódia (rhythm, intonation), **camadas finais** captam conteúdo fonético. Implicação: extrair features de múltiplas camadas, não só da última.

### 1.2 Datasets

| Dataset | Modalidades | Tamanho | Foco | Status |
|---|---|---|---|---|
| **POM** (Persuasive Opinion Multimedia) | A+V+T | 1k vídeos | Persuasão | Clássico, ainda usado |
| **MIT Interview** | A+V+T | 138 entrevistas | Hireability, friendliness | Ground truth com PCC 0.98 alcançado |
| **FICS** (First Impressions) | A+V+T | 10k vídeos | Big-5 traits | Big-5 baseline, PCC 0.57 (Extraversion) |
| **AVI Challenge 2025** | A+V+T | — | Interview multimodal, 5 dims | Novo, ativo, relevante |
| **3MASSIV** | A+V+T multilíngue | 50k | Sentiment | Útil pra robustez idioma |

### 1.3 Estratégias de fusion

- **Late fusion** [HIGH] — superou early fusion em vários estudos comparativos 2025 (ex: aggression prediction 0.876 vs 0.828 acc). Mais robusto a modalidades assíncronas.
- **Early/feature fusion** [MED] — melhor quando modalidades são fortemente correlacionadas em curtas janelas temporais.
- **Intermediate/cross-attention** [HIGH] — transformers com cross-attention entre modalidades emergiram como SOTA (FLAVA, MMBT) — combinam vantagens das duas.
- **Recomendação para o projeto:** o projeto hoje opera **late fusion implícita** (cada dim é um analyzer independente, score combinado depois). Migrar pra cross-attention seria salto grande de complexidade — só justifica se gap calibração persistir após explorar Tracks 3 e 4.

### Papers Shortlist (Top 7)

1. **arXiv:2507.22676** — "Listening to the Unspoken: Exploring '365' Aspects of Multimodal Interview Performance Assessment" (2025) — AVI Challenge baseline.
2. **arXiv:2508.12591** — "Beyond Modality Limitations: A Unified MLLM Approach to Automated Speaking Assessment with Effective Curriculum Learning" (2025).
3. **arXiv:2502.19387** — "Residual Speech Embeddings for Tone Classification: Removing Linguistic Content to Enhance Paralinguistic Analysis" (2025).
4. **arXiv:2505.13688** — "Gaze-Enhanced Multimodal Turn-Taking Prediction in Triadic Conversations" (2025).
5. **PMC12733550** — "Bridging Text and Speech for Emotion Understanding: Explainable Multimodal Transformer Fusion" (2025) — explainability é underexplored, gap pro projeto.
6. **arXiv:2506.02891** — "OpenFace 3.0: A Lightweight Multitask System for Comprehensive Facial Behavior Analysis" (2025).
7. **MDPI Applied Sciences 2025** — "Early and Late Fusion for Multimodal Aggression Prediction" — comparação clean.

---

## Track 2 — Concorrentes Comerciais

### Tabela Comparativa

| Produto | Posicionamento | Dimensões expostas | Pricing 2025 | Diferencial |
|---|---|---|---|---|
| **Yoodli** | B2C+B2B coach + roleplay | Pacing (WPM), filler words, eye contact, pauses, perceived confidence, clarity, empathy | $19.99/mo Pro, free trial 7d | Roleplay com IA generativa (interview, sales, difficult convos); integração Zoom/Teams/Meet |
| **Poised** | Real-time durante calls | Confidence, clarity, filler count, pace, energy, eye contact | Free tier; Pro $10-20/mo | Coaching durante a chamada, não só replay |
| **Orai** | B2C app mobile + cursos | Speech clarity, pacing, confidence, filler words | $8-15/mo Pro, free trial 7d | Lições e cursos estruturados, gamificação |
| **Speeko** | B2C app mobile | Pace, vocal variety, filler words | Pago, sem free tier | Currículo adaptativo (lessons mudam por performance) |
| **Virtual Orator** | VR simulator | Não scoring — simulação ambiente | Pago (SideQuest/Steam) | Audiência virtual customizável; **não avalia, treina** |
| **Verble** | AI debate simulator | Logic, evidence, rhetorical strength, tone, persuasion score | — | Foco em debate/argumentação, não delivery |
| **Elqo** | B2C concorrente direto Yoodli | (similar Yoodli) | — | Mais novo no mercado |
| **BigSpeak** | Bureau de palestrantes (não app) | n/a | n/a | Não é avaliador, é marketplace |

### Vetores de diferenciação para Oratória Avaliador

1. **Calibração com mentor humano** [HIGH] — nenhum concorrente expõe ground truth blind validado por mentor real. Isso é o moat técnico.
2. **Profundidade de dimensões** [HIGH] — Yoodli expõe ~7 dims; Poised ~6. Oratória Avaliador tem 14 dims com famílias Look/Feel/Sound — narrativa estrutural mais rica.
3. **Português BR + cultura local** [HIGH] — todos os concorrentes são English-first; ground truth Gui em PT-BR é vantagem competitiva regional.
4. **Coaching pedagógico (24 hooks + congruence)** [MED] — recente sprint de calibração construiu camada pedagógica que vai além de feedback descritivo.
5. **Gemini Vision on-demand** [LOW] — uso seletivo de ML pago em dims onde matemática é fraca é insight de eficiência operacional que concorrentes podem não ter.

### Gaps que concorrentes deixam abertos

- **Storytelling/narrativa** — todos focam em delivery; nenhum avalia estrutura narrativa profundamente. (Oportunidade pra Track 3 → integrar rubric tipo Toastmasters Pathways.)
- **Performance corporal além do rosto** — gestos, postura, peso corporal ficam sub-explorados. Verble nem cobre; Yoodli cobre superficial.
- **Voz como instrumento (Roger Love-style)** — ressonância, breathiness, melody — ninguém scoreia bem.
- **Presença (Patsy Rodenburg "Second Circle")** — concept de "circulo" não é capturado em nenhum produto comercial.

---

## Track 3 — Rubricas Humanas

### 3.1 Toastmasters Pathways

[HIGH] — sistema oficial de evaluation forms (PDF resources em toastmasters.org). Cada projeto tem evaluation form específica. **Estrutura geral genérica:**

- **Speech objectives** — atingiu o goal do projeto?
- **Content** — clarity, organization, supporting material.
- **Delivery** — voice, gestures, eye contact, posture.
- **Language** — vocabulary, grammar, rhetorical devices.
- **Suggestions for improvement** (qualitativo).

### 3.2 TOEFL iBT Speaking Rubric (ETS) [HIGH]

3 componentes principais, scale 0-4:

| Componente | Sub-aspectos |
|---|---|
| **Delivery** | Pronunciation, flow, intonation, pacing |
| **Language Use** | Grammar, vocabulary range, accuracy |
| **Topic Development** | Coherence, completeness, idea progression |

Score automatizado pelo **SpeechRater** (ETS) — sistema interno usando ASR + NLP.

### 3.3 Patsy Rodenburg — Second Circle [HIGH]

Não é rubric, é **framework qualitativo** de presença:

- **First Circle** — energia inward (retraimento, monologue interno).
- **Second Circle** — energia em troca real com a audiência (dar e receber). Estado ideal.
- **Third Circle** — energia outward exagerada (broadcast, sem reciprocidade).

[LOW] Operacionalizar isso em ML é não-trivial. Proxies possíveis: variação de gaze + variação de tonalidade + responsividade (pause patterns). Squad já tem Patsy Rodenburg como mentora consultiva — vale aproximar do produto via heurísticas, não classificador direto.

### 3.4 Roger Love — Voice Framework [LOW]

Busca não retornou framework formal indexado. Conhecimento de treino: Roger Love trabalha com 5 melodias (rising, falling, mixed, monotone breaks), ressonância (chest/mask/head), volume dynamics, pitch range. Aplicável a `voice_analyzer` e `variety_analyzer`.

### Cross-walk Rubric × 14 Dimensões do Projeto

Assumindo as 14 dims = 3 famílias Look/Feel/Sound + articulation passivo. Sem acesso ao código exato, mapeamento aproximado:

| Rubric source | Dim coberta no projeto | Dim possivelmente ausente |
|---|---|---|
| **Toastmasters: Voice (Delivery)** | Sound: pitch/volume/pace | — |
| **Toastmasters: Gestures** | Look: gesture/body | — |
| **Toastmasters: Eye contact** | Look: gaze | — |
| **Toastmasters: Content/Organization** | ❓ provavelmente fraco | **Estrutura narrativa / abertura-meio-fim** |
| **Toastmasters: Language/Vocabulary** | ❓ | **Rhetorical devices, sticky language** |
| **TOEFL: Pronunciation** | Sound: articulation passivo | — |
| **TOEFL: Flow/Pacing** | Sound: pacing | — |
| **TOEFL: Topic Development (Coherence)** | ❓ | **Coherence linguístico** |
| **Patsy Rodenburg: 2nd Circle (presence)** | Feel: presença ❓ | **Reciprocidade/responsiveness — proxy difícil** |
| **Roger Love: Melody (5 padrões)** | Sound: variety/melody | **Padrões nomeados (rising/falling/mixed)** |
| **Roger Love: Resonance (chest/mask/head)** | ❓ | **Ressonância — gap claro** |

### Recomendações Track 3

- **GAP 1 — Estrutura narrativa**: nenhuma das 14 dims atuais (pelas memórias) cobre arco narrativo (gancho/desenvolvimento/payoff). Considerar dim NEW: `narrative_structure`.
- **GAP 2 — Ressonância vocal**: Roger Love distingue chest/mask/head; nenhum analyzer atual segmenta. Possível dim NEW: `vocal_resonance`.
- **REDUNDÂNCIA possível**: se `articulation` e `pacing` são separados, podem se sobrepor — TOEFL os trata como sub-itens de "Delivery". Considerar fundir como `delivery_quality` com sub-scores.
- **PRESENÇA (2nd circle)**: muito qualitativo. Operacionalizar como **score composto** (gaze variability × tonal variability × pause responsiveness) em vez de dim direta.

---

## Track 4 — Tecnologia Substituta

### 4.1 wav2vec2 → alternativas

| Modelo | Vantagem | Quando usar | Status |
|---|---|---|---|
| **HuBERT** | Match/supera wav2vec2; mais robusto | Drop-in substituto | HF disponível |
| **WavLM (Microsoft)** | Speaker-related downstream tasks | Quando precisa de identidade vocal | HF disponível |
| **w2v-BERT 2.0 (Google/Meta)** | Combina wav2vec2 + BERT + Conformer | Tarefas com forte componente fonético | HF (`facebook/w2v-bert-2.0`) |
| **Whisper-prosody** | ASR + features | Quando ASR já é dependency | HF |
| **NVIDIA NeMo** | Pipeline production-ready | Deploy em GPU | NVIDIA repo |

**Recomendação:** [HIGH] migrar pra **HuBERT** ou **WavLM** — são drop-in compatíveis na API HF; WavLM tem leve vantagem em paralinguística. Para prosódia pura, considerar **camadas iniciais** (ex: layer 4-6) em vez da última.

### 4.2 py-feat → alternativas

[HIGH] py-feat 0.6.2 é lento pra real-time e bloqueia Py3.12.

| Alternativa | Pros | Cons |
|---|---|---|
| **OpenFace 3.0** (arXiv:2506.02891, 2025) | Lightweight, multitask, mais rápido que py-feat e OpenFace 2.0 | C++ core, Python bindings menos maduros |
| **LibreFace** | AU + emotion, performance similar a OpenFace 3.0 | Comunidade menor |
| **PyFaceAU** | Implementação Python pura do pipeline OpenFace 2.2 | Compatível Py3.11 (Py3.12 não confirmado) |
| **MediaPipe FaceLandmarker** | Já usado no projeto (Iris); landmarks + blendshapes | AUs precisam ser mapeados de blendshapes — não são FACS canônicos |
| **EmoNet** | Emoção continuous (valence/arousal) | Não dá AUs |

**Recomendação:** [HIGH] **OpenFace 3.0** é a aposta mais sólida pra substituir py-feat — paper de 2025, ativo, mais rápido. Como bridge: usar **MediaPipe FaceLandmarker blendshapes** mapeados pra AUs aproximadas (rápido, já no stack).

### 4.3 Gaze — alternativas a MediaPipe-iris

| Modelo | Pros | Cons |
|---|---|---|
| **L2CS-Net** | Fine-grained, unconstrained env, PyTorch oficial | Requer face crop preciso |
| **ETH-XGaze** | Dataset 1M imagens, head poses extremos; modelos treinados generalizam bem | Modelo grande |
| **MPIIGaze** | Clássico, leve | Datasets antigos, perde em pose extrema |
| **MediaPipe Iris** (atual) | Rápido, já integrado | Sensível a pose extrema, oclusão |

**Recomendação:** [MED] manter MediaPipe Iris como default; **fallback L2CS-Net ou ETH-XGaze** quando MediaPipe falha (low confidence ou pose extrema). Ensemble traz robustez sem custo permanente.

### 4.4 Prosody/voice 2024-2026

[MED] Modelos relevantes:

- **emotion2vec / emotion2vec+** (Alibaba) — embeddings dedicados a emoção paralinguística.
- **TRILLsson** (Google) — embedding paralinguístico universal.
- **Whisper para alinhamento de palavras** — útil pra calcular pacing/pauses precisos.
- **Praat (parselmouth)** — features clássicas (jitter, shimmer, F0) ainda funcionam bem como features baseline.

### 4.5 Gesture / body pose

- **MediaPipe Holistic** — atual padrão; combinação de pose + face + hands.
- **MMPose** (OpenMMLab) — alternativa pesada mas mais precisa.
- **YOLOv8-pose** — ultraleve, real-time.
- **SAM-Pose / SAM 2** — recentes 2024, segmentation+pose.

### Lista priorizada de oportunidades técnicas (Track 4)

1. **[ALTA] HuBERT/WavLM como substituto wav2vec2** — drop-in, baixo risco.
2. **[ALTA] OpenFace 3.0 substituindo py-feat** — destrava Py3.12, ganha velocidade.
3. **[MÉDIA] Camadas iniciais wav2vec2/HuBERT pra prosódia** — pode reduzir gap em dims tonais sem novo modelo.
4. **[MÉDIA] L2CS-Net como fallback gaze** — ensemble com MediaPipe Iris pra robustez.
5. **[BAIXA] emotion2vec+ pra `voice_analyzer`** — feature extra, valor incremental.
6. **[BAIXA] Praat/parselmouth jitter/shimmer** — features clássicas como sanity check.

---

## Caveats globais

- Cobertura única wave (~78%) — não houve wave 2 nem deep-read. Para decisão técnica de produção, recomendo follow-up `04-*` antes de mover.
- Roger Love framework não confirmado por fontes web — basear em treino + livros oficiais requer leitura direta.
- AVI Challenge 2025 baseline é o benchmark mais relevante — considerar reproduzir para ter número absoluto comparável ao gap Gui (18-38pts).
