# Brainstorm: IA Avaliadora de Oratoria em Video

**Data:** 2026-03-30
**Facilitador:** @analyst (Atlas)
**Participante:** Bruno
**Status:** Draft

---

## Objetivo

Investigar como uma IA pode avaliar o desempenho de oratoria de uma pessoa em video, cobrindo 4 dimensoes: postura, gestual, tom de voz e vicios de linguagem.

---

## Streams de Dados

O video fornece 2 streams complementares:

| Stream | Dados | Dimensoes Avaliadas |
|--------|-------|---------------------|
| **Visual** (frames) | Corpo, rosto, maos, posicao | Postura, Gestual |
| **Audio** (waveform) | Voz, palavras, pausas, ritmo | Tom de Voz, Vicios de Linguagem |

---

## Dimensao 1: POSTURA — Analise Visual

### O que avaliar

- Alinhamento da coluna (ereta vs curvada)
- Distribuicao de peso (equilibrado vs pendendo para um lado)
- Abertura do peito (confiante vs fechada/defensiva)
- Posicao da cabeca (erguida vs baixa)
- Estabilidade (firme vs balancando/inquieto)

### Abordagens tecnicas

| # | Abordagem | Como funciona | Pros | Contras |
|---|-----------|---------------|------|---------|
| 1 | **Pose Estimation (MediaPipe/OpenPose)** | Extrai 33 keypoints do corpo frame a frame, calcula angulos entre articulacoes | Open source, roda local, tempo real | Precisa calibrar thresholds de "boa postura" |
| 2 | **Vision LLM (GPT-4o / Claude Vision)** | Envia frames selecionados para modelo multimodal avaliar postura qualitativamente | Avaliacao contextual rica, sem treinar modelo | Custo por frame, latencia, nao e tempo real |
| 3 | **Modelo customizado (fine-tuned CNN)** | Treina classificador proprio em dataset de oratoria anotado | Alta precisao para o dominio | Precisa de dataset anotado (caro de criar) |

### Metricas derivaveis

- Score de alinhamento postural (0-100)
- % do tempo em postura aberta vs fechada
- Variacao postural ao longo do tempo (estabilidade)

---

## Dimensao 2: GESTUAL — Analise de Gestos

### O que avaliar

- Frequencia de gestos (excesso vs ausencia)
- Amplitude (gestos amplos vs contidos)
- Coerencia gesto-fala (gesto reforca a mensagem?)
- Gestos repetitivos/tiques (tocar cabelo, cruzar bracos)
- Zona de gesticulacao (acima da cintura = positivo em oratoria)
- Contato visual (olha para camera/plateia vs desvia)

### Abordagens tecnicas

| # | Abordagem | Como funciona |
|---|-----------|---------------|
| 1 | **Hand Tracking (MediaPipe Hands)** | 21 keypoints por mao, rastreia trajetoria e velocidade |
| 2 | **Action Recognition (temporal)** | Modelos como SlowFast ou VideoMAE classificam acoes em segmentos de video |
| 3 | **Heatmap de movimento** | Optical flow para mapear regioes de maior atividade gestual |
| 4 | **Face Mesh + Gaze Estimation** | 468 pontos faciais para expressoes + direcao do olhar |

### Metricas derivaveis

- Taxa de gestos por minuto
- Mapa de calor de movimentacao
- Score de expressividade facial
- % de contato visual com camera

---

## Dimensao 3: TOM DE VOZ — Analise Prosodica

### O que avaliar

- Variacao de pitch (monotonico vs expressivo)
- Volume / energia vocal (projecao)
- Velocidade de fala (palavras por minuto)
- Pausas estrategicas vs pausas de hesitacao
- Clareza da diccao
- Emocao transmitida na voz

### Abordagens tecnicas

| # | Abordagem | Como funciona |
|---|-----------|---------------|
| 1 | **Analise prosodica (Praat/Parselmouth)** | Extrai F0 (pitch), intensidade, formantes, duracao de silencios |
| 2 | **Speech-to-Text + analise temporal** | Whisper (OpenAI) com timestamps por palavra — calcula WPM, pausas |
| 3 | **Emotion Recognition (audio)** | Modelos como SER (Speech Emotion Recognition) classificam emocao por segmento |
| 4 | **Audio LLM (Gemini 2.5)** | Envia audio para modelo multimodal que analisa prosodia diretamente |

### Metricas derivaveis

- WPM (palavras por minuto) — ideal oratoria: 130-170 WPM
- Variacao de pitch em semitones (monotonia score)
- Razao fala/silencio
- Score de projecao vocal (dB medio)
- Mapa emocional ao longo do tempo

---

## Dimensao 4: VICIOS DE LINGUAGEM — Analise Linguistica

### O que avaliar

- Palavras de preenchimento ("ne", "tipo", "entao", "eeee", "hum")
- Repeticoes desnecessarias
- Uso excessivo de gerundio
- Frases incompletas / truncadas
- Vocabulario limitado (repeticao de palavras)
- Concordancia verbal/nominal

### Abordagens tecnicas

| # | Abordagem | Como funciona |
|---|-----------|---------------|
| 1 | **STT + Regex/NLP** | Whisper transcreve → conta ocorrencias de fillers com regex + spaCy |
| 2 | **LLM como avaliador linguistico** | Envia transcricao para Claude/GPT analisar qualidade do discurso |
| 3 | **Filler detection model** | Modelo especifico treinado para detectar fillers no audio (antes da transcricao) |
| 4 | **Analise de disfluencia** | Detecta hesitacoes, falsos inicios, autocorrecoes no audio bruto |

### Metricas derivaveis

- Fillers por minuto (meta: < 3/min)
- Diversidade lexical (type-token ratio)
- Score de clareza da mensagem
- Lista dos vicios mais frequentes com timestamps

---

## Arquitetura — Opcoes

| # | Arquitetura | Descricao | Ideal para |
|---|-------------|-----------|------------|
| 1 | **Pipeline modular** | Cada dimensao e um modulo independente (MediaPipe + Whisper + Parselmouth + LLM) → scores agregados no final | Controle fino, custo previsivel, explicabilidade |
| 2 | **Multimodal LLM end-to-end** | Envia video inteiro para Gemini 2.5 Pro com prompt estruturado pedindo avaliacao nas 4 dimensoes | Simples de implementar, mas caro e menos controlavel |
| 3 | **Hibrido (RECOMENDADO)** | Extrai features com ferramentas especializadas → alimenta LLM com dados estruturados para gerar avaliacao qualitativa | Melhor custo-beneficio, combina precisao numerica com feedback humano |

### Arquitetura Hibrida — Fluxo

```
Video → Split audio/video
         |
         ├── Video → MediaPipe (pose + hands + face) → metricas visuais
         |
         └── Audio → Whisper (transcricao + timestamps)
                   → Parselmouth (prosodia)
                   → Contagem de fillers
                   |
                   v
         Todas as metricas → LLM (Claude/GPT) → Relatorio qualitativo
                                                  com scores e feedback acionavel
```

---

## Proximos passos

| # | Opcao | Status |
|---|-------|--------|
| 1 | Aprofundar numa dimensao especifica | Pendente |
| 2 | Detalhar arquitetura tecnica (stack, APIs, custos) | Pendente |
| 3 | Pesquisar ferramentas e APIs existentes (estado da arte) | Pendente |
| 4 | Definir MVP minimo viavel | Pendente |
| 5 | Criar Project Brief formal | Pendente |

---

*Documento gerado por @analyst (Atlas) — Brainstorming Session*
