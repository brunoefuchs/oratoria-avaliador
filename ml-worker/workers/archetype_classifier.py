"""Classificador de Arquetipos Vocais.

Identifica qual dos 4 arquetipos vocais o orador esta usando em cada trecho:

- Educador: ritmo mais lento, pitch descendente no fim das frases,
  tom autoritativo e estruturado. Termina frases com entonacao BAIXA.
- Coach: staccato (palavras separadas), energia alta, tom diretivo.
  Pausas curtas entre palavras, volume acima da media.
- Motivador: legato (palavras fluem juntas), tom aspiracional e suave.
  Ritmo fluido, pitch ascendente, volume crescente.
- Amigo: ritmo casual, tom conversacional e relaxado.
  Variacao natural, volume moderado, humor no tom.

O objetivo nao e estar em um arquetipo "certo", mas CICLAR entre eles.
Ficar preso em um so = default = nao-funcional.
"""

import numpy as np
import parselmouth
import structlog

from contracts import WorkerResult
from workers._truth_contract_helpers import wrap_worker_result

logger = structlog.get_logger()

JANELA_ARQUETIPO = 10  # Analisa blocos de 10 segundos


def _extrair_features_janela(sound: parselmouth.Sound, t_inicio: float, t_fim: float) -> dict:
    """Extrai features acusticas de uma janela temporal para classificacao."""
    try:
        trecho = sound.extract_part(from_time=t_inicio, to_time=t_fim)
    except Exception:
        return None

    if trecho.get_total_duration() < 0.5:
        return None

    # Pitch
    pitch = trecho.to_pitch()
    pitch_values = pitch.selected_array["frequency"]
    pitch_voiced = pitch_values[pitch_values > 0]

    if len(pitch_voiced) < 5:
        return None

    pitch_mean = float(np.mean(pitch_voiced))
    pitch_std = float(np.std(pitch_voiced))

    # Tendencia do pitch (subindo ou descendo?)
    if len(pitch_voiced) > 10:
        meio = len(pitch_voiced) // 2
        pitch_primeira_metade = np.mean(pitch_voiced[:meio])
        pitch_segunda_metade = np.mean(pitch_voiced[meio:])
        tendencia_pitch = float(pitch_segunda_metade - pitch_primeira_metade)
    else:
        tendencia_pitch = 0.0

    # Intensidade (volume)
    intensity = trecho.to_intensity()
    if intensity.get_number_of_frames() < 2:
        return None

    int_values = intensity.values[0]
    int_mean = float(np.mean(int_values))
    int_std = float(np.std(int_values))

    # Tendencia de volume
    if len(int_values) > 10:
        meio = len(int_values) // 2
        vol_primeira = np.mean(int_values[:meio])
        vol_segunda = np.mean(int_values[meio:])
        tendencia_volume = float(vol_segunda - vol_primeira)
    else:
        tendencia_volume = 0.0

    # Staccato vs Legato (variacao rapida de intensidade = staccato)
    if len(int_values) > 2:
        diffs = np.abs(np.diff(int_values))
        staccato_index = float(np.mean(diffs))
    else:
        staccato_index = 0.0

    # Ratio silencio nesta janela
    threshold = int_mean - 8
    speech_frames = np.sum(int_values > threshold)
    speech_ratio = speech_frames / len(int_values) if len(int_values) > 0 else 0.0

    return {
        "pitch_mean": pitch_mean,
        "pitch_std": pitch_std,
        "tendencia_pitch": tendencia_pitch,
        "volume_mean": int_mean,
        "volume_std": int_std,
        "tendencia_volume": tendencia_volume,
        "staccato_index": staccato_index,
        "speech_ratio": float(speech_ratio),
    }


def _classificar_arquetipo(features: dict, media_global: dict) -> dict:
    """Classifica um trecho em um dos 4 arquetipos.

    B7 FIX (2026-04-18): scoring por ranking percentil entre janelas do proprio
    video, nao mais relativo a media global (que forcava todos rel~1.0 → Amigo
    sempre ganhava). Agora usa thresholds ABSOLUTOS + sinal de diferenca.

    Perfis prototipicos (absolutos):
    - EDUCADOR: tendencia_pitch < 0 (cai) + staccato baixo + speech_ratio baixo
    - COACH: staccato alto + volume alto (absoluto >65dB) + speech_ratio alto
    - MOTIVADOR: tendencia_pitch > 0 (sobe) + tendencia_volume > 0 + pitch acima
    - AMIGO: perfil neutro (ganha quando nenhum outro se destaca)
    """
    scores = {}

    tendencia_pitch = features["tendencia_pitch"]
    tendencia_volume = features["tendencia_volume"]
    volume_mean = features["volume_mean"]
    volume_std = features["volume_std"]
    speech_ratio = features["speech_ratio"]
    staccato_index = features["staccato_index"]
    pitch_mean = features["pitch_mean"]

    # ranks (percentil entre janelas) usando media_global + stats:
    # B7 fix: usa desvio relativo que permite contraste
    pitch_delta = pitch_mean - media_global["pitch_mean"]  # Hz
    vol_delta = volume_mean - media_global["volume_mean"]  # dB
    staccato_delta = staccato_index - media_global["staccato_index"]  # dB/frame

    # EDUCADOR: didatico, explica, pitch descendente pra enfase
    scores["educador"] = (
        max(0, -tendencia_pitch * 2.0)  # Pitch CAI forte (>20Hz queda)
        + max(0, (0.7 - speech_ratio) * 60)  # Mais pausas (speech<0.7)
        + max(0, -staccato_delta * 8)  # Menos staccato que media
        + max(0, 10 - abs(vol_delta))  # Volume proximo media
    )

    # COACH: diretivo, staccato, projecao
    scores["coach"] = (
        max(0, staccato_delta * 10)  # Mais staccato que media
        + max(0, vol_delta * 2.5)  # Volume acima media
        + max(0, (volume_mean - 62) * 2)  # Volume absoluto alto (>62dB)
        + max(0, volume_std * 3)  # Variacao volume (enfase)
    )

    # MOTIVADOR: aspiracional, pitch sobe, volume cresce
    scores["motivador"] = (
        max(0, tendencia_pitch * 2.0)  # Pitch SOBE forte
        + max(0, tendencia_volume * 4)  # Volume CRESCE
        + max(0, pitch_delta * 0.3)  # Pitch acima media
        + max(0, -staccato_delta * 5)  # Legato (fluido)
    )

    # AMIGO: casual, moderado (ganha quando nenhum outro se destaca)
    # B7 fix: score amigo agora eh baseline (nao depende de match proximo de 1.0)
    dominio_outros = max(scores["educador"], scores["coach"], scores["motivador"])
    # Amigo: base 25pt - ajustado quando outros arquetipos nao se destacam
    amigo_base = 25.0
    # Bonus amigo quando variacao natural baixa (sem extremos) — max 15pt
    amigo_bonus = 0.0
    if volume_std < 10 and abs(tendencia_pitch) < 15 and abs(tendencia_volume) < 2:
        amigo_bonus = 15
    # Penalidade se algum outro arquetipo dominou muito
    scores["amigo"] = amigo_base + amigo_bonus - max(0, (dominio_outros - 40) * 0.3)

    # Arquetipo dominante
    arquetipo = max(scores, key=scores.get)
    confianca = scores[arquetipo] / (sum(v for v in scores.values() if v > 0) + 1e-8)

    return {
        "arquetipo": arquetipo,
        "confianca": round(float(confianca), 3),
        "scores": {k: round(float(v), 2) for k, v in scores.items()},
    }


def _compute_archetype_metrics(audio_path: str) -> dict:
    """Classifica arquetipos vocais ao longo do audio.

    Analisa janelas de JANELA_ARQUETIPO segundos e identifica:
    - Arquetipo dominante geral
    - Cycling entre arquetipos
    - Lock-in (preso em um so)
    - Mapa temporal de arquetipos
    """
    logger.info("archetype_classification_start", audio_path=audio_path)

    sound = parselmouth.Sound(audio_path)
    duracao = sound.get_total_duration()
    # N janelas uniformes cobrindo 100% da duracao (alvo ~10s cada)
    num_janelas = max(1, round(duracao / JANELA_ARQUETIPO))
    janela_dur = duracao / num_janelas

    # Primeira passada: extrair features de todas as janelas
    features_por_janela = []
    for j in range(num_janelas):
        t_inicio = j * janela_dur
        t_fim = (j + 1) * janela_dur
        features = _extrair_features_janela(sound, t_inicio, t_fim)
        if features:
            features["t_inicio"] = t_inicio
            features["t_fim"] = t_fim
            features_por_janela.append(features)

    if not features_por_janela:
        return {
            "score": 0,
            "confidence": "failed",
            "metrics": {},
        }

    # Calcular medias globais para normalizacao
    media_global = {
        "pitch_mean": float(np.mean([f["pitch_mean"] for f in features_por_janela])),
        "pitch_std": float(np.mean([f["pitch_std"] for f in features_por_janela])),
        "volume_mean": float(np.mean([f["volume_mean"] for f in features_por_janela])),
        "staccato_index": float(np.mean([f["staccato_index"] for f in features_por_janela])),
    }

    # Segunda passada: classificar cada janela
    classificacoes = []
    for features in features_por_janela:
        resultado = _classificar_arquetipo(features, media_global)
        resultado["t_inicio"] = features["t_inicio"]
        resultado["t_fim"] = features["t_fim"]
        classificacoes.append(resultado)

    # =============================================
    # METRICAS DE ARQUETIPOS
    # =============================================

    from collections import Counter

    arquetipos_usados = [c["arquetipo"] for c in classificacoes]
    contagem = Counter(arquetipos_usados)
    total = len(arquetipos_usados)

    # Distribuicao percentual
    distribuicao = {arq: round(count / total * 100, 1) for arq, count in contagem.items()}

    # Garantir todos os 4 presentes
    for arq in ["educador", "coach", "motivador", "amigo"]:
        if arq not in distribuicao:
            distribuicao[arq] = 0.0

    # Arquetipo dominante (default)
    arquetipo_dominante = contagem.most_common(1)[0][0] if contagem else "indefinido"
    pct_dominante = distribuicao.get(arquetipo_dominante, 0)

    # Arquetipos acessiveis (>10%) vs ausentes (<5%)
    acessiveis = [arq for arq, pct in distribuicao.items() if pct >= 10]
    ausentes = [arq for arq, pct in distribuicao.items() if pct < 5]

    # Cycling: quantas trocas de arquetipo ao longo do tempo
    trocas = 0
    for i in range(1, len(arquetipos_usados)):
        if arquetipos_usados[i] != arquetipos_usados[i - 1]:
            trocas += 1

    trocas_por_minuto = round(trocas / (duracao / 60), 1) if duracao > 0 else 0
    num_arquetipos_unicos = len(set(arquetipos_usados))

    # Lock-in tiered (2026-05-06):
    # - lock_in_warning: >50% = sinal de tendencia (audiencia comeca a perceber)
    # - lock_in: >70% = travamento real (audiencia percebe "personagem unico")
    # - lock_in_critico: >=80% = audiencia adormece, archetype default total
    lock_in_warning = pct_dominante > 50
    lock_in = pct_dominante > 70
    lock_in_critico = pct_dominante >= 80

    # =============================================
    # SCORE DE ARQUETIPOS (0-100)
    # =============================================

    # 1. Diversidade de arquetipos — peso 40%
    # Story 7.1 AC-1: combina cobertura (quantos dos 4 arquetipos foram usados)
    # com evenness (quao equilibrado e o uso entre os usados).
    #   1 arquetipo em 100%  = 0
    #   2 em 50/50           = ~50
    #   4 igualmente (25%)   = 100
    #   2 em 80/20           = ~36 (penalizado por desequilibrio interno)
    if num_arquetipos_unicos <= 1:
        diversidade_score = 0.0
    else:
        valores_norm = [pct / 100.0 for pct in distribuicao.values() if pct > 0]
        entropy = -sum(v * np.log(v) for v in valores_norm)
        # Max entropy = log(N) onde N = arquetipos usados (uso equilibrado entre eles).
        # Isso isola "evenness interna" da "cobertura".
        max_entropy = np.log(num_arquetipos_unicos)
        evenness = entropy / max_entropy if max_entropy > 0 else 0
        diversidade_score = (num_arquetipos_unicos / 4) * evenness * 100

    # 2. Cycling (trocas por minuto) — peso 30%
    #    Ideal: 2-5 trocas/min
    if trocas_por_minuto < 1:
        cycling_score = 20  # Quase nao troca
    elif trocas_por_minuto <= 2:
        cycling_score = 50 + (trocas_por_minuto - 1) * 30
    elif trocas_por_minuto <= 5:
        cycling_score = 80 + (trocas_por_minuto - 2) * 7
    else:
        cycling_score = max(
            60, 100 - (trocas_por_minuto - 5) * 10
        )  # Demais trocas = inconsistencia

    # 3. Anti-lock-in — peso 30%
    #    2026-05-06: tiers ajustados pra audit Vinh. Lock-in severo (>=70%)
    #    e critico (>=80%) penalizados mais — audiencia REALMENTE percebe
    #    "personagem unico" nesses niveis. >50% e warning leve mas detectavel.
    if pct_dominante >= 80:
        lockin_score = 5  # critico — audiencia adormece, era 10
    elif pct_dominante >= 70:
        lockin_score = 20  # severo — era 30
    elif pct_dominante > 50:
        lockin_score = 55  # warning — era 60
    elif pct_dominante > 35:
        lockin_score = 90
    else:
        lockin_score = 100  # Distribuicao equilibrada

    # 4. Qualidade do dominante — peso 30% (BUG-MP-5: consistência > diversidade)
    #    Orador que sustenta 1 persona forte com alta confiança = valor real
    #    Confiança média do dominante nas janelas onde aparece
    confiancas_dominante = [
        c["confianca"] for c in classificacoes if c["arquetipo"] == arquetipo_dominante
    ]
    confianca_media_dom = float(np.mean(confiancas_dominante)) if confiancas_dominante else 0.0
    qualidade_dominante = min(100, confianca_media_dom * 200)  # 0.5 confiança → 100

    # Score rebalanceado: valoriza CONSISTÊNCIA + QUALIDADE, não só diversidade
    # v1: 40% diversidade + 30% cycling + 30% lockin → score=9 pra persona forte
    # v2: 25/20/25/30 → score=35 (melhorou mas gap -46 vs LLMs)
    # v3: 15/20/25/40 → qualidade do dominante pesa mais que diversidade
    archetype_score = round(
        diversidade_score * 0.15
        + cycling_score * 0.20
        + lockin_score * 0.25
        + qualidade_dominante * 0.40
    )

    # Floor: persona forte (alta confiança) com lock-in nunca < 35
    # Rubric: "Arquétipo claro, consistente, autêntico" ≥ 61
    if lock_in and confianca_media_dom > 0.4:
        archetype_score = max(archetype_score, 35)

    archetype_score = max(0, min(100, archetype_score))

    logger.info(
        "archetype_classification_complete",
        score=archetype_score,
        dominante=arquetipo_dominante,
        lock_in=lock_in,
        trocas_por_min=trocas_por_minuto,
        num_unicos=num_arquetipos_unicos,
    )

    return {
        "score": archetype_score,
        "confidence": "high" if len(features_por_janela) >= 3 else "medium",
        "metrics": {
            "arquetipo_dominante": arquetipo_dominante,
            "distribuicao": distribuicao,
            "acessiveis": acessiveis,
            "ausentes": ausentes,
            "lock_in": lock_in,
            "lock_in_warning": lock_in_warning,
            "lock_in_critico": lock_in_critico,
            "pct_dominante": pct_dominante,
            "trocas_por_minuto": trocas_por_minuto,
            "num_arquetipos_usados": num_arquetipos_unicos,
            "total_janelas": len(classificacoes),
            "mapa_temporal": [
                {
                    "inicio": c["t_inicio"],
                    "fim": c["t_fim"],
                    "arquetipo": c["arquetipo"],
                    "confianca": c["confianca"],
                }
                for c in classificacoes
            ],
            "sub_scores": {
                "diversidade": round(diversidade_score),
                "cycling": round(cycling_score),
                "anti_lockin": round(lockin_score),
            },
        },
    }


# Story 8.2 — Truth Contract


def classify_archetypes_legacy(audio_path: str) -> dict:
    """Legacy path (TRUTH_CONTRACT_ENABLED=false)."""
    return _compute_archetype_metrics(audio_path)


def classify_archetypes(audio_path: str) -> dict:
    """Legacy alias kept for backwards compat with app.py callers."""
    return _compute_archetype_metrics(audio_path)


def analyze_archetypes(audio_path: str) -> "WorkerResult":
    """Truth Contract path (TRUTH_CONTRACT_ENABLED=true)."""
    return wrap_worker_result("archetypes", _compute_archetype_metrics, audio_path)
