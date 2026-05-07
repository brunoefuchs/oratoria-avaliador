# 05 — Spec: Bridge MediaPipe Blendshapes → AUs (Rota 2)

**Status:** Research spec. Não é implementação — @dev/@pm executam.
**Data:** 2026-05-06
**Origem:** Decisão pós-04, após bloqueio comercial OpenFace 3.0 (license CMU non-commercial only — ver `curiosity_queue.yaml`).

---

## 1. Contexto

### Problema
- `py-feat 0.6.2` bloqueia Python 3.12 (memória de projeto).
- OpenFace 3.0 tecnicamente viável mas **proibido comercialmente** (CMU license).
- Necessidade: substituto para detecção de Action Units (AUs) FACS comercialmente livre.

### Hipótese
MediaPipe FaceLandmarker já está integrado (`facial_analyzer.py` usa Face Mesh refined com 478 landmarks). O modelo MediaPipe Tasks expõe **52 blendshape coefficients ARKit-style** que podem ser mapeados aproximadamente a AUs FACS canônicas.

### Caveat científico [HIGH confiança da literatura]
Blendshapes ARKit ≠ AUs FACS. Correspondência é "loose" (não 1:1). Validação empírica contra ground truth é obrigatória antes de promover.

### Licença
- **MediaPipe:** Apache 2.0 — uso comercial OK.
- **ARKit blendshape spec:** público.

---

## 2. Mapping Table — Blendshapes → AUs

Mapping baseado em literatura (Ekman FACS, Apple ARKit docs, py-feat/blendshape mapping community).

| Blendshape(s) MediaPipe | AU FACS | Nome AU | Confiança mapping |
|---|---|---|---|
| `browDownLeft` + `browDownRight` | **AU4** | Brow Lowerer | Alta |
| `browInnerUp` | **AU1** | Inner Brow Raiser | Alta |
| `browOuterUpLeft` + `browOuterUpRight` | **AU2** | Outer Brow Raiser | Alta |
| `cheekSquintLeft` + `cheekSquintRight` | **AU6** | Cheek Raiser | Alta |
| `cheekPuff` | **AU34** | Cheek Puff | Média (raro em oratória) |
| `eyeBlinkLeft` + `eyeBlinkRight` | **AU45** | Blink | Alta |
| `eyeWideLeft` + `eyeWideRight` | **AU5** | Upper Lid Raiser | Alta |
| `eyeSquintLeft` + `eyeSquintRight` | **AU7** | Lid Tightener | Alta |
| `noseSneerLeft` + `noseSneerRight` | **AU9** | Nose Wrinkler | Alta |
| `mouthUpperUpLeft` + `mouthUpperUpRight` | **AU10** | Upper Lip Raiser | Alta |
| `mouthSmileLeft` + `mouthSmileRight` | **AU12** | Lip Corner Puller (smile) | Alta |
| `mouthDimpleLeft` + `mouthDimpleRight` | **AU14** | Dimpler | Média |
| `mouthFrownLeft` + `mouthFrownRight` | **AU15** | Lip Corner Depressor | Alta |
| `mouthShrugUpper` + `mouthShrugLower` | **AU17** | Chin Raiser | Média |
| `mouthPucker` | **AU18** | Lip Puckerer | Alta |
| `mouthStretchLeft` + `mouthStretchRight` | **AU20** | Lip Stretcher | Alta |
| `mouthFunnel` | **AU22** | Lip Funneler | Média |
| `mouthPressLeft` + `mouthPressRight` + `mouthClose` | **AU24** | Lip Pressor | Média |
| `mouthRollLower` + `mouthRollUpper` | **AU28** | Lip Suck | Média |
| `jawOpen` | **AU26** / **AU27** | Jaw Drop / Mouth Stretch | Alta (threshold define qual) |
| `jawForward` | **AU29** | Jaw Thrust | Baixa (raro relevante) |
| `jawLeft` / `jawRight` | **AU30** | Jaw Sideways | Baixa |
| `tongueOut` | **AU19** | Tongue Show | Alta (raro em oratória) |

### Cobertura
- **AUs cobertas:** ~22 (das ~30+ AUs FACS canônicas detectáveis).
- **AUs não cobertas:** AU8 (Lips Toward), AU11, AU13 (Sharp Lip Puller), AU16 isolado, AU21, AU23, AU25 isolado, AU38, AU39 (head movement), AU41-46 outros eye AUs.
- **AUs irrelevantes para oratória:** AU19 (tongue), AU33 (cheek blow), AU34 (cheek puff) podem ser deprioritizadas.

### Cobertura efetiva pra oratória
Subset crítico que importa pro projeto (cruza com framework Vinh + congruence_analyzer):

| AU | Função no produto | Coberto via blendshape? |
|---|---|---|
| AU1+AU2 (sobrancelhas levantadas) | Surpresa, ênfase | ✅ |
| AU4 (sobrancelha baixada) | Concentração, raiva | ✅ |
| AU6+AU12 (Duchenne smile genuíno) | Empatia, alegria autêntica | ✅ |
| AU12 (smile mecânico) | Sorriso social | ✅ |
| AU15 (corner depressor) | Tristeza, desagrado | ✅ |
| AU5 (upper lid raise) | Surpresa, medo, alerta | ✅ |
| AU7 (lid tightener) | Foco, raiva | ✅ |
| AU9+AU10 (nose+upper lip) | Nojo | ✅ |
| AU45 (blink rate) | Estresse cognitivo | ✅ |
| AU26/27 (jaw drop) | Surpresa, ênfase | ✅ |

**Conclusão cobertura:** ≥10 AUs críticas cobertas. Suficiente pra rodar `facial_analyzer` + `congruence_analyzer` em paridade funcional com py-feat.

---

## 3. Protocolo de validação (gate de promoção)

### Setup
- 7 vídeos de teste já batizados (GUI ITAJAI/PRIME/WENDEL/ARARANGUA, ALUNA LOIRA/MORENA, ALUNO MONO).
- Ground truth: rodar **py-feat 0.6.2** (Py3.11 isolado) nos mesmos vídeos como referência. NÃO usar Gui aqui — Gui é ground truth de score, não de AU.
- Output: por frame, intensidade AU 0-5 (ou 0-1 normalizado).

### Métricas
1. **Pearson por AU** entre py-feat e bridge (frame-by-frame).
2. **Concordância de presença binária** (AU ativo / não ativo, threshold por AU): F1-score.
3. **Concordância temporal** em janelas de 1s (pico em janela): IoU.
4. **Estabilidade**: variância intra-vídeo (bridge não pode ter mais ruído que py-feat × 1.5).

### Critério de aceite
Bridge promovido a default se, **nas 10 AUs críticas**:
- Pearson médio ≥ 0.65
- F1 binário médio ≥ 0.70
- IoU temporal médio ≥ 0.55

Se ≥ 1 AU crítica falhar critério, **não promove globalmente** — usa bridge só pras AUs aprovadas e mantém py-feat ou heurística existente nas demais (hybrid).

### Calibração de thresholds
Cada AU tem threshold de "ativo" diferente. Precisa varrer thresholds pra maximizar F1 contra py-feat. Deixar threshold por AU em config (`facial_analyzer.py` já usa pattern `SMILE_INDEX_THRESHOLD = 0.42`).

---

## 4. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Blendshape values são **suaves** (smooth coefficients), AUs FACS canônicas são picos discretos. | Usar derivada temporal + smoothing window pra detectar onset (não só intensidade absoluta). |
| MediaPipe blendshapes treinados em vídeo facial geral, não em oratória PT-BR. | Calibrar thresholds nos 7 vídeos do projeto, não usar defaults universais. |
| `cheekSquintLeft + Right` pode disparar com squint sem AU6 real (Duchenne). | Cross-check com smile (`mouthSmileL/R` simultâneo) pra confirmar Duchenne genuíno. |
| Vídeos handheld/mobile têm jitter — pode gerar falsos positivos em AUs sutis. | Reusar pattern do `BROW_RAISE_DELTA_THRESHOLD = 0.005` (já calibrado pra mobile, B10). |
| Latência. | Blendshapes são output direto do FaceLandmarker — sem overhead vs landmarks atuais. |
| Cobertura FACS menor que py-feat. | Documentar AUs faltantes; se análise depender de AU não coberta, manter dependência clara. |

---

## 5. Plano de migração sugerido (pra @dev)

**Fase 0 — Spike (1 dia):**
- Habilitar `output_face_blendshapes=True` no FaceLandmarker já instanciado em `facial_analyzer.py`.
- Coletar blendshapes nos 7 vídeos. Salvar como CSV.

**Fase 1 — Bridge module (2 dias):**
- Criar `_facs_blendshape_bridge.py` (peer de `_facs_ml.py`) — função puramente determinística que recebe blendshape dict e retorna AU dict.
- Sem fine-tuning, sem ML. Mapping table direta + thresholds.

**Fase 2 — Validação (1-2 dias):**
- Setup paralelo: py-feat (Py3.11 venv isolado) processa os 7 vídeos.
- Calcular as 4 métricas (Pearson, F1, IoU, estabilidade).
- Decisão: aprovado / hybrid / rejeitado.

**Fase 3 — Migração condicional:**
- Se aprovado: feature flag `USE_BLENDSHAPE_AU_BRIDGE=true` (padrão Epic 9). A/B contra py-feat por 1 sprint nos novos vídeos calibrados com Gui.
- Se hybrid: documentar quais AUs vêm de bridge, quais de py-feat.
- Se rejeitado: caveat no curiosity_queue, voltar a explorar OpenFace 3.0 license CMU comercial.

**Fase 4 — Cleanup (após 1 sprint estável):**
- Remover dependência py-feat se 100% das AUs cobertas.
- Atualizar `pyproject.toml` para Py3.12.

---

## 6. O que NÃO está no escopo deste spec

- Implementação do bridge — fica com @dev.
- Decisão de roadmap (quando priorizar) — fica com @pm.
- Treinar modelo ML pra refinar mapping — overengineering, deixar pra futura research se F1 ficar baixo.
- Migrar `_facs_ml.py` (modelo ML separado pro caso de blendshape failure) — independente.
- Refatorar `congruence_analyzer.py` pra consumir AU dict — pode precisar de pequena mudança de schema; @dev avalia.

---

## 7. Próximos research relacionados (curiosity queue)

- **Ainda aberto:** layer recipe HuBERT/WavLM converge em quais layers pra 14 dims (validação empírica nos 7 vídeos).
- **Ainda aberto:** AVI Challenge 2025 baseline absoluto vs gap Gui.
- **Resolvido nesta sessão:** MediaPipe blendshapes ≠ FACS canônico (loose mapping); OpenFace 3.0 license commercial bloqueada.

---

**Para implementar:** acionar @pm pra priorizar story, depois @dev pra Fase 0 (spike de 1 dia já desbloqueia Py3.12 informacionalmente).
