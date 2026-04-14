# Handoff — Migração Completa do App para "The Resonant Stage"

**Data:** 2026-04-13
**Agente:** @ux-design-expert (Uma)
**Branch:** main
**Modo:** YOLO

---

## 1. Objetivo

Reformular todo o app `apps/web` aplicando o design system **"The Resonant Stage"** (criado em `design/design-system-resonant-stage.html`), com foco em responsividade **mobile + desktop**, **sem remover nenhuma função**.

## 2. Validações

- **TypeCheck:** `npx tsc --noEmit` → **exit 0** (zero erros)
- **Next Build:** `npx next build` → **compilação OK**, todas as 8 rotas geradas
- **Bundle:** First Load JS compartilhado = **87.3 kB** (saudável)

## 3. Arquivos Tocados (13 arquivos)

### Infraestrutura / Tokens (3)

| Arquivo | Mudança |
|---|---|
| `apps/web/tailwind.config.ts` | +65 linhas · paleta completa Resonant Stage, `font-headline` (Manrope), `font-body/label` (Plus Jakarta), border radius escalado, `bg-ai-pulse` gradient, shadows `cta-glow`/`ambient`/`focus-ring`, keyframes `glow-pulse` + `float` |
| `apps/web/src/app/globals.css` | +90 linhas · base (scrollbar dark, selection, Material Symbols axis), components (`.glass`, `.glass-low`, `.ghost-border`, `.fluency-wave`, `.focus-glow`, `.display-lg`, `.display-md`, `.stage-ambient`) |
| `apps/web/src/app/layout.tsx` | Fonts via `next/font/google` (Manrope + Plus Jakarta Sans) com CSS variables; Material Symbols via `<link>`; body com `bg-background text-on-surface font-body`; classe `dark` no html |

### Componentes (7 — 6 refatorados + 1 novo)

| Arquivo | Mudança |
|---|---|
| `apps/web/src/components/app-shell.tsx` | **NOVO** · header sticky com glass-low, logo gradient, back button, nav Início/Evolução; props `maxWidth`, `showBack`, `backHref`, `backLabel` |
| `apps/web/src/components/score-card.tsx` | Surface tonal + ghost border · Material Symbols por dimensão (`mic`, `graphic_eq`, `visibility`, `accessibility`, `chat_bubble`) · barra de progresso tonal por score · hover state com arrow_forward |
| `apps/web/src/components/star-rating.tsx` | Card em surface-container-low · estrelas `tertiary` (reward) · textarea com focus-glow · CTA ai-pulse |
| `apps/web/src/components/processing-status.tsx` | Barra de progresso % gradient · step cards com tonal layering · check icon Material Symbols · spinner current step em ai-pulse shadow-cta-glow |
| `apps/web/src/components/onboarding.tsx` | 3 slides com kickers + displays grandes · dimension cards em tonal · stepper em ai-pulse · CTA pill-shape |
| `apps/web/src/components/video-uploader.tsx` | Drop zone rounded-3xl · border dashed outline-variant · ícone videocam · chips MP4/500MB/10min · progress bar gradient + animação glow-pulse no cloud_upload |
| `apps/web/src/components/video-player.tsx` | Player em card tonal · timeline com lanes coloridas (error/tertiary/secondary) · playhead com glow secondary · legenda em chips ghost-border |

### Páginas (8 refatoradas)

| Rota | Mudança principal |
|---|---|
| `app/page.tsx` (home) | Hero com `display-lg` + gradient text · chips de dimensões · grid 3-col de highlights · dentro do AppShell |
| `app/evolution/page.tsx` | Hero com score diff primeira→última · cards de dimensão com delta badge · histórico em lista tonal |
| `app/evaluate/[id]/context/page.tsx` | Stepper 6 steps com checkbox custom ai-pulse · sentimento em grid 5 colunas · empty state com icons |
| `app/processing/[id]/page.tsx` | Hero com "Iluminando seu palco" · FAB central pulsante · error states em error-container |
| `app/report/[id]/page.tsx` | **Dashboard completo** — hero + score gigante gradient · força cards · grid 2/3 colunas de dimensões · 80/20 em `<details>` numerados com ai-pulse · Congruência · Arco da performance (3 terços) · plano 12 semanas grid 2-col · mensagem final em card com format_quote · 4 CTAs finais tonais |
| `app/report/[id]/[dimension]/page.tsx` | Hero com ícone da dimensão · métricas grid · sub-scores com barras tonais · arquétipos em ai-pulse bars · pausas em 3 mini-cards · feedback v1/v2 em cards tonais |
| `app/report/[id]/replay/page.tsx` | Header gradient · VideoPlayer integrado · 4 stats cards tonais · warning olhar baixo em tertiary |
| `app/report/[id]/shared/page.tsx` | Badge "somente leitura" · score hero centralizado · forças/melhorias/plano · mensagem final em tonal highest |

## 4. Padrões Aplicados (Resonant Stage)

### Cores (sistema tonal, não "semântico verde/amarelo/vermelho")

- **Score ≥ 70** → `text-secondary` (#45d8ed) · celeste, bioluminescente
- **Score 40-69** → `text-tertiary` (#ffb954) · dourado, atenção suave
- **Score < 40** → `text-error` (#ffb4ab) · vermelho suave (nunca `#ff0000`)

### Regras obrigatórias

| Regra | Aplicação |
|---|---|
| **No-Line Rule** | Seções separadas por tonal layering (container-low ↔ container-high) · zero `border-1px` como separador |
| **Ghost Borders** | `.ghost-border` (15% opacity) em todos os cards |
| **AI Pulse CTAs** | Todos botões primários com `bg-ai-pulse` + `shadow-cta-glow` + `rounded-full` |
| **Tertiary parcimônia** | `tertiary` apenas em reward states (streak, celebrate, warnings médios, melhorias) |
| **No pure black** | `surface = #0b1326` em todos os fundos, nunca `#000` |
| **Focus Glow** | Inputs usam `.focus-glow` (ring secondary + glow 16px) |
| **Fluency Wave** | Linha animada no rodapé dos hero cards |
| **Stage Ambient** | `.stage-ambient` gera blob radial secondary/6% em heros |

### Tipografia

- **`display-lg`** → Manrope 800 · clamp(2.5rem → 4.5rem) · letter-spacing -2%
- **`font-headline`** → títulos de seção (Manrope 700/800)
- **`font-body`** → texto corrido (Plus Jakarta 400/500)
- **`font-label`** → uppercase tracking-[0.2em-0.4em] (Plus Jakarta 500)

## 5. Responsividade

- **Mobile-first:** tudo funciona em 375px
- **Breakpoints:** `md:` (768px) para grid 2/3 colunas, `md:` para typography scaling
- **AppShell:** header 14h mobile / 16h desktop · labels nav escondidos <md (só icons)
- **CTAs:** 48px+ altura (WCAG target size)
- **Grids:** 2 cols mobile → 3-4 cols desktop

## 6. O Que NÃO Foi Tocado (preservação)

- `apps/web/src/hooks/use-evaluation-status.ts`
- `apps/web/src/lib/api-client.ts`
- `apps/web/src/types/index.ts`
- Nenhum comportamento/função foi removido ou alterado
- Onboarding, localStorage, rotas, APIs — idênticos

## 7. Próximos Passos Sugeridos

1. **Abrir no browser** em mobile + desktop e validar visual
2. **Testar fluxo E2E:** home → upload → context → processing → report → dimension → replay → share
3. **WCAG audit:** rodar contrast checker em `on-surface-variant` (#c3c6d4) sobre `surface-container-low` (#131b2e) — AA esperado
4. **Bottom nav mobile?** — opcional, hoje nav está no header. Se quiser BottomNavBar fixo como no DESIGN.md, fácil adicionar no AppShell
5. **Dark only por enquanto** — `<html class="dark">` hardcoded. Light mode não é prioridade segundo DESIGN.md

## 8. Referência

- **Design System visual:** `design/design-system-resonant-stage.html`
- **Design guide:** `design/modelo design/stitch_gravar_upload_de_v_deo/eloquent_ai/DESIGN.md`

---

— @ux-design-expert (Uma)
