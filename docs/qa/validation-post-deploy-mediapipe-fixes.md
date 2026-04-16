# Test Plan — Validação Pós-Deploy dos 5 Fixes MediaPipe

**Contexto:** PR #20 mergeado via admin override em 2026-04-16T11:12:20Z (merge commit `f71014b`). Re-aplica MP-1, MP-2, MP-3 que foram perdidos em rebase do Epic 8. MP-4 e MP-5 já estavam em main. Deploy Railway esperado ~5-7min pós-merge.

---

## 1. Pré-validação: confirmar que deploy pegou o commit

### 1.1. Railway Dashboard (primário)

1. Abrir https://railway.app/dashboard
2. Projeto `oratoria-avaliador` → serviço `ml-worker` → Deployments
3. Procurar deployment com:
   - Commit SHA: `f71014b` ou mais novo
   - Status: **Active** (verde)
   - Timestamp: > 2026-04-16T11:12:20Z
4. Se status for `Building` ou `Deploying` → aguardar e re-checar

### 1.2. Endpoint `/health` (secundário, se existir)

```bash
curl https://<ml-worker-url>/health  # se endpoint existir
```

Se retornar version ou git SHA, confirmar que bate com `f71014b`.

### 1.3. Timestamp da última modificação no Supabase

Se o endpoint do ml-worker não expõe version, alternativa: subir 1 vídeo → ver em qual "geração" de código ele foi processado pelos markers abaixo.

---

## 2. Test plan — markers concretos pra saber se fixes pegaram

**Protocolo:** usar o MESMO vídeo que rodou antes (53.85s, evaluation `775b5f6b...`) pra ter comparação direta.

### 2.1. Submeter análise via web app

1. Abrir o web app em produção
2. Upload do vídeo de referência (WhatsApp 53s — o mesmo da análise de 2026-04-16T09:44)
3. Aguardar processamento
4. Ir no Supabase → `aggregated_metrics` → pegar a NOVA linha mais recente
5. Comparar com os valores abaixo

### 2.2. Markers obrigatórios (PASS se TODOS batem)

| Dimensão | Pré-fix (análise 09:44) | **Pós-fix esperado** | Marker |
|----------|-------------------------|----------------------|--------|
| `posture score` | 76 | **~66** (±3) | MP-2 aplicado ✓ |
| `gesture score` | 68 | **~85** (±5) | MP-3 aplicado ✓ |
| `dimension_scores.posture` | 76 | ~66 | idem |
| `dimension_scores.gesture` | 68 | ~85 | idem |

### 2.3. Markers em `detailed_metrics` (nas tabelas `analyses`)

Query Supabase:

```sql
SELECT dimension, metrics
FROM analyses
WHERE evaluation_id = '<novo_eval_id>'
  AND dimension IN ('gesture', 'posture');
```

Verificar nas métricas retornadas:

#### `gesture`
- `eye_contact_pct`: antes 100%, **pós-fix ~95.4%** (MP-1)
- `desvio_positivo_pct`: **deve existir** (campo novo MP-1)
- `desvio_negativo_pct`: **deve existir** (campo novo MP-1)
- `desvio_neutro_pct`: **deve existir** (campo novo MP-1)
- `zona_ideal_pct`: antes 1.5%, **pós-fix ~91%** (MP-3)

#### `posture`
- `dinamismo_postural`: **deve existir** (campo novo MP-2), valor entre 0-100
- `sub_scores.dinamismo`: **deve existir**
- `padrao_movimento`: pode ser `energetico` se orador dinâmico (MP-4, já em main)

#### `archetypes`
- `score`: se lock-in (persona consistente), deve ser **≥35** (MP-5 floor, já em main)

---

## 3. Cenários de falha e diagnóstico

| Sintoma | Causa provável | Ação |
|---------|---------------|------|
| Scores idênticos à análise 09:44 (posture=76, gesture=68) | Deploy não rodou OU Railway usa cache de build | Railway Dashboard → force redeploy |
| `desvio_negativo_pct` ausente nas métricas | MP-1 não aplicado | Verificar qual SHA está em produção; se não for f71014b ou descendente, Railway não pegou |
| `dinamismo_postural` ausente | MP-2 não aplicado | idem |
| `zona_ideal_pct` ainda baixo (<20%) | MP-3 não aplicado | idem |
| Deploy failed com erro Python | Possível: SyntaxError ou ImportError | Ver logs Railway. Suspeito: incompatibilidade com Truth Contract wrapper |
| `tonality: 0` (continua) | Não é bug do PR #20 — Epic 7 storytelling/facial/tonality separado | Escopo diferente — não bloqueia este validation |
| `variety: incomplete` | Não é bug do PR #20 — depende de gesture com hand_visible_pct alto | Pode ser efeito colateral da mudança em gesture, mas provável cause: 76 erros ruff do 8.2 afetam runtime |

---

## 4. Evidence pack

Quando rodar validação, salvar como evidência em `docs/qa/evidence/2026-04-16-post-deploy-validation.md`:

```markdown
# Evidence — Pós-deploy PR #20

**Video:** <UUID>
**Evaluation ID:** <novo>
**Timestamp:** <quando rodou>

## Comparação direta

| Métrica | Pré-fix (eval 775b5f6b) | Pós-fix (eval <novo>) | Delta | PASS? |
|---------|--------------------------|------------------------|-------|-------|
| posture | 76 | X | +X | ✓/✗ |
| gesture | 68 | X | +X | ✓/✗ |
| eye_contact_pct | 100% | X% | -X | ✓/✗ |
| zona_ideal_pct | 1.5% | X% | +X | ✓/✗ |
| desvio_negativo_pct | (ausente) | X% | NOVO | ✓/✗ |
| dinamismo_postural | (ausente) | X | NOVO | ✓/✗ |

## Verdict

[PASS | FAIL | PARTIAL] — <justificativa>
```

---

## 5. Gate de sucesso

**PASS** se:
- 3+ markers da seção 2.2 batem dentro da tolerância (±5 pontos)
- 5+ campos novos da seção 2.3 existem no output

**CONCERNS** se:
- 1-2 markers dentro da tolerância, outros fora
- Campos novos existem mas valores inesperados

**FAIL** se:
- Scores idênticos à análise 09:44 (deploy não pegou)
- Campos novos ausentes
- Deploy Railway status Error

---

## 6. Validação end-to-end (opcional, mais completa)

Se quiser validar além dos markers, rodar 2 vídeos de contexto diferente:

1. **Vídeo de orador estático** (tipo WhatsApp 53s) — esperado: posture 55-70, dinamismo 30-50
2. **Vídeo de orador energético** (tipo Insta-1 68s) — esperado: posture 70-85, padrão `energetico`, dinamismo 70-90

Se AMBOS batem os ranges, calibração está robusta. Se só 1 bater, fix é específico e precisa mais smoke.

---

## 7. Próximo passo após validação PASS

- Documentar evidence em `docs/qa/evidence/`
- Atualizar `docs/sessions/2026-04/handoff-sessao-2026-04-15-completa.md` com evidência de calibração em produção
- Prosseguir com fluxo de ground truth (Story 7.7 — Gui Reginatto) sabendo que o pipeline está calibrado

---

— Quinn, guardião da qualidade 🛡️
