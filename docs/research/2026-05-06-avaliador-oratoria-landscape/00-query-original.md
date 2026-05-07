# Query Original

**Data:** 2026-05-06
**Solicitante:** Bruno (proj. Oratória Avaliador)
**Comando:** `/tech-research "avaliador de oratória / comunicação"` → "todas" (4 tracks)

## Pergunta

"avaliador de oratória / comunicação" — landscape research em 4 tracks paralelas.

## Contexto do projeto (não pesquisado)

- IA multimodal (Next.js + Python ml-worker + Supabase) que avalia vídeos de oratória.
- Epic 9 completo (2026-04-17): 14 dimensões, 3 famílias **Look / Feel / Sound** + articulation passivo. 311 testes.
- Sprint calibração 04-29 → 05-06: 9 dims validadas 1-a-1, iris-based gaze, 24 hooks, congruence pedagógica. Gap 18-38pts vs ground truth Gui.
- Mentor Guilherme Reginatto fornece ground truth (rubric 11-dim, blind protocol).
- Squad consultivo: Patsy Rodenburg (presença) + Roger Love (voz).
- Bibliotecas atuais: MediaPipe (gaze, face), wav2vec2 removido do HF, py-feat 0.6.2 bloqueia Py3.12, Gemini Vision on-demand.

## 4 Tracks

1. **SOTA acadêmico 2024-2026** — papers, datasets, fusion architectures.
2. **Concorrentes comerciais** — Yoodli, Poised, Orai, Speeko, Virtual Orator, Verble, etc.
3. **Rubricas humanas** — Toastmasters, ETS/TOEFL/IELTS, Patsy Rodenburg, Roger Love. Cross-walk vs 14 dims.
4. **Tecnologia substituta** — wav2vec2, py-feat, MediaPipe-iris, prosody, gesture.
