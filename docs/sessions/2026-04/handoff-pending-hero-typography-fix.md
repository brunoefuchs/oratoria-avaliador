# Handoff — Pendência: Hero da Home em 3 Linhas (voltar depois)

**Data:** 2026-04-14
**Status:** PENDENTE · cache stale suspeito

---

## Contexto

Durante a migração do app para o design system "The Resonant Stage", o hero da home (`apps/web/src/app/page.tsx`) está renderizando em **3 linhas** em vez das **2 linhas esperadas**:

**Esperado:**
```
Descubra o que está
travando sua comunicação
```

**Atual (observado no browser do usuário, desktop):**
```
Descubra o que está
travando sua
comunicação
```

## Última Configuração Aplicada

- `.display-lg` em `apps/web/src/app/globals.css`:
  ```css
  font-size: clamp(1.5rem, 4.5vw, 3rem);   /* 24px mobile → 48px desktop */
  line-height: 1.15;
  letter-spacing: -0.015em;
  font-weight: 700;  (mobile) / 800 (md+)
  ```
- `page.tsx` — 2 spans com `block` forçado:
  ```tsx
  <span className="block bg-clip-text ...">Descubra o que está</span>
  <span className="block bg-clip-text ...">travando sua comunicação</span>
  ```

## Suspeita

**Cache stale do Next.js + browser**, não o CSS em si. Múltiplas iterações de redução de fonte (72px → 48px → 20px → 16px → 14px) não mudaram nada visualmente — indicativo claro de que o navegador está servindo CSS antigo.

## Passos Para Retomar

1. Matar qualquer `next dev` em execução (`Ctrl+C` + `pgrep -f next | xargs kill`)
2. Apagar cache:
   ```bash
   rm -rf apps/web/.next
   ```
3. Reiniciar dev:
   ```bash
   cd apps/web && npm run dev
   ```
4. Abrir em **janela anônima** (`Ctrl+Shift+N`) para bypassar cache do Chrome:
   - `http://localhost:3000`
5. Se persistir após cache clean + anônima → é bug de CSS real. Investigar:
   - Viewport exato (DevTools Ctrl+Shift+M)
   - Width da janela em px
   - Se há padding adicional no container `max-w-xl` do AppShell
   - Considerar aumentar `AppShell maxWidth="xl"` para `"2xl"` na home

## Arquivos Envolvidos

- `apps/web/src/app/globals.css` — `.display-lg`
- `apps/web/src/app/page.tsx` — hero h1
- `apps/web/src/components/app-shell.tsx` — container max-width

## Nota

Todo o restante da migração (13 arquivos, 8 rotas, tokens DS completo) **está funcional** — `npx tsc --noEmit` e `npx next build` passaram com exit 0. Esta é a única pendência visual aberta.

---

— @ux-design-expert (Uma)
