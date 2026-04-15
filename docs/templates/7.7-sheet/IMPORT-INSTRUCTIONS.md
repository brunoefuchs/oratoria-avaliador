# IMPORT-INSTRUCTIONS — Google Sheet do Ground Truth 7.7

**Tempo estimado:** 15min
**Resultado:** Google Sheet funcional pro mentor Gui Reginatto avaliar 10 vídeos com data validation completa.

---

## Arquivos entregues nesta pasta

| Arquivo | Vai virar | Linhas |
|---------|-----------|--------|
| `readme-content.md` | Aba `README` (texto) | — |
| `calibracao.csv` | Aba `Calibração` | 1 header + 1 linha |
| `ground-truth.csv` | Aba `Ground Truth` | 1 header + 10 linhas |
| `comparacao.csv` | Aba `Comparação` | 1 header + 11 linhas (com fórmulas) |

---

## Passo 1 — Criar Google Sheet

1. Abre [sheets.google.com](https://sheets.google.com) > Blank sheet
2. Renomeia pra: **`Oratoria Avaliador — Ground Truth Gui 7.7`**
3. Renomeia a aba atual (Sheet1) pra `README`

---

## Passo 2 — Importar as 4 abas

### 2.1 Aba `README`

1. Abre `readme-content.md` neste repo
2. Copia o conteúdo todo
3. Cola na célula `A1` da aba `README`
4. Dá um `Format > Wrap text > Wrap`
5. Alarga a coluna A pra ~800px

### 2.2 Abas `Calibração`, `Ground Truth`, `Comparação`

Para cada uma:

1. Clica no `+` embaixo da tela > cria nova aba
2. Renomeia conforme o nome do CSV (sem .csv)
3. **File > Import**
4. **Upload** tab > arrasta o arquivo `.csv` correspondente
5. Em "Import location": **"Replace current sheet"**
6. Em "Separator type": **Detect automatically** (ou "Comma")
7. **Import data**

Ordem recomendada: README → Calibração → Ground Truth → Comparação

---

## Passo 3 — Aplicar Data Validation

Vai na aba `Ground Truth`. Selecione o range, depois `Data > Data validation > Add rule`.

### 3.1 Score columns (C, E, G, I, K, M, P, S, V, X, Z — todas as `*_score`)

Range: ex. `C2:C11` (posture_score), faça pra cada coluna de score.

**Criteria:** `Custom formula is`
**Formula:** `=AND(C2>=0,C2<=100,MOD(C2,10)=0)`
**On invalid:** `Reject input`
**Advanced:** marcar "Show validation help text" com `0-100, múltiplos de 10`

Dica: faça 1 coluna, use `Paint format` (ícone do pincel) pra propagar pras outras score columns.

**Exceção — temporal_score (coluna X):** Aceitar também "N/A".
**Formula:** `=OR(AND(X2>=0,X2<=100,MOD(X2,10)=0),UPPER(X2)="N/A")`

### 3.2 archetypes_arquetipo_principal (coluna N)

Range: `N2:N11`
**Criteria:** `Dropdown (from a range)` OR `Dropdown`
**Options:** `guerreiro`, `sábio`, `bobo`, `herói`, `cuidador`, `criador`, `rebelde`, `mago`, `inocente`, `amante`, `explorador`, `governante`

### 3.3 identity_vicios_observados (coluna Q)

**Criteria:** `Dropdown (multiple)` (novo recurso do Google Sheets 2024+)
**Options:** `vitimização`, `comparação`, `rejeição`, `culpa`, `injustiça`

Se sua conta não suportar multi-select: usar `Dropdown` simples com todas as combinações (ex: "vitimização+culpa") OU deixar livre com nota de preenchimento no README.

### 3.4 opening_tecnica_usada (coluna T)

**Criteria:** `Dropdown`
**Options:** `impacto`, `pergunta`, `dado`, `história`, `quebra-gelo`, `provocação`, `nenhuma`

### 3.5 Campos de justificativa obrigatória (AA, AB, AC)

Colunas: `overall_forca_principal`, `overall_fraqueza_principal`, `overall_impressao_geral`

Range: `AA2:AA11` (repete pra AB e AC)
**Criteria:** `Custom formula is`
**Formula:** `=LEN(AA2)>=30`
**On invalid:** `Reject input`
**Help text:** `Mínimo 30 caracteres`

---

## Passo 4 — Frozen header + rubric de referência

1. Clica na linha 1 (header) > `View > Freeze > 1 row`
2. Opcional: inserir linha 2 com descritores resumidos pra cada dimensão:
   - posture_score: "0-20 fechado / 41-60 neutra / 81-100 firme-aberta"
   - gesture_score: "0-20 travado / 41-60 mecânico / 81-100 ilustrativo"
   - (etc — vide rubric completa em `docs/sessions/2026-04/handoff-7.7-ground-truth-rubric-gui-reginatto.md`)

Se inserir, congelar 2 linhas em vez de 1.

---

## Passo 5 — Formatação condicional (aba Comparação)

1. Selecione `E2:E12` (coluna `distance`)
2. `Format > Conditional formatting`
3. **Rule:** `Greater than` → `20`
4. **Style:** preencher célula vermelho claro, texto vermelho escuro
5. Aplicar

A coluna `flag_gt20` já usa fórmula `=IF(E2>20,"FLAG","")`.

---

## Passo 6 — Compartilhar com Gui

1. Canto superior direito > **Share**
2. **Get link** → mudar pra `Anyone with the link`
3. Permissão: **Editor** (Gui vai preencher)
4. Copia o link e manda pro Gui

⚠️ NÃO ATIVAR Editor ainda se Bruno não quiser que outras pessoas vejam. Alternativa: adicionar Gui pelo e-mail dele especificamente.

---

## Passo 7 — Exportar CSV depois (pro script rodar)

Quando Gui terminar os 10 vídeos:

1. Aba `Ground Truth` > `File > Download > Comma-separated values (.csv)`
2. Salvar como `ground-truth-gui.csv` na raiz do repo (ou onde preferir)
3. Rodar:
   ```bash
   python scripts/compare-ground-truth.py \
     --gui-csv ./ground-truth-gui.csv \
     --output ./ground-truth-comparison.csv
   ```
4. Copiar conteúdo de `ground-truth-comparison.csv` pra aba `Comparação` do sheet

---

## Checklist pós-setup

- [ ] 4 abas criadas (README, Calibração, Ground Truth, Comparação)
- [ ] Data validation aplicada em todas as 11 colunas de score
- [ ] temporal_score aceita N/A
- [ ] 3 dropdowns funcionando (arquétipo, vícios, técnica abertura)
- [ ] Min 30 chars nas 3 colunas de overall
- [ ] Frozen header
- [ ] Formatação condicional na aba Comparação
- [ ] Link compartilhado com Gui (Editor)
- [ ] Bruno testou: preencheu 1 linha de teste, validação bloqueia valores fora do range

---

## Troubleshooting

**Problema:** "Não consigo criar multi-select dropdown"
**Solução:** usar dropdown simples com entradas únicas. Gui pode preencher em texto livre separado por vírgula se necessário.

**Problema:** "Data validation rejeita a linha inteira"
**Solução:** Data validation é por célula. Fórmula deve referenciar a célula atual (`C2` quando aplicado em C2), não range.

**Problema:** "Gui abriu e não vê o README"
**Solução:** README é a primeira aba — deve abrir automaticamente. Se não, mover pra primeira posição (clicar aba e arrastar).

**Problema:** "Fórmulas da Comparação sumiram após import"
**Solução:** Import CSV converte fórmulas em texto. Refaz manualmente as colunas E e F depois do import. Ver fórmulas em `comparacao.csv`.

---

## Referências

- **Rubric master:** `docs/sessions/2026-04/handoff-7.7-ground-truth-rubric-gui-reginatto.md`
- **QA Gate (PASS v2):** `docs/qa/7.7-rubric-validation.md`
- **Script consolidação:** `scripts/compare-ground-truth.py`
- **Story master:** 7.7 (parte do Epic 7 — Harness Multi-IA)

— Dex, sempre construindo 🔨
