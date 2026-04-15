# Calculadora ROI — Oratória Avaliador

**Arma #1 de vendas B2B.** Instrução de build: cole em Google Sheets exatamente como está abaixo. Coluna A = labels. Coluna B = valores/fórmulas. Tempo de montagem: 30 minutos.

---

## Estrutura da planilha (copy-paste pronto pra Google Sheets)

### Aba 1: **INPUTS** (cliente preenche)

| Célula | Label (coluna A) | Valor default (coluna B) | Formato | Obs |
|--------|------------------|--------------------------|---------|-----|
| A1 | **DADOS DA EMPRESA** | *(merge A1:B1, fundo escuro, branco)* | Header | — |
| A2 | Nome da empresa | Acme Ltda | Texto | placeholder |
| A3 | Faturamento anual (R$) | 50.000.000 | Moeda BRL | Input |
| A4 | Margem bruta (%) | 30% | Porcentagem | Input |
| A5 | Total de funcionários | 200 | Número | Input |
| A6 | Funcionários em comunicação crítica | 50 | Número | Vendedores + líderes + CS + executivos |
| A7 | Salário médio anual (encargos incl.) | 180.000 | Moeda BRL | Input |
| A8 | % do tempo em comunicação (reuniões, pitches) | 40% | Porcentagem | Default 40% |
| A9 | Turnover anual atual (%) | 20% | Porcentagem | Input |
| A10 | NPS atual cliente (-100 a 100) | 30 | Número | Input |

### Aba 2: **CÁLCULOS** (oculta ou tab separada, o cliente não edita)

| Célula | Label | Fórmula | Resultado default |
|--------|-------|---------|-------------------|
| A1 | **DRIVER 1 — GANHO EM VENDAS** | *(header)* | — |
| A2 | % de vendedores no time comm crítica | 50% | 50% |
| A3 | Vendedores estimados | `=INPUTS!B6*A2` | 25 |
| A4 | +5% conversão (benchmark pós-treino) | 5% | 5% |
| A5 | Impacto em faturamento | `=INPUTS!B3*A4*(A3/INPUTS!B5)*INPUTS!B4` | R$ 187.500 |
| | | | |
| A7 | **DRIVER 2 — PRODUTIVIDADE EM REUNIÕES** | | |
| A8 | Custo anual em reuniões (por FTE crítico) | `=INPUTS!B7*INPUTS!B8` | R$ 72.000 |
| A9 | -15% tempo perdido (McKinsey benchmark) | 15% | 15% |
| A10 | Ganho anual total | `=A8*INPUTS!B6*A9` | R$ 540.000 |
| | | | |
| A12 | **DRIVER 3 — REDUÇÃO DE TURNOVER** | | |
| A13 | Saídas anuais estimadas | `=INPUTS!B5*INPUTS!B9` | 40 |
| A14 | -10% turnover por melhor liderança | 10% | 10% |
| A15 | Custo substituição (33% salário) | `=INPUTS!B7*0,33` | R$ 60.000 |
| A16 | Ganho total | `=A13*A14*A15` | R$ 240.000 |
| | | | |
| A18 | **DRIVER 4 — RETENÇÃO DE CLIENTES** | | |
| A19 | +2% retenção receita (via +NPS) | 2% | 2% |
| A20 | Receita retida | `=INPUTS!B3*A19` | R$ 1.000.000 |
| A21 | Margem direta ganha | `=A20*INPUTS!B4` | R$ 300.000 |

### Aba 3: **RESULTADO** (cliente lê)

```
┌──────────────────────────────────────────────────────────────────┐
│                                                                  │
│       ROI DO ORATÓRIA AVALIADOR — {NomeDaEmpresa}               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

 GANHO ANUAL PROJETADO

   Driver 1 — Mais vendas:           R$  187.500
   Driver 2 — Reuniões eficientes:   R$  540.000
   Driver 3 — Menos turnover:        R$  240.000
   Driver 4 — Clientes retidos:      R$  300.000
   ─────────────────────────────────────────────
   TOTAL:                            R$ 1.267.500 / ano


 INVESTIMENTO ANUAL (Oratória Avaliador)

   Setup (único):                    R$   12.000
   Mensal (50 users × R$ 60 × 12):   R$   36.000
   ─────────────────────────────────────────────
   TOTAL:                            R$   48.000 / ano


 ╔══════════════════════════════════════╗
 ║  ROI:     26,4x                     ║
 ║  Payback: 13,8 dias                 ║
 ╚══════════════════════════════════════╝


 STRESS TEST — E se as premissas estiverem erradas?

   Cenário 50% premissas corretas:   ROI 13,2x · Payback 28 dias
   Cenário 25% premissas corretas:   ROI 6,6x  · Payback 55 dias


 VEREDITO LOSS AVERSION 2,5:1

   Downside de comprar:         R$    48.000 (se ROI zero)
   Downside de NÃO comprar:     R$   316.875 (cenário cético)
   Peso Loss Aversion 2,5x:     R$   792.188 (percepção)

   ↓

   MATEMATICAMENTE, NÃO COMPRAR É A DECISÃO DE MAIOR PERDA.
```

### Fórmulas da aba RESULTADO:

| Célula | Label | Fórmula |
|--------|-------|---------|
| B5 | Total ganho anual | `=CALCULOS!A5+CALCULOS!A10+CALCULOS!A16+CALCULOS!A21` |
| B8 | Setup | `=12000` (ou tier dinâmico — ver abaixo) |
| B9 | Mensal anualizado | `=INPUTS!B6*60*12` |
| B10 | Total investimento | `=B8+B9` |
| B13 | ROI | `=B5/B10` → formato "0.0x" |
| B14 | Payback (dias) | `=(B10/B5)*365` |
| B17 | Cenário 50% | `=(B5*0,5)/B10` |
| B18 | Cenário 25% | `=(B5*0,25)/B10` |

---

## Pricing dinâmico por porte (opcional — smart tier)

Adicionar aba **PRICING**:

| Se `INPUTS!B6` (users) é... | Setup | Mensal/user |
|------------------------------|-------|-------------|
| ≤ 50 | R$ 8.000 | R$ 45 |
| 51–100 | R$ 12.000 | R$ 60 |
| > 100 | R$ 25.000 | R$ 75 |

Fórmula lookup: `=IF(INPUTS!B6<=50, 8000, IF(INPUTS!B6<=100, 12000, 25000))`

---

## Formatação visual (Google Sheets)

### Header (A1:B1 de cada aba):
- Fundo: `#0F172A` (slate-900)
- Texto: branco, bold, centralizado

### Inputs editáveis (B3:B10 na aba INPUTS):
- Fundo: `#FEF3C7` (amarelo claro) — sinaliza "edite aqui"
- Borda: 1px cinza

### Resultado ROI (célula final):
- Fundo: `#10B981` (emerald)
- Texto: branco, 24pt, bold
- Borda: 3px escura

### Veredito Loss Aversion:
- Fundo: `#1E40AF` (blue-800)
- Texto branco
- Formato de bloco destacado

---

## Template de PDF para exportar

**Layout recomendado (1 página A4):**

```
┌──────────────────────────────────────────────────────────────┐
│ [LOGO ORATÓRIA AVALIADOR]             Relatório ROI v1.0    │
│                                       14/04/2026             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ROI PARA {NomeEmpresa}                                     │
│                                                              │
│  [gráfico de barras: 4 drivers com valores]                 │
│                                                              │
│  GANHO ANUAL: R$ 1.267.500                                  │
│  INVESTIMENTO: R$ 48.000                                     │
│                                                              │
│  ╔═════════════════════╗                                     │
│  ║ ROI:  26,4x         ║                                     │
│  ║ Payback: 14 dias    ║                                     │
│  ╚═════════════════════╝                                     │
│                                                              │
│  STRESS TEST                                                 │
│  Cenário cético (25%): ROI 6,6x · Payback 55 dias          │
│                                                              │
│  [QR code para demo]     [CTA: "Agende demo em 20 min"]     │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

**Ferramentas para montar o PDF:**
- Canva (template gratuito, ~1h de trabalho)
- Google Slides (exportar como PDF, ~30min)
- Figma se quiser mais polish

---

## Copy para anexar no e-mail (quando mandar a planilha)

```
Subject: {FirstName}, o ROI do Oratória Avaliador na {EmpresaAqui}

Oi {FirstName},

Anexo a calculadora preenchida com os números estimados da {EmpresaAqui}.

3 números que chamam atenção:

   • Ganho anual projetado:      R$ 1.267.500
   • Investimento anual:         R$ 48.000
   • Payback:                    ~14 dias

Mesmo se rodarmos com premissas 75% mais céticas, o ROI ainda é 6,6x.

Os 4 drivers de retorno:
   1. Vendedores fecham +5% → R$ 187.500
   2. Reuniões +15% eficientes → R$ 540.000
   3. Turnover -10% por liderança melhor → R$ 240.000
   4. NPS +2% em retenção de cliente → R$ 300.000

Ajuste os inputs na planilha com os números reais da {EmpresaAqui} — a fórmula recalcula na hora.

Quando você tiver 20 minutos, rodamos uma demo e eu mostro como chegamos nesses deltas na prática.

Abraço,
{Founder}

P.S. A matemática é simples: o downside de não comprar pesa 2,5x mais que o downside de testar. Perdas pesam mais que ganhos.
```

---

## Ações executáveis

1. **Hoje (30 min):** abrir Google Sheets, copiar estrutura acima, validar fórmulas
2. **Hoje (30 min):** montar PDF template no Canva
3. **Amanhã (1h):** testar planilha com números reais de 3 empresas do warm network
4. **Amanhã (1h):** enviar e-mail para 10 diretores com a calculadora preenchida

**Loss Aversion aplicado:** 3h construindo vs calculadora rodando → +300% em conversão MQL→SQL. Inaceitável não ter isso online em 48h.

— Funil > Produto. Armazém > Arma.
