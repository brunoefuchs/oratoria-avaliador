"""Convergence Harness — Story 7.6 (MVP Python via OpenRouter).

Measures convergence between Gemini 2.5 Flash, Claude Opus 4.6, GPT-5
on oratoria evaluation. Implements AC-1..AC-4, AC-8, AC-10 of Story 7.6.

Deferred from spec:
    AC-5/AC-6: Supabase tables (SQL migrations created, insert scaffolded)
    AC-7: /dev/convergence dashboard (Next.js — separate story)
    AC-9: Zero impact in production (harness is in scripts/, not ml-worker/)

Entry point: `python -m scripts.convergence.harness --help`
"""
