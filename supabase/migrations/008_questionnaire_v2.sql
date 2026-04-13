-- Migration 008: Questionario V2 — 6 perguntas reescritas pelo mentor
-- Renomeia contexto→motivacao, adiciona desejo_transmitir/desejo_melhorar, dropa objetivo

-- 1. Remover constraint do campo contexto (agora e motivacao)
ALTER TABLE evaluation_context DROP CONSTRAINT IF EXISTS evaluation_context_contexto_check;

-- 2. Renomear contexto para motivacao (agora e TEXT[] em vez de TEXT)
-- Nota: ALTER TYPE nao funciona direto, entao dropamos e recriamos
ALTER TABLE evaluation_context ADD COLUMN IF NOT EXISTS motivacao TEXT[];
-- Migrar dados antigos de contexto (single value) para motivacao (array)
UPDATE evaluation_context SET motivacao = ARRAY[contexto] WHERE contexto IS NOT NULL AND motivacao IS NULL;
ALTER TABLE evaluation_context DROP COLUMN IF EXISTS contexto;

-- 3. Adicionar novas colunas
ALTER TABLE evaluation_context ADD COLUMN IF NOT EXISTS desejo_transmitir TEXT[];
ALTER TABLE evaluation_context ADD COLUMN IF NOT EXISTS desejo_melhorar TEXT[];

-- 4. Remover coluna objetivo (substituida por desejo_transmitir + desejo_melhorar)
ALTER TABLE evaluation_context DROP COLUMN IF EXISTS objetivo;
