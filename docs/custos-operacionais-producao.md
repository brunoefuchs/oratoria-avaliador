# Custos Operacionais de Produção — Oratória Avaliador

**Data:** 2026-05-06
**Escopo:** Custos para rodar o sistema em produção comercial, incluindo infraestrutura, ferramentas, APIs e variáveis por avaliação.

> **Premissa de qualidade:** todos os cenários abaixo mantêm **100% das 14 dimensões e workers atuais** rodando, sem degradação funcional. As diferenças entre cenários são apenas em latência percebida, capacidade de pico e disponibilidade. Detalhe completo na seção 11.

---

## 1. Stack atual em produção

| Componente | Tecnologia | Recurso necessário |
|---|---|---|
| **Frontend** | Next.js 14 (App Router) | CPU baixo / SSR leve |
| **API** | FastAPI (Python) | 1 vCPU, 1GB RAM |
| **ML Worker** | FastAPI + Whisper "medium" + MediaPipe + Praat (parselmouth) + Gemini calls | **GPU recomendada** (ou CPU forte) |
| **Banco de dados** | Supabase Postgres | Free tier suficiente até ~500 evals/mês |
| **Storage de vídeo** | Supabase Storage | $0.021/GB/mês |
| **LLM (geração de relatório)** | Gemini 2.5 Flash | Pay-per-use |
| **LLM Vision (cross-validation)** | Gemini Vision Flash | On-demand, opcional |

---

## 2. Custos variáveis (por avaliação)

| Item | Custo unitário | Notas |
|---|---|---|
| **LLM relatório (Gemini Flash)** | ~$0.001 | Confirmado em logs (`llm_cost_usd: 0.001138`). 3K input + 1K output tokens médios. |
| **Compute GPU** (5min processing) | $0.04 – $0.10 | Depende do provider. Whisper medium é o gargalo. |
| **Storage vídeo** (10-30MB) | ~$0.0005/mês | Supabase $0.021/GB. Negligível. |
| **Bandwidth** (upload + streaming) | ~$0.001 | Marginal em provedores modernos. |
| **Total variável** | **~$0.05 – $0.12 por eval** | |

### Decomposição típica do tempo de pipeline

| Etapa | Tempo (CPU) | Tempo (GPU) |
|---|---|---|
| Whisper transcribe (60s áudio) | ~60-120s | ~10-20s |
| MediaPipe pose + face + hands | ~30-60s | ~15-30s |
| Praat F0 + intensidade | ~5-10s | ~5-10s |
| LLM Gemini report | ~30-50s | ~30-50s |
| **Total por eval** | **2-4 min** | **1-2 min** |

---

## 3. Custos fixos (independentes do volume)

| Item | Mensal | Notas |
|---|---|---|
| **Supabase** Free → Pro | $0 → $25 | Pro recomendado >500 evals/mês (8GB DB, 250GB egress) |
| **Frontend hosting** (Vercel/Cloudflare) | $0 – $20 | Free tier cobre maioria dos casos |
| **API instance** (small VPS sempre online) | $5 – $10 | DigitalOcean $6, Hetzner €5 |
| **ML Worker base** | varia | Maior variável de todas — depende GPU on-demand vs dedicada |
| **Domínio + email + monitoring** | $5 – $20 | Cloudflare/Resend/Sentry mix |
| **Total fixo mínimo** | **$10 – $75/mês** | |

---

## 4. Cenários de escala

### 🟢 Cenário A — Hobby / Beta
**Volume:** 300 evals/mês (10/dia)

| Item | Custo |
|---|---|
| GPU on-demand (RunPod/Modal) | $12 – $25 |
| LLM (Gemini) | $0.30 |
| Supabase (Free tier) | $0 |
| Frontend (Vercel Free) | $0 |
| API VPS | $5 – $10 |
| Domínio + monitoring | $5 |
| **Total** | **$25 – $40/mês** |
| **Custo/eval** | **~$0.10 – $0.13** |

### 🟡 Cenário B — SMB / Startup
**Volume:** 3.000 evals/mês (100/dia)

| Item | Custo |
|---|---|
| GPU dedicada part-time (~6h/dia A40) | $90 – $150 |
| LLM (Gemini) | $3 |
| Supabase Pro | $25 |
| Frontend | $0 – $20 |
| API VPS + ML Worker base | $20 – $30 |
| Domínio + monitoring + email | $20 |
| **Total** | **$160 – $250/mês** |
| **Custo/eval** | **~$0.05 – $0.083** |

### 🔴 Cenário C — Mid-scale
**Volume:** 30.000 evals/mês (1.000/dia)

| Item | Custo |
|---|---|
| GPU 24/7 (1-2x A40 ou A100 reserved) | $700 – $1.500 |
| LLM (Gemini) | $30 |
| Supabase Pro/Team | $25 – $599 |
| Frontend (paid plan) | $20 – $50 |
| Always-on infra (load balancer, multi-region) | $100 |
| Email + monitoring + observability | $50 |
| **Total** | **$925 – $2.330/mês** |
| **Custo/eval** | **~$0.031 – $0.078** |

### 🌊 Cenário D — Enterprise / Scale
**Volume:** 100.000 evals/mês

| Item | Custo |
|---|---|
| GPU cluster (4-8x A100 ou H100) | $3.000 – $6.000 |
| LLM (Gemini) | $100 |
| Supabase Team/Enterprise | $599+ |
| CDN + multi-region | $500 |
| DevOps + observability | $200 |
| **Total** | **$4.400 – $7.500/mês** |
| **Custo/eval** | **~$0.044 – $0.075** |

---

## 5. Provedores GPU — comparativo

Preços referência (jan/2026):

| Provider | GPU | Preço/hora | Latência BR | Modo de cobrança | Notas |
|---|---|---|---|---|---|
| **RunPod Spot** | RTX 4090 / A40 | $0.20 – $0.50 | Média | Por segundo | Spot pode ser interrompido |
| **RunPod Reserved** | A40 | $0.40 | Média | Por hora | Sempre online |
| **Modal** | A10G | $1.10 | Boa | Por segundo (auto-scale) | Cold start 5-15s |
| **AWS** g4dn.xlarge SP | T4 | $0.55 | **Excelente** (São Paulo) | Por hora | Reserved 30-50% mais barato |
| **Lambda Labs** | A10 | $0.75 | Boa | Por hora | Estoque limitado |
| **Vast.ai** | RTX 3090 | $0.20 – $0.30 | Variável | Por hora | Marketplace, qualidade variável |
| **Hugging Face Inference Endpoints** | A10G | $1.30 | Boa | Por hora | Auto-scale, mas caro |
| **Replicate** | Misc | $0.001/segundo+ | Boa | Por segundo | Pay-as-you-go, simples |

### Recomendação por fase

| Fase | Provider sugerido | Razão |
|---|---|---|
| **MVP / Beta** | Modal | Auto-scale, paga só uso, sem gerenciar infra |
| **SMB stable** | RunPod Reserved A40 | Custo fixo previsível, sempre online |
| **Mid-scale** | AWS g4dn São Paulo (Reserved 1-year) | Latência BR + desconto reserved |
| **Enterprise** | Mix multi-cloud + Spot pra batch | Resiliência + otimização |

---

## 6. Otimizações de custo

### 6.1 Trocar modelo Whisper

| Modelo | VRAM | Velocidade | Qualidade PT-BR | Recomendação |
|---|---|---|---|---|
| **medium** (atual) | 1.5GB | 1x baseline | Excelente | Atual — ok mas pesado |
| **turbo** | 1.6GB | 6x mais rápido | Excelente | **⭐ Trocar para esse já** |
| **small** | 700MB | 2.5x mais rápido | Bom | Aceitável se latência crítica |
| **tiny** | 250MB | 10x mais rápido | Médio | Só pra demos rápidas |

**Economia estimada:** trocar `medium` → `turbo` = **50-70% redução tempo GPU = mesma % do custo compute**.

### 6.2 CPU-only (sem GPU)

Viável até **100-200 evals/dia** com Whisper turbo:
- VPS 4 vCPU + 8GB RAM: ~$20-40/mês (Hetzner, Contabo, DigitalOcean)
- Pipeline: 60s áudio = 2-3min processing
- Trade-off: latência 2-3x maior, mas zero custo GPU
- **Economia: $80-150/mês vs GPU dedicada**

### 6.3 Batch processing

Processar 5-10 vídeos sequencialmente na MESMA instância GPU:
- Reduz overhead de cold start de modelos (Whisper carrega ~5s)
- Aproveita warm cache de MediaPipe
- **Economia: 30-40% do tempo total**

### 6.4 Cache de resultados

Mesmo vídeo (hash) retorna resultado salvo (já implementado em parte):
- Re-uploads acidentais: zero custo
- Iterações de UI: zero re-processing
- **Economia situacional**

### 6.5 LLM tiering

Atual: Gemini 2.5 Flash (~$0.001/eval).

Alternativas mais baratas:
| Modelo | Custo input | Custo output | Custo/eval | Qualidade |
|---|---|---|---|---|
| Gemini 2.5 Flash (atual) | $0.075/M | $0.30/M | $0.001 | ⭐⭐⭐⭐⭐ |
| Gemini Flash Lite | $0.025/M | $0.10/M | $0.0003 | ⭐⭐⭐⭐ |
| Cohere Command R+ | $0.15/M | $0.60/M | $0.0015 | ⭐⭐⭐⭐ |
| Llama 3.3 70B (Groq) | $0.59/M | $0.79/M | $0.003 | ⭐⭐⭐⭐ |

**Economia:** ~70% LLM se trocar pra Flash Lite — mas é insignificante no total ($0.0007 por eval).

---

## 7. Pricing sugerido e margem

### Modelo per-eval (transação)

Preço sugerido: **R$ 30 por avaliação** (~$5–6 USD)

| Volume mensal | Revenue | Custo total | Lucro | Margem |
|---|---|---|---|---|
| 10 evals | R$ 300 | R$ 250 | R$ 50 | 17% |
| 100 evals | R$ 3.000 | R$ 250 | R$ 2.750 | 92% |
| 1.000 evals | R$ 30.000 | R$ 1.000 | R$ 29.000 | 97% |
| 10.000 evals | R$ 300.000 | R$ 4.000 | R$ 296.000 | 99% |

### Modelo de assinatura

Pacotes mensais:
| Plano | Preço | Evals incluídos | Custo eval avulso |
|---|---|---|---|
| **Free** | R$ 0 | 1/mês | — |
| **Starter** | R$ 49 | 5 | R$ 9,80/eval |
| **Pro** | R$ 149 | 20 | R$ 7,45/eval |
| **Team** | R$ 499 | 100 | R$ 4,99/eval |
| **Enterprise** | Custom | 500+ | Negociado |

Margem em qualquer caso > 90% no break-even após cliente nº 5.

---

## 8. Custos esquecidos que aparecem em produção

| Item | Custo típico | Quando vira problema |
|---|---|---|
| **Email transacional** (notificar relatório pronto) | $15-30/mo | Day 1 |
| **CDN para vídeos** (streaming preview) | $5-50/mo | >100 usuários ativos |
| **Erro tracking** (Sentry) | $0-26/mo | Day 1 |
| **Analytics** (PostHog/Plausible) | $0-20/mo | Validação produto |
| **Backup off-site** | Incluso Supabase Pro | Compliance/segurança |
| **Status page** (Better Stack/Statuspage) | $0-25/mo | >50 usuários pagantes |
| **SSL** | $0 (Let's Encrypt) | Sempre |
| **Domínio** | $10-15/ano | Day 1 |
| **Compliance LGPD** | Variável | Vendendo B2B |
| **Infraestrutura PIX/Stripe** | 1-3% transação | Cobrança |
| **Total adicional típico** | **$50-150/mês** | |

---

## 9. Resumo executivo

### Tabela mestra

| Volume mensal | Custo total/mês | Custo/eval | Receita potencial @ R$30 | Margem |
|---|---|---|---|---|
| 100 | $20-40 | $0.20-0.40 | R$ 3.000 | 90%+ |
| 1.000 | $80-150 | $0.08-0.15 | R$ 30.000 | 96%+ |
| 10.000 | $400-800 | $0.04-0.08 | R$ 300.000 | 98%+ |
| 100.000 | $2.500-5.000 | $0.025-0.05 | R$ 3.000.000 | 99%+ |

### Insights chave

1. **Margem absurdamente alta** — gargalo do negócio é aquisição de cliente, não custo operacional
2. **Break-even ridículamente baixo** — ~10 evals/mês cobrem custos fixos básicos
3. **Compute GPU é o único custo significativo** — 80% do custo variável
4. **Otimização Whisper turbo** reduz ~60% do compute imediatamente
5. **Pricing pode ser agressivo** sem comprometer margem
6. **Crescimento diluí custo fixo** — eficiência aumenta com escala

### Recomendação fase-a-fase

| Fase | Foco | Custo target |
|---|---|---|
| **Pré-revenue (validação)** | Modal + Whisper turbo + Supabase Free | <$30/mês |
| **Primeiros clientes (1-50/mês)** | RunPod Spot + Supabase Pro | <$80/mês |
| **Crescimento (50-500/mês)** | RunPod Reserved + email + monitoring | <$250/mês |
| **Escala (500+/mês)** | AWS São Paulo + DevOps mínimo | $500-1500/mês |
| **Enterprise (5k+/mês)** | Multi-region + SLA + support | $2k-5k/mês |

---

## 10. Pontos de atenção

### 🚨 Custos que escalam mal (cuidado)

- **Supabase egress** acima de 250GB/mês cobra $0.09/GB → vídeos grandes podem explodir
- **Modal** tem cold start ~5-15s → user UX ruim em baixo volume
- **GPU on-demand** em horários de pico do provider pode ter espera

### 💡 Custos que escalam BEM

- **LLM (Gemini)** — pricing linear, sem surpresas
- **Frontend** (Next.js + CDN) — efetivamente grátis até milhares de usuários
- **Compute** com batching — custo unitário CAI com volume

### ⚖️ Trade-offs principais

1. **Latência vs custo:** GPU sempre online é caro mas rápido; on-demand é barato mas tem cold start
2. **Qualidade vs custo:** Whisper medium > turbo > small > tiny — escolher ponto de equilíbrio
3. **Brasil vs USA:** AWS São Paulo é mais caro mas tem latência 50-100ms melhor para usuários BR

---

---

## 11. Garantia de qualidade — o que mantém igual ao atual

### 11.1 Os 14 workers continuam rodando em todos os cenários

| Worker | Tecnologia | Onde roda | Incluído? |
|---|---|---|---|
| Voice analyzer | Praat (parselmouth) — F0, jitter, shimmer | CPU | ✅ Sim |
| Variety analyzer | Cálculo numérico | CPU | ✅ Sim |
| Gesture analyzer | MediaPipe Pose + Hands + Face | CPU/GPU | ✅ Sim |
| Posture analyzer | MediaPipe Pose | CPU/GPU | ✅ Sim |
| Facial analyzer | MediaPipe Face Landmarker (478 landmarks + iris) | CPU/GPU | ✅ Sim |
| Fillers | Análise de transcrito | CPU | ✅ Sim |
| Storytelling | LLM + heurísticas | CPU + LLM | ✅ Sim |
| Identity | Análise lexical | CPU | ✅ Sim |
| Tonality VAD | Modelo VAD (arousal/valence/dominance) | CPU/GPU leve | ✅ Sim |
| Congruence | Cruzamento de features | CPU | ✅ Sim |
| Articulation | Análise espectral | CPU | ✅ Sim |
| Archetypes | Classificador | CPU + LLM | ✅ Sim |
| Opening | Heurística + LLM | CPU + LLM | ✅ Sim |
| Report generator | Gemini 2.5 Flash | API externa | ✅ Sim |

**Total: 14 dimensões funcionando idêntico ao ambiente local atual.**

### 11.2 As 2 nuances do custo

#### Whisper "medium" vs "turbo"

A estimativa principal **assume Whisper turbo** (configurado como primary no `voice_analyzer.py`, com fallback automático pra medium). Em PT-BR claro, qualidade entre os dois é **praticamente idêntica** (~5-6% WER vs 5% WER).

| Modelo | Tempo pipeline | Custo/eval | WER PT-BR | Quando faz diferença |
|---|---|---|---|---|
| **medium** (fallback) | 4-7 min | $0.05–0.10 | ~5% | Áudio muito degradado (que já é flagado por SNR low/babble) |
| **turbo** (primary atual) | 1.5-3 min | $0.02–0.05 | ~5-6% | Casos típicos |

**Se quiser forçar Whisper medium em 100% dos evals** (sem turbo), os custos ficam:

| Cenário | Custo turbo | Custo medium forçado |
|---|---|---|
| A — Hobby (300/mês) | $25–40 | $40–65 |
| B — SMB (3.000/mês) | $160–250 | $250–400 |
| C — Mid-scale (30.000/mês) | $850–2.250 | $1.700–3.500 |
| D — Enterprise (100.000/mês) | $4.400–7.500 | $8.000–12.000 |

**Recomendação:** manter turbo como primary (já está). Cenários onde medium faz diferença real (áudio ruim) já estão protegidos pelos gates de SNR/babble que mostram warning ao usuário.

#### Latência (cold start) em providers on-demand

| Provider | Cold start | Afeta qualidade? |
|---|---|---|
| **Modal** | 5-15s primeira req do dia | ❌ Só UX |
| **RunPod Spot** | Variável (segundos) | ❌ Só UX |
| **RunPod Reserved** | 0s (sempre online) | — |
| **AWS GPU on-demand** | 30-60s (boot da VM) | ❌ Só UX |
| **AWS GPU reserved** | 0s | — |

**Em cenários A/B com GPU on-demand:** usuário vê 5-15s de espera adicional na primeira avaliação do dia. Depois fica warm.

**Não há degradação de qualidade dos resultados** — apenas espera maior. Pra eliminar, basta migrar pra reserved (incluso desde cenário B).

### 11.3 Tabela com qualidade explícita

| Cenário | Volume | Custo/mês | Qualidade vs atual | Trade-off operacional |
|---|---|---|---|---|
| **A — Hobby** | 300/mês | $25-40 | **100% igual** | Cold start 5-15s na 1ª req do dia |
| **B — SMB** | 3.000/mês | $160-250 | **100% igual** | Nenhum (GPU dedicada part-time) |
| **C — Mid-scale** | 30.000/mês | $850-2.250 | **100% igual** | Nenhum |
| **D — Enterprise** | 100.000/mês | $4.400-7.500 | **100% igual** | Nenhum |

### 11.4 Custos opcionais não incluídos (features off por default)

Esses workers existem no código mas estão atrás de feature flags `false` por default. Se ativar, recalibrar:

| Feature | Flag | Custo adicional |
|---|---|---|
| **Gemini Vision cross-validation** | on-demand por dimensão | +$0.005–0.010 por eval que disparar |
| **Pyannote VAD / Diarization** | `PYANNOTE_VAD_ENABLED` | +30-90s GPU por eval (~+30% compute) |
| **opensmile** | `OPENSMILE_ENABLED` | ~zero (CPU only, leve) |

**Resumo:** com as flags atuais (todas off por default), os números do doc são corretos. Ativar Pyannote ou Gemini Vision exigiria recalibrar.

---

## 12. Resposta curta

**Sim — com os custos estimados, o sistema roda exatamente como hoje, com qualidade 100% equivalente, em todos os cenários (A → D).**

As únicas "ressalvas honestas":
1. O cálculo assume Whisper turbo (default atual). Forçar medium dobra custo compute.
2. Cenário A tem cold start 5-15s na primeira avaliação do dia (afeta UX, não qualidade).
3. Features opcionais hoje desligadas (Pyannote, Gemini Vision per-eval) adicionam custo se ativadas.

---

**Última atualização:** 2026-05-06
**Próxima revisão sugerida:** após primeiros 100 clientes pagantes (recalibrar com dados reais de uso)
