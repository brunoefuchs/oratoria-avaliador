# Handoff — Design System "The Resonant Stage" (Showcase HTML)

**Data:** 2026-04-13
**Agente:** @ux-design-expert (Uma)
**Branch:** main

---

## 1. Objetivo

Criar uma página HTML de showcase do Design System do Oratória Avaliador, baseada em:

- **Estrutura de referência:** `design/design-system-showcase.html` (Neural Architect — usado apenas como modelo de layout/tabs, não de design)
- **Sistema de design:** `design/modelo design/stitch_gravar_upload_de_v_deo/eloquent_ai/DESIGN.md` (The Resonant Stage)
- **Tokens reais extraídos de:** `design/modelo design/stitch_gravar_upload_de_v_deo/home_dashboard_1/code.html`

## 2. Entregável

**Arquivo único:** `design/design-system-resonant-stage.html`

- Self-contained (Tailwind CDN + Google Fonts + Material Symbols)
- Abre direto no browser: `file:///C:/Users/bruno/code/oratoria-avaliador/design/design-system-resonant-stage.html`
- 6 tabs com navegação JS (`switchTab()`)
- Showcase original (`design-system-showcase.html`) **preservado** como referência

## 3. Estrutura de Tabs

| Tab | Conteúdo |
|---|---|
| **Design System** | Hero · Cores (4 grupos: Primary, Secondary, Tertiary+Error, 7 Surfaces tonal) · Texto/Outline · Tipografia (Manrope display + Plus Jakarta body, com "Power Gap") · Elevação (carved, glass, ambient shadow) · Componentes (5 botões, 3 cards, inputs com focus glow, chips, fluency wave SVG, FAB + bottom nav) · Iconografia (16 ícones) · Do's & Don'ts |
| **Dashboard** | Greeting · Bento grid (score 78/100 + quote card) · 3 performances recentes · Coaching plan + streak |
| **Record** | Toggle gravar/upload · Viewport com rule-of-thirds grid · CTA central AI Pulse · Form de contexto |
| **Análise IA** | Player + timeline com 5 marcadores SVG · Score card com 4 dimensões · Cards Ritmo/Presença/Clareza |
| **Feedback** | 3 recomendações priorizadas (alto/médio/contínuo) + card "Celebrate milestone" tertiary |
| **Biblioteca** | Curso destaque · Grid 6 cards (5 disponíveis + 1 locked Pro) · Filtros por categoria |

## 4. Tokens Aplicados

### Cores (Tailwind extend)

```yaml
primary: "#a2c9ff"
primary-container: "#004d89"
on-primary: "#00315b"
secondary: "#45d8ed"
secondary-container: "#00bacd"
on-secondary: "#00363d"
tertiary: "#ffb954"          # uso parcimonioso (reward only)
on-tertiary: "#452b00"
error: "#ffb4ab"
background/surface: "#0b1326" # NUNCA usar #000 puro
surface-container-lowest: "#060e20"
surface-container-low: "#131b2e"
surface-container: "#171f33"
surface-container-high: "#222a3d"
surface-container-highest: "#2d3449"
surface-bright: "#31394d"
on-surface: "#dae2fd"
on-surface-variant: "#c3c6d4"
outline: "#8d909d"
outline-variant: "#434652"     # ghost borders @ 15%
```

### Tipografia

```yaml
headline: Manrope (400, 500, 600, 700, 800)
body:     Plus Jakarta Sans (400, 500, 600, 700)
label:    Plus Jakarta Sans (uppercase, tracking 0.2em–0.4em)
display-lg: Manrope 800 · clamp(3.5rem, 8vw, 5.5rem) · letter-spacing -2%
```

### Border Radius

```yaml
DEFAULT: 0.5rem
md: 0.75rem
lg: 1rem
xl: 1.5rem
2xl: 2rem
3xl: 2.5rem        # cards principais
full: 9999px       # CTAs primários
```

## 5. Regras do Resonant Stage Aplicadas

| Regra | Implementação no HTML |
|---|---|
| **No-Line Rule** | Sectioning via tonal layering — sem `border` 1px para separar seções |
| **Ghost Borders** | Classe `.ghost-border` = `box-shadow: inset 0 0 0 1px rgba(67,70,82,0.15)` |
| **Glass Panel** | Classe `.glass` = `bg rgba(45,52,73,0.6)` + `backdrop-filter: blur(20px)` |
| **AI Pulse Gradient** | Classe `.ai-pulse` = linear-gradient 135° secondary → primary-container |
| **Ambient Shadow** | Classe `.cta-glow` em CTAs · `box-shadow: 0 20px 40px rgba(69,216,237,0.25)` |
| **Fluency Wave** | Classe `.fluency-wave` (linha animada) + variante SVG path com gradient stops |
| **Power Gap** | Display-lg + label-md adjacentes (ex.: "78" + "Current Eloquence") |
| **Reward Color** | `tertiary` aparece apenas em: streak counter, celebrate milestone, recomendações de continuidade |
| **No Pure Black** | `surface = #0b1326` em todos os fundos |
| **Focus Glow** | Classe `.focus-glow:focus-within` em inputs · ring 1px secondary @ 40% + outer glow 16px |

## 6. Animações Custom

| Nome | Uso |
|---|---|
| `animate-glow` | Pulsação no botão de gravação (mic ativo) |
| `animate-float` | FAB Quick Practice + ícone hero da biblioteca |
| `fluency-wave` (CSS) | Linha de cadência no rodapé do score card |
| SVG path animado | Onda de ritmo na timeline da Análise IA |

## 7. Próximos Passos Sugeridos

1. **Revisão visual** — abrir o HTML e validar contraste WCAG AA em texto on-surface-variant sobre surface-container-low.
2. **Migração para o app real** — extrair tokens para `apps/web/tailwind.config.ts` e refatorar componentes existentes (`apps/web/src/components/`) para o novo sistema.
3. **Substituir o `design-system-showcase.html` antigo (Neural Architect)** se o novo design for o oficial — ou manter como comparação.
4. **Aplicar nas telas reais:** começar pela `apps/web/src/app/report/[id]/replay/page.tsx` e `processing-status.tsx` (já modificadas no working tree).
5. **Componentes faltantes a desenhar** se houver expansão: modal, toast, dropdown, date picker, tooltip, skeleton loader.

## 8. Arquivos Tocados Nesta Sessão

```
A  design/design-system-resonant-stage.html       (novo, ~830 linhas)
A  docs/sessions/2026-04/handoff-design-system-resonant-stage.md  (este)
```

Nenhum código de produção foi alterado. Showcase original preservado.

## 9. Referências

- **DESIGN.md fonte:** `design/modelo design/stitch_gravar_upload_de_v_deo/eloquent_ai/DESIGN.md`
- **14 telas modelo disponíveis em:** `design/modelo design/stitch_gravar_upload_de_v_deo/*/code.html`
- **Estrutura de showcase modelo:** `design/design-system-showcase.html`

---

— @ux-design-expert (Uma)
