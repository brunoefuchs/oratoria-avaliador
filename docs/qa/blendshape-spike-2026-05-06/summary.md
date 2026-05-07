# Blendshape Spike — Story 10.2 Fase 0

**Data:** 2026-05-06

**Objetivo:** Verificar que MediaPipe FaceLandmarker expõe blendshapes ARKit-style nos 7 vídeos do bench. Standalone deliverable; desbloqueio Py3.12 informacional.

## Blendshapes detectados (52)

```
_neutral, browDownLeft, browDownRight, browInnerUp, browOuterUpLeft, browOuterUpRight, cheekPuff, cheekSquintLeft, cheekSquintRight, eyeBlinkLeft, eyeBlinkRight, eyeLookDownLeft, eyeLookDownRight, eyeLookInLeft, eyeLookInRight, eyeLookOutLeft, eyeLookOutRight, eyeLookUpLeft, eyeLookUpRight, eyeSquintLeft, eyeSquintRight, eyeWideLeft, eyeWideRight, jawForward, jawLeft, jawOpen, jawRight, mouthClose, mouthDimpleLeft, mouthDimpleRight, mouthFrownLeft, mouthFrownRight, mouthFunnel, mouthLeft, mouthLowerDownLeft, mouthLowerDownRight, mouthPressLeft, mouthPressRight, mouthPucker, mouthRight, mouthRollLower, mouthRollUpper, mouthShrugLower, mouthShrugUpper, mouthSmileLeft, mouthSmileRight, mouthStretchLeft, mouthStretchRight, mouthUpperUpLeft, mouthUpperUpRight, noseSneerLeft, noseSneerRight
```

## Per-vídeo stats

| Apelido | Status | Frames sampled | Face detected | Detection % | Elapsed (s) |
|---|---|---|---|---|---|
| GUI ITAJAI | ✅ | 329 | 329 | 100.0% | 4.3 |
| ALUNA MORENA | ✅ | 404 | 404 | 100.0% | 5.1 |
| GUI PRIME | ✅ | 351 | 351 | 100.0% | 6.3 |
| ALUNO MONO | ✅ | 324 | 324 | 100.0% | 3.8 |
| ALUNA LOIRA | ✅ | 198 | 198 | 100.0% | 2.2 |
| GUI WENDEL | ✅ | 222 | 206 | 92.8% | 2.7 |
| GUI ARARANGUA | ✅ | 264 | 224 | 84.8% | 2.5 |

## Conclusão Fase 0

- Vídeos processados com sucesso: **7/7**
- Blendshapes ARKit-style expostos: **52**
- Esperado pra mapping table de `05-mediapipe-au-bridge-spec.md`: 52 → ✅ confirmado

**Próxima fase:** Fase 1 — bridge module determinístico `_facs_blendshape_bridge.py` (ver story 10.2 AC2).
