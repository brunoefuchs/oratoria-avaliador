# 04 — Deep-Read: OpenFace 3.0 + HuBERT/WavLM Layer-Wise

**Data:** 2026-05-06
**Foco:** Eliminar caveat de cobertura rasa nos acionáveis #1 (HuBERT/WavLM) e #2 (OpenFace 3.0) do report base.
**Wave:** 1 (3 fontes deep-read + 2 search aggregations).

---

## Foco 1 — OpenFace 3.0 vs py-feat (acionável #2)

### Verdict rápido

**Py3.12 viável: SIM (alta confiança).** OpenFace 3.0 é pacote Python puro (PyTorch + OpenCV + NumPy + Pillow + gdown), instala via `pip install -r requirements.txt` + `pip install openface-test` + `openface download`. README declara "Python 3.6+" — formulação floor, não ceiling. PyTorch tem suporte oficial Py3.12 desde 2.2 (2024). Sem código C++ a recompilar (diferente de OpenFace 2.x). [HIGH]

### Arquitetura (paper arXiv:2506.02891 + repo)

- **Modelo unificado multitask:** lightweight, single-pass extrai landmarks + AUs + gaze + emoção. [HIGH]
- **Pipeline declarado no README:**
  - Face detection: **RetinaFace**
  - Landmarks: **STAR**
  - AUs: muscle activity intensity (lista exata não exposta no README)
  - Emoção: **8 categorias AffectNet**
  - Gaze: **yaw + pitch**
- **Framework:** PyTorch. CPU ou CUDA via parâmetro `device='cpu'|'cuda'`. [HIGH]
- **Real-time sem hardware especializado** declarado no abstract. Números FPS exatos não estão no abstract nem no README; benchmarks ficam no corpo do PDF (não acessíveis ao deep-read). [MED — verificar localmente]

### vs py-feat (gap-analysis)

| Aspecto | py-feat 0.6.2 | OpenFace 3.0 |
|---|---|---|
| Python | bloqueia 3.12 (memória do projeto) | 3.6+ declarado, 3.12 esperado funcionar |
| Stack | mistura PyTorch + sklearn + várias libs | PyTorch puro + OpenCV |
| Velocidade | lento p/ real-time (memória do projeto) | "lightweight, real-time" claim |
| AUs | FACS-canônicos (treinados em DISFA, BP4D) | "muscle activity intensity" — cobertura FACS específica não exposta no README; conferir no paper |
| Multi-task | não unificado | unificado em single forward-pass |
| Repo activity | py-feat lentidão e bugs conhecidos | 45 commits, ativo em 2025 |
| GitHub | py-feat/py-feat | CMU-MultiComp-Lab/OpenFace-3.0 |
| License | MIT (py-feat) | LICENSE no repo, tipo não confirmado no preview — IEEE FG 2025 paper sugere uso de pesquisa OK [MED] |

### Risco a investigar antes de migrar

1. **Lista exata de AUs detectadas** — paper enumera; README não. Bloqueio: não foi possível extrair via WebFetch o corpo do PDF (`-` retornou estrutura vazia). Recomendo download manual + leitura local da seção "Methods" do paper antes de comprometer.
2. **Cobertura FACS canônica** — se OpenFace 3.0 detecta menos AUs que py-feat (que cobre ~20 AUs FACS), pode haver gap em features que o `facial_analyzer` atual usa. Validação obrigatória contra `facial_analyzer.py` atual nos 7 vídeos de teste.
3. **License** — confirmar no LICENSE file antes de uso comercial. IEEE FG 2025 standard terms permitem "personal use" — comercial requer leitura.
4. **Formato output** — verificar compatibilidade com pipeline atual (CSVs por frame, formato de timestamps, normalização de coords).

### MediaPipe FaceLandmarker blendshapes → AUs (bridge plano-B)

**Validade científica: aproximada, não canônica.** [HIGH]

- MediaPipe entrega **52 blendshapes** estilo ARKit (jawOpen, browInnerUp, mouthSmileLeft, etc.), derivados do face mesh.
- ARKit blendshapes "loosely correspond" a FACS AUs — relação **não 1:1**. Várias AUs FACS canônicas não têm blendshape direto; vários blendshapes não correspondem a AU FACS.
- **Existe biblioteca pronta:** `py-feat/mp_blendshapes` no HuggingFace — extensão py-feat que aceita blendshapes MediaPipe e estima AUs aproximadas. Ironicamente é parte do ecossistema py-feat, então pode herdar o mesmo bloqueio Py3.12. Verificar.
- **Recomendação como bridge:** funciona para destravar Py3.12 em horas, **mas não substitui validação contra ground truth Gui** — diferenças de AU mapping podem mover scores em dimensões `feel:expressivity` e `look:micro-expressions`.

### LibreFace e PyFaceAU (alternativas)

Não foi possível deep-read nesta wave. Sinal fraco do report base sugere que ambas têm comunidade menor. Recomendação: **OpenFace 3.0 como aposta principal**, LibreFace como fallback se OpenFace 3.0 tiver bloqueio inesperado em commercial use.

---

## Foco 2 — HuBERT/WavLM Layer-Wise (acionável #1)

### Verdict rápido

**Recipe prática:**
- **Prosódia / paralinguística (rhythm, intonation, voice quality):** camadas **iniciais a médio-iniciais** (em base 12-layer: ~3–8; em large 24-layer: ~6–14).
- **Emoção:** camadas **médias** (combinação de paralinguístico + contexto). Em large: ~10–18.
- **Conteúdo fonético/ASR:** camadas **finais**.
- **Default ideal:** **weighted-sum learnable** sobre todas as 12/24 camadas (protocolo SUPERB). Pesos aprendidos são interpretáveis e raramente convergem na última camada para tasks paralinguísticas. [HIGH]

### Evidências quantitativas

[HIGH] Múltiplas fontes confirmam o padrão de especialização:

> "Initial layers encode fundamental timbre and prosody; middle layers synthesise abstract traits; and final layers suppress speaker identity to abstract linguistic content."

> "Lower layers tend to preserve low-level acoustic cues such as formant structures, energy dynamics, and spectral patterns, while upper layers encode higher-level information such as phonetic boundaries, lexical units, and long-range contextual semantics."

[MED] Caso específico:
> "HuBERT embeddings obtained from early layers yield the best result (~95.7% accuracy with SVM) for singing phonation classification."

[HIGH] Achado contra-intuitivo crítico:
> "Fine-tuning ASRs does not facilitate the downstream speech emotion recognition task, indicating a loss of prosodic information during ASR fine-tuning."

→ **Implicação direta pro projeto:** se algum analyzer estiver usando modelo wav2vec2/HuBERT já fine-tuned em ASR, está degradando sinal paralinguístico. Use checkpoints **base SSL** (não ASR-tuned) para `voice_analyzer`/`variety_analyzer`.

### HuBERT vs WavLM vs wav2vec2 — escolha por feature

| Feature/Dim | Modelo recomendado | Layer range | Notas |
|---|---|---|---|
| Pitch (F0, intonation contour) | **HuBERT-base** | 3–7 | Reforçar com Praat F0 como sanity check |
| Intensity / energy dynamics | **HuBERT-base** ou **WavLM-base** | 2–6 | Camadas baixas |
| Rhythm / pacing | **HuBERT-base** | 6–10 | Combinar com Whisper word timestamps |
| Voice quality (breathiness, resonance) | **WavLM-base+** | 4–10 | WavLM treinou com mais dados de speaker → melhor [MED] |
| Emoção/affect | **WavLM-large** | 10–18 (weighted-sum) | Best em IEMOCAP-like benchmarks [HIGH] |
| Speaker identity (NÃO desejado em paralinguístico) | — | evitar 12+ em large | Suprimir camadas tardias se quiser conteúdo, ou tardias se quiser speaker |

**Compatibility:** todos drop-in via HuggingFace `transformers` (`Wav2Vec2Model.from_pretrained` / `HubertModel.from_pretrained` / `WavLMModel.from_pretrained`). API idêntica — output `hidden_states` é tupla de tensores (uma por layer).

**Latência (ordem de grandeza, sem hardware específico):**
- base (12 layers, ~95M params): ~1× real-time em CPU moderna, ~5–10× em GPU consumer.
- large (24 layers, ~316M params): ~0.3× CPU, ~3–5× GPU.
- WavLM-large > HuBERT-large > wav2vec2-large em tasks paralinguísticas (margem pequena, 1–3pp).

[MED — números aproximados, validar empiricamente nos vídeos de teste]

### Disentanglement prosódia↔conteúdo (arXiv:2502.19387)

Não foi possível deep-read nesta wave (sem fetch direto). Sinal do report base: técnica residual subtrai componente linguístico, isolando paralinguístico. Vale follow-up `05-*` se Foco 2 entrar em sprint.

---

## Curiosity Queue — atualizações

**Resolvidas nesta wave:**
- ✅ "MediaPipe FaceLandmarker blendshapes mapeiam bem pra AUs FACS canônicos?" → **NÃO 1:1**, "loosely correspond". Bridge aproximado existe (`py-feat/mp_blendshapes`) mas validação empírica obrigatória.

**Reforçadas (mais evidência, mantidas abertas):**
- "AVI Challenge 2025 baseline absoluto" — segue HIGH priority, não foi alvo desta wave.

**Novas abertas:**
- "OpenFace 3.0 lista exata de AUs detectadas e cobertura FACS vs py-feat" — HIGH, requer leitura local do PDF.
- "OpenFace 3.0 license formal (commercial vs research)" — MED, ler LICENSE no repo.
- "Existe checkpoint HuBERT/WavLM PT-BR ou multilingual base (não ASR-tuned)?" — MED, important pra ground truth Gui em PT-BR.
- "Layer-wise weighted sum aprendido converge em quais layers para dims do projeto?" — MED, descobrível experimentalmente nos 7 vídeos.

---

## Caveats

- 1 wave, 5 fontes consultadas. Paper PDF arXiv:2506.02891 não rendeu corpo via WebFetch (binary PDF saved mas inacessível pra extração); benchmarks numéricos exatos requerem leitura local.
- ScienceDirect retornou 403 (paywall) — citação layer-wise emotion vem de aggregation search + ResearchGate fig.
- Latências citadas são ordem de grandeza, não medidas no hardware de produção.

---

## Recomendações ajustadas (override do `03-recommendations.md` quando aplicável)

### Acionável #1 (HuBERT/WavLM) — confirmado e refinado

- **Modelo padrão:** começar com **WavLM-base+** (`microsoft/wavlm-base-plus`) — melhor margem em paralinguística, pesos público, drop-in HF.
- **Estratégia:** weighted-sum learnable sobre 12 layers como feature extractor congelado. Loss aprende os pesos.
- **NÃO usar checkpoints ASR-fine-tuned** (ex: `facebook/wav2vec2-large-960h`) — perdem prosódia.
- **A/B obrigatório** contra wav2vec2 atual (se ainda tem cache local) nos 7 vídeos de teste antes de cutover.
- Esforço revisado: 1-2 dias mantido.

### Acionável #2 (OpenFace 3.0) — confirmado, mas com 2 gates

- **Gate 1:** ler localmente seção 4 (AU coverage) do PDF arXiv:2506.02891 antes de comprometer migração.
- **Gate 2:** verificar LICENSE no repo (ou abrir issue) — se restritiva pra comercial, fica fallback OpenFace 2.x via Docker.
- **Bridge curto destravado:** se Py3.12 é blocker urgente, MediaPipe blendshapes via `py-feat/mp_blendshapes` ou mapping próprio resolve em horas (com perda de canonicidade FACS).
- Esforço revisado: 3-5 dias (era 2-4) por causa dos gates.

---

## Sources

- [OpenFace 3.0 paper (arXiv:2506.02891)](https://arxiv.org/abs/2506.02891)
- [OpenFace 3.0 GitHub (CMU-MultiComp-Lab)](https://github.com/CMU-MultiComp-Lab/OpenFace-3.0)
- [Wang et al. — Fine-tuned wav2vec2/HuBERT Benchmark (arXiv:2111.02735)](https://arxiv.org/abs/2111.02735)
- [Layer-wise benchmarking wav2vec2 Large / HuBERT Large / Data2vec (ResearchGate fig)](https://www.researchgate.net/figure/Layer-wise-benchmarking-of-wav2vec-20-Large-HuBERT-Large-and-Data2vec-Large-on-5-tasks_fig3_379882278)
- [Large-Scale Evaluation of Speech Foundation Models (arXiv:2404.09385)](https://arxiv.org/pdf/2404.09385)
- [WavLM original (Microsoft)](https://audiocc.sjtu.edu.cn/user/pages/05.members/zhengyang.chen/publications/WavLM@@Large-Scale@Self-Supervised@Pre-Training@for@Full@Stack@Speech@Processing/paper.pdf)
- [Unveiling embedded features in Wav2vec2 and HuBERT (Procedia Computer Science)](https://www.sciencedirect.com/science/article/pii/S1877050924002515) (paywall, accessed via aggregation)
- [MediaPipe FaceLandmarker blendshapes guide (Google AI)](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker)
- [py-feat/mp_blendshapes (HuggingFace)](https://huggingface.co/py-feat/mp_blendshapes)
- [Speaker Emotion Recognition with wav2vec2/HuBERT (arXiv:2411.02964)](https://arxiv.org/html/2411.02964v1)
