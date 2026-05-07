# 06 — Test Comparativo Concorrentes (artefatos públicos reais)

**Data:** 2026-05-06
**Wave:** Follow-up #2
**Método:** Coleta de artefatos públicos (docs oficiais, reviews independentes, Reddit, G2, Duarte) — sem signup, sem browser automation contra paywalls.

---

## Limitações declaradas

1. **NÃO foi feito signup** em qualquer concorrente — output real do produto rodando vem de reviewers terceiros (Duarte, G2, Reddit, blog comparisons).
2. **Confiança variável por concorrente:** alguns têm dezenas de reviews independentes (Yoodli, Poised); outros só têm página oficial (Elqo, Verble) → menor confiança.
3. **Reviews com viés:** páginas tipo "Best Yoodli alternatives" frequentemente são content-marketing de competidores. Priorizei Duarte (consultoria respeitada de comunicação) e G2 reviews críticas com voto negativo.

---

## 1. Cobertura de evidência por concorrente

| Concorrente | Evidência pública | Confiança comparação |
|---|---|---|
| **Yoodli** | Duarte review crítica, Reddit r/PublicSpeaking, G2, blog Yoodli próprio, support docs detalhados | **ALTA** |
| **Poised** | Duarte review crítica, G2 com elogios + críticas concretas | **ALTA** |
| **Orai** | Capterra, comparação Yoodli-blog, App Store listing | **MÉDIA** |
| **Speeko** | Página oficial Roger Love + MWM listing + comparação Yoodli-blog | **MÉDIA-ALTA** (Roger Love confirmado) |
| **Elqo** | Página oficial works/pricing, 1 comparação branded, TikTok presence | **BAIXA** |
| **Verble** | OpenTools, comparações em listas | **MÉDIA** — categorização wave 1 ESTAVA ERRADA |

---

## 2. Top 3 surpresas que contradizem ou refinam Wave 1

### Surpresa #1 — Verble NÃO é AI debate tool, é speech-writing service

Wave 1 categorizou Verble como "AI debate simulator" com "logic, evidence, rhetorical strength". **Errado.** Verble é uma ferramenta de **escrita de discurso assistida por IA** ($9.99 lifetime, não SaaS recorrente) com practice center via webcam + teleprompter. Casos de uso citados: weddings, palestras médicas, pitches investidor.

**Implicação:** Verble não compete diretamente com Oratória Avaliador. Compete com ChatGPT pra escrever discurso + grava você lendo. Sai da matriz competitiva como ameaça primária.

### Surpresa #2 — Speeko licenciou Roger Love como content embarcado

Wave 1: "Roger Love voice ressonância (chest/mask/head) é gap claro mas operacionalização incerta — esperar literatura ou Gemini Vision".

**Realidade:** Speeko anunciou **collab oficial com Roger Love** ("America's #1 voice coach") com **1000+ premium exercises**, daily warm-ups e exclusive content. Métricas que Speeko mede: pace, tone, filler words, intonation, sentiment, talk time, pitch range, vocal energy, sentiment scores.

**Implicação:** o "moat de voz Roger Love-style" foi PARCIALMENTE capturado — não como métrica científica de chest/mask/head ressonance, mas como **content premium licenciado** (lessons, exercícios). Diferenciador de produto, não de modelo. Tu não pode "competir contra Roger Love a Speeko" — tem que mirar gap não coberto.

### Surpresa #3 — Crítica pública valida tese do Oratória Avaliador

Reviewers respeitados (Duarte, Reddit) criticam concorrentes EXATAMENTE nos pontos onde tu é superior tecnicamente:

- **Yoodli pacing algorithm:** "Pacing algorithm produces misleading results by averaging fast and slow speech" (Duarte). Confirmação direta de que **pacing average** é ruim — tu tens pacing por janela temporal.
- **Yoodli feedback genérico:** "Generic recommendations without specific implementation guidance"; "doesn't identify specific opportunities for improvement... recommended pausing more, but didn't suggest where to add a pause" (Reddit). Confirmação direta que **feedback diagnóstico (24 hooks + congruence)** é o moat real.
- **Yoodli body language ausente:** "Body language analysis completely absent" (Duarte). Tu tem `facial_analyzer` + `gesture_analyzer` + `posture_analyzer` + congruence.
- **Yoodli ignora contexto:** "encouraging smiles during serious topics". Teu `congruence_analyzer` cruza face↔voz↔conteúdo.
- **Poised não tem visual no practice:** "no camera connection during practice eliminates visual feedback" (Duarte).

---

## 3. Tabela detalhada por concorrente

### Yoodli (HIGH evidence)

| Aspecto | Realidade pública | Oratória Avaliador | Veredicto |
|---|---|---|---|
| Profundidade dims (pública) | Smiles, eye contact, pause, pacing, filler words, perceived confidence, clarity, empathy, energy — ~9 dims | 14 dims + articulation passivo, com famílias Look/Feel/Sound | **Tu na frente em profundidade** |
| Body language | "Completely absent" (Duarte) | facial_analyzer + gesture_analyzer + posture_analyzer + congruence | **Tu na frente significativamente** |
| Hook analysis | Não detecta tipos de hook | 9-14 técnicas calibradas com qualidade boa/fraca | **Tu na frente** |
| Pacing methodology | Average WPM (criticado por enviesar) | Por janela temporal | **Tu na frente — validado por Duarte** |
| Real-time | Não (assíncrono) | Não (assíncrono) | **Par** |
| Practice/roleplay mode | **Sim — multi-persona, multi-session memory, Salesforce integration** | Review-only | **Yoodli na frente** |
| Integração calls | Salesforce + Gong + Slack | Standalone | **Yoodli na frente (B2B)** |
| Calibração ground truth | Não declarada | Mentor humano blind (Gui rubric 11-dim) | **Tu na frente — moat** |
| Feedback acionabilidade | "Generic without implementation" (Reddit) | 24 hooks + congruence | **Tu na frente — validado** |
| Free tier | 5 lifetime sessions ≥30s | Desconhecido | **Yoodli mais maduro de produto** |

### Poised (HIGH evidence)

| Aspecto | Realidade | Oratória Avaliador | Veredicto |
|---|---|---|---|
| Profundidade dims | Confidence, clarity, filler count, pace, energy, eye contact, words most spoken, empathy — ~8 dims | 14 dims + famílias | **Tu na frente em profundidade** |
| Real-time durante calls | **SIM — durante Zoom/Meet/Teams** | Não | **Poised na frente — categoria diferente** |
| Visual no practice | "Não conecta câmera no practice" (Duarte) | Sim | **Tu na frente** |
| Methodology transparency | "Vague and inconsistent... unclear what makes performance poor/okay/great" (G2 critical) | Truth Contract (Epic 8) com invariantes | **Tu na frente em rigor** |
| Roleplay/practice | Não (review only de meetings reais) | Não | **Par — categorias diferentes** |
| Voice analysis depth | Energy, pace básicos | voice_analyzer + tonality + variety | **Tu na frente** |

### Orai (MEDIUM evidence)

| Aspecto | Realidade | Oratória Avaliador | Veredicto |
|---|---|---|---|
| Plataforma | Mobile-first iOS/Android, sem web | Web (presumido) | **Orai na frente em mobile-native** |
| Dims | Pacing, fillers, energy, conciseness, clarity, confidence, facial expressions — ~7 | 14 + famílias | **Tu na frente em profundidade** |
| Practice modes | Freestyle + scripted + custom upload | Não | **Orai na frente em estrutura de prática** |
| Curriculum | Lições gamificadas adaptativas | Não | **Orai na frente** |
| Bugs reportados | "Buggy after extended use, clunky feedback, hard-to-read graphs" (Capterra) | Sem reports públicos | **Tu indeterminado mas Orai com débito de UX** |

### Speeko (MEDIUM-HIGH evidence)

| Aspecto | Realidade | Oratória Avaliador | Veredicto |
|---|---|---|---|
| Voice coach content | **Roger Love embarcado, 1000+ exercises premium** | Squad consultivo Roger Love (não embarcado) | **Speeko na frente em content** |
| Métricas voz | Pace, tone, fillers, intonation, sentiment, talk time, pitch range, vocal energy | voice_analyzer + tonality + variety | **Provavelmente par** |
| Practice format | 2-min daily exercises personalizados | Sem trilha curta diária | **Speeko na frente em ritual de prática** |
| Plataforma | iOS/Mac + web app.speeko.co | Web | **Par-ish** |
| Pricing | $19.99/mo, expensive without annual | — | informativo |

### Elqo (LOW evidence — só docs oficiais)

| Aspecto | Realidade | Oratória Avaliador | Veredicto |
|---|---|---|---|
| Plataforma | **PWA (Progressive Web App), sem app download** | Web | **Elqo formato interessante** |
| Dims expostas | Pace, tone, filler words, eye contact, facial expressions, body language, clarity, structure, content — ~9 dims | 14 + famílias | **Tu na frente em profundidade** |
| Visual analysis | Sim, via webcam (multimodal) | Sim | **Par — Elqo ambicioso pra novo entrante** |
| Content "estrutura" | Mede "structure" como dim isolada | Família narrativa próxima fase | **Elqo levanta flag — vale monitorar** |
| Pricing | $9.99/mo Pro, $99.99/yr Platinum, free 5 sessions | — | informativo |
| Maturidade | Novo entrante, evidência limitada | — | Watch list |

### Verble (REFINADO — wave 1 estava errado)

| Aspecto | Realidade | Oratória Avaliador | Veredicto |
|---|---|---|---|
| Categoria | **Speech-writing assistant + practice teleprompter** | Avaliador de oratória | **Categoria diferente — não é competidor direto** |
| Pricing model | $9.99 lifetime | — | Modelo diferente (não SaaS) |

---

## 4. Gaps competitivos do Oratória Avaliador (em produto, não em modelo) — priorizados

| Prioridade | Gap | Quem tem | Esforço estimado |
|---|---|---|---|
| **ALTA** | Practice/roleplay mode com persona AI + multi-session memory | Yoodli (referência), Elqo | Alto — exige LLM persona, voice TTS, conversation orchestration |
| **ALTA** | Feedback longitudinal / progress tracking visual | Yoodli (Admin Analytics), Speeko, Orai | Médio — UI sobre dados que tu já gera |
| **MÉDIA-ALTA** | Curriculum / trilha estruturada de prática | Orai (lessons gamificadas), Speeko (2min/dia), Elqo (drills) | Alto — exige design pedagógico + content |
| **MÉDIA** | Real-time durante calls reais (Zoom/Meet/Teams plugin) | Poised | Muito alto — engenharia de plugin + latência |
| **MÉDIA** | Mobile-first nativo | Orai, Speeko | Alto — port arquitetural |
| **BAIXA** | Free tier robusto pra acquisition | Yoodli (5 lifetime), Poised, Elqo (5 lifetime) | Decisão de business, não produto |
| **BAIXA** | Salesforce/Gong/Slack integration | Yoodli | Engenharia + B2B sales motion |

**Insight estratégico:** o gap mais defensável tecnicamente (practice mode multi-persona) também é o mais caro. Mas é o que transforma o produto de "boletim post-mortem" em "sparring partner". Yoodli investiu pesado aí — sinal de que é onde o valor B2B está sendo capturado.

---

## 5. Onde Oratória Avaliador está NA FRENTE (com evidência pública)

| Vantagem | Evidência pública que valida |
|---|---|
| **Pacing diagnóstico (não average)** | Duarte: "Yoodli pacing algorithm produces misleading results by averaging fast and slow speech" |
| **Feedback acionável (24 hooks + congruence)** | Reddit: "Yoodli recommended pausing more, but didn't suggest where to add a pause"; G2: "Poised feedback vague and inconsistent" |
| **Body language + facial + cross-modal** | Duarte: "Yoodli body language analysis completely absent"; Duarte: "Poised no camera connection during practice eliminates visual feedback" |
| **Profundidade analítica (14 dims + famílias)** | Concorrentes mais maduros expõem 6-9 dims. Tu tem 14 + estrutura familiar |
| **Hook analysis tipologizado** | Nenhuma evidência pública mostra concorrente detectando tipos de hook (pergunta reflexiva, dado, gancho história). Eles medem filler words, não estrutura de abertura |
| **Storytelling architecture (Vinh)** | Nenhum concorrente detecta bridge sentence, CTA, chemicals. Speeko (Roger Love) é VOZ, não estrutura narrativa |
| **Calibração com mentor humano blind** | Não há evidência pública de qualquer concorrente publicar ground truth ou método de calibração |
| **PT-BR cultural** | Todos English-first; nenhum review menciona PT-BR ou regionalismos |
| **Transparência de scoring** | G2 criticou Poised: "unclear what makes performance poor, okay, or great". Tu tem Truth Contract com invariantes (Epic 8) |

---

## 6. Onde concorrentes estão na frente (em produto)

| Vantagem deles | Quem | Implicação |
|---|---|---|
| Practice mode roleplay multi-persona com memória multi-session | Yoodli | Maior diferencial de produto. Categoria nova: sparring vs avaliação. |
| Real-time live durante calls (Zoom/Meet/Teams) | Poised | Categoria diferente (coach in-ear vs boletim) |
| Curriculum gamificado mobile | Orai, Speeko, Elqo | Acquisition + retention via hábito de 2min/dia |
| Roger Love content licenciado | Speeko | Marca embarcada acelera trust |
| B2B integrations (Salesforce, Gong, Slack) | Yoodli | Bloqueio de B2B sales |
| Admin Analytics / cohort dashboards | Yoodli | B2B venda — necessário pra empresa adotar |
| PWA sem download | Elqo | Distribuição mais leve |

---

## 7. Riscos competitivos identificados (novos, pós-evidência real)

1. **Yoodli Roleplay Memory** — multi-session AI persona com memória entre conversas. Sales call → discovery → demo encadeados. **Cria moat de produto enquanto tu não tem practice mode.**
2. **Speeko + Roger Love** — quando Bruno tentar adicionar dim "ressonância" Roger Love-style, Speeko pode dizer "nós já temos o Roger Love oficial". Tem que ser honesto que tu cobre ÁREA diferente (estrutura/diagnóstico) ou licenciar outro coach.
3. **Elqo PWA + verbal+visual em $9.99/mo** — entrante novo já cobre 9 dims e visual. Vale monitorar trimestralmente.
4. **Yoodli Admin Analytics + Salesforce** — bloqueio B2B sales coaching. Tu vai ter que escolher: B2C/coach white-label vs competir em B2B.

---

## 8. Recomendações pra @pm (priorização de produto)

Esta seção é informativa — implementação fica com @pm/@dev. Princípio: **proteger moat técnico + fechar gaps de produto que destravam adoção**, sem comprometer princípio "não medir > medir errado".

| Sugestão | Defesa baseada em evidência |
|---|---|
| **A. Investir em practice mode (multi-persona LLM)** | Maior gap competitivo identificado. Yoodli capturou valor B2B aqui. Sem isso, tu é "boletim post-mortem". |
| **B. Surface acionabilidade do feedback como diferencial de marketing** | Validado por crítica pública (Duarte + Reddit) que concorrentes falham em "WHERE/HOW to improve". Esse é teu trump card. |
| **C. Trilha longitudinal mínima (progresso por sessão)** | Esforço médio sobre dados existentes. Concorrentes têm; é table-stakes pra retenção. |
| **D. NÃO copiar "perceived confidence"** | Evidência: Yoodli proprietary, criticado como composto opaco; Poised "vague and inconsistent" pelo mesmo motivo. Confirma princípio "não medir > medir errado". |
| **E. Monitorar Elqo trimestralmente** | Entrante mais agressivo, modelo PWA + multimodal + pricing baixo. |
| **F. Decidir foco vertical** | B2C coach white-label vs B2B sales coaching (Yoodli/Salesforce) vs prosumer mobile (Orai/Speeko). Cada caminho exige investimentos diferentes. |

---

## Caveat final

Cobertura desta wave: ~70% por concorrente em média, com Yoodli/Poised altos (~85%) e Elqo baixo (~40%). Para validação **real real**, signup + teste contra 1-2 vídeos públicos seria a próxima wave (`07-*`). Esta wave já dá base sólida pra decisão estratégica de produto.
